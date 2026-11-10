import asyncio
import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from time import monotonic
from typing import Any

from sqlalchemy import select, text, update

from app.audit import cleanup_audit_history
from app.config import Settings, get_settings
from app.db import SessionLocal, engine, init_db
from app.models import AuditLog, SyncRequest, SyncRun
from app.sync import sync_all
from app.telegram_alerts import send_telegram_alert
from app.transform import transform_raw_orders

logger = logging.getLogger(__name__)
SYNC_ADVISORY_LOCK_ID = 1_735_531_090
_last_audit_cleanup_at: float | None = None
MANUAL_SYNC_POLL_SECONDS = 5


def cancel_interrupted_sync_runs() -> int:
    with SessionLocal() as session:
        result = session.execute(
            update(SyncRun)
            .where(
                SyncRun.status == "running",
                SyncRun.finished_at.is_(None),
            )
            .values(
                status="cancelled",
                error="Previous worker stopped before the sync cycle completed",
                finished_at=datetime.now(UTC),
            )
        )
        session.commit()
        return max(int(result.rowcount or 0), 0)


def recover_interrupted_sync_requests() -> int:
    """Return requests abandoned by a restarted worker to the durable queue."""
    with SessionLocal() as session:
        result = session.execute(
            update(SyncRequest)
            .where(SyncRequest.status == "running")
            .values(
                status="queued",
                error="Worker restarted before the requested sync completed",
                started_at=None,
            )
        )
        session.commit()
        return max(int(result.rowcount or 0), 0)


def claim_sync_request() -> SyncRequest | None:
    with SessionLocal() as session:
        request = session.scalar(
            select(SyncRequest)
            .where(SyncRequest.status == "queued")
            .order_by(SyncRequest.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if request is None:
            return None
        request.status = "running"
        request.started_at = datetime.now(UTC)
        request.error = None
        session.commit()
        session.expunge(request)
        return request


def finish_sync_request(request_id: str, result: dict[str, Any]) -> None:
    status = "skipped" if result.get("status") == "skipped" else "completed"
    sync_result = result.get("sync") if isinstance(result.get("sync"), dict) else {}
    with SessionLocal() as session:
        request = session.get(SyncRequest, request_id)
        if request is None:
            return
        request.status = status
        request.result_json = result
        request.finished_at = datetime.now(UTC)
        session.add(
            AuditLog(
                actor_user_id=request.requested_by_user_id,
                action="orders.sync",
                resource_type="sync",
                resource_id=request.id,
                result=(
                    "skipped"
                    if status == "skipped"
                    else "success" if sync_result.get("success") is True else "partial"
                ),
                metadata_json={
                    "shops_processed": int(sync_result.get("shops_processed") or 0),
                    "connectors_failed": int(sync_result.get("connectors_failed") or 0),
                    "rows_written": int(sync_result.get("rows_written") or 0),
                },
            )
        )
        session.commit()


def fail_sync_request(request_id: str, exc: Exception) -> None:
    with SessionLocal() as session:
        request = session.get(SyncRequest, request_id)
        if request is None:
            return
        request.status = "failed"
        request.error = type(exc).__name__
        request.finished_at = datetime.now(UTC)
        session.add(
            AuditLog(
                actor_user_id=request.requested_by_user_id,
                action="orders.sync",
                resource_type="sync",
                resource_id=request.id,
                result="failed",
                metadata_json={"error_type": type(exc).__name__},
            )
        )
        session.commit()


def run_audit_cleanup(settings: Settings) -> dict[str, int]:
    with SessionLocal() as session:
        result = cleanup_audit_history(
            session,
            detail_retention_days=settings.audit_detail_retention_days,
            general_retention_days=settings.audit_general_retention_days,
        )
        session.commit()
        return result


def cleanup_audit_history_if_due(
    settings: Settings,
    *,
    current_monotonic: float | None = None,
) -> dict[str, int] | None:
    global _last_audit_cleanup_at
    current_time = current_monotonic if current_monotonic is not None else monotonic()
    if (
        _last_audit_cleanup_at is not None
        and current_time - _last_audit_cleanup_at < settings.audit_cleanup_interval_seconds
    ):
        return None
    result = run_audit_cleanup(settings)
    _last_audit_cleanup_at = current_time
    return result


@contextmanager
def sync_cycle_lock() -> Iterator[bool]:
    """Hold one PostgreSQL session lock for the complete sync/transform cycle."""
    with engine.connect() as connection:
        acquired = bool(
            connection.scalar(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": SYNC_ADVISORY_LOCK_ID},
            )
        )
        if not acquired:
            yield False
            return
        try:
            yield True
        finally:
            connection.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                {"lock_id": SYNC_ADVISORY_LOCK_ID},
            )


async def run_cycle(settings: Settings) -> dict[str, Any]:
    with sync_cycle_lock() as acquired:
        if not acquired:
            return {"status": "skipped", "reason": "already_running"}
        interrupted_runs = cancel_interrupted_sync_runs()
        if interrupted_runs:
            logger.warning("Cancelled %s interrupted sync runs", interrupted_runs)
        logger.info("Sync phase started")
        sync_started_at = monotonic()
        sync_result = await sync_all(settings)
        logger.info(
            "Sync phase completed in %.1fs: shops=%s pages=%s rows_seen=%s rows_written=%s failed_connectors=%s",
            monotonic() - sync_started_at,
            sync_result.get("shops_processed", 0),
            sync_result.get("pages_processed", 0),
            sync_result.get("rows_seen", 0),
            sync_result.get("rows_written", 0),
            sync_result.get("connectors_failed", 0),
        )
        logger.info("Transform phase started")
        transform_started_at = monotonic()
        transform_result = transform_raw_orders()
        logger.info(
            "Transform phase completed in %.1fs: batches=%s orders=%s customers=%s items=%s",
            monotonic() - transform_started_at,
            transform_result.get("batches_processed", 0),
            transform_result.get("orders_transformed", 0),
            transform_result.get("customers_transformed", 0),
            transform_result.get("items_transformed", 0),
        )
        return {
            "status": "completed",
            "sync": sync_result,
            "transform": transform_result,
        }


def sync_cycle_health(result: dict[str, Any]) -> bool | None:
    if result.get("status") != "completed":
        return None
    sync_result = result.get("sync")
    if not isinstance(sync_result, dict):
        return False
    return sync_result.get("success") is True


def sync_failure_message(result: dict[str, Any], settings: Settings) -> str:
    sync_result = result.get("sync") if isinstance(result.get("sync"), dict) else {}
    failed = int(sync_result.get("connectors_failed") or 0)
    processed = int(sync_result.get("shops_processed") or 0)
    errors = sync_result.get("errors") if isinstance(sync_result.get("errors"), list) else []
    failed_names = ", ".join(
        str(item.get("connector"))
        for item in errors[:3]
        if isinstance(item, dict) and item.get("connector")
    )
    failed_detail = f"Kết nối cần kiểm tra: {failed_names}\n" if failed_names else ""
    interval_hours = settings.pancake_sync_interval_seconds / 3600
    return (
        "🚨 HỒNG HÀ DATAHUB\n"
        "Đồng bộ Pancake không hoàn tất.\n"
        f"Kết nối lỗi: {failed}\n"
        f"Shop đã xử lý: {processed}\n"
        f"{failed_detail}"
        f"Hệ thống sẽ tự thử lại sau khoảng {interval_hours:g} giờ."
    )


async def _send_alert(settings: Settings, message: str) -> bool:
    sent = await send_telegram_alert(settings.telegram_alerts_file, message)
    if sent is False:
        logger.warning("Telegram alert could not be delivered")
    return sent is True


async def run_forever(settings: Settings) -> None:
    init_db()
    recovered_requests = recover_interrupted_sync_requests()
    if recovered_requests:
        logger.warning("Requeued %s interrupted manual sync requests", recovered_requests)
    sync_unhealthy = False
    failure_notified = False
    next_scheduled_sync = 0.0
    logger.info(
        "Pancake sync worker started with interval=%s seconds",
        settings.pancake_sync_interval_seconds,
    )
    while True:
        manual_request = claim_sync_request()
        scheduled_sync_due = monotonic() >= next_scheduled_sync
        if manual_request is None and not scheduled_sync_due:
            await asyncio.sleep(
                max(
                    0.1,
                    min(MANUAL_SYNC_POLL_SECONDS, next_scheduled_sync - monotonic()),
                )
            )
            continue
        try:
            result = await run_cycle(settings)
            logger.info("Sync cycle completed: %s", json.dumps(result, default=str))
            if manual_request is not None:
                finish_sync_request(manual_request.id, result)
            health = sync_cycle_health(result)
            if health is False:
                if not sync_unhealthy or not failure_notified:
                    failure_notified = await _send_alert(
                        settings,
                        sync_failure_message(result, settings),
                    )
                sync_unhealthy = True
            elif health is True:
                if sync_unhealthy and failure_notified:
                    await _send_alert(
                        settings,
                        "✅ HỒNG HÀ DATAHUB\nĐồng bộ Pancake đã phục hồi bình thường.",
                    )
                sync_unhealthy = False
                failure_notified = False
        except Exception as exc:
            logger.exception("Sync cycle failed")
            if manual_request is not None:
                fail_sync_request(manual_request.id, exc)
            if not sync_unhealthy or not failure_notified:
                failure_notified = await _send_alert(
                    settings,
                    "🚨 HỒNG HÀ DATAHUB\n"
                    "Worker đồng bộ gặp lỗi ngoài dự kiến.\n"
                    f"Loại lỗi: {type(exc).__name__}\n"
                    "Hãy kiểm tra log trên VPS.",
                )
            sync_unhealthy = True
        finally:
            next_scheduled_sync = monotonic() + settings.pancake_sync_interval_seconds
        try:
            cleanup_result = cleanup_audit_history_if_due(settings)
            if cleanup_result is not None:
                logger.info(
                    "Audit cleanup completed: %s",
                    json.dumps(cleanup_result, default=str),
                )
        except Exception:
            logger.exception("Audit cleanup failed")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # Pancake authenticates through a query parameter. httpx's INFO request log
    # includes the complete URL, so keep it disabled to prevent credential leaks.
    logging.getLogger("httpx").setLevel(logging.WARNING)


def main() -> None:
    configure_logging()
    asyncio.run(run_forever(get_settings()))


if __name__ == "__main__":
    main()
