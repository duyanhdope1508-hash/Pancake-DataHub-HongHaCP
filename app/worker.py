import asyncio
import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from time import monotonic
from typing import Any

from sqlalchemy import text

from app.audit import cleanup_audit_history
from app.config import Settings, get_settings
from app.db import SessionLocal, engine, init_db
from app.sync import sync_all
from app.telegram_alerts import send_telegram_alert
from app.transform import transform_raw_orders

logger = logging.getLogger(__name__)
SYNC_ADVISORY_LOCK_ID = 1_735_531_090
_last_audit_cleanup_at: float | None = None


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
        sync_result = await sync_all(settings)
        transform_result = transform_raw_orders()
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
    interval_hours = settings.pancake_sync_interval_seconds / 3600
    return (
        "🚨 HỒNG HÀ DATAHUB\n"
        "Đồng bộ Pancake không hoàn tất.\n"
        f"Kết nối lỗi: {failed}\n"
        f"Shop đã xử lý: {processed}\n"
        f"Hệ thống sẽ tự thử lại sau khoảng {interval_hours:g} giờ."
    )


async def _send_alert(settings: Settings, message: str) -> bool:
    sent = await send_telegram_alert(settings.telegram_alerts_file, message)
    if sent is False:
        logger.warning("Telegram alert could not be delivered")
    return sent is True


async def run_forever(settings: Settings) -> None:
    init_db()
    sync_unhealthy = False
    failure_notified = False
    logger.info(
        "Pancake sync worker started with interval=%s seconds",
        settings.pancake_sync_interval_seconds,
    )
    while True:
        try:
            result = await run_cycle(settings)
            logger.info("Sync cycle completed: %s", json.dumps(result, default=str))
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
            if not sync_unhealthy or not failure_notified:
                failure_notified = await _send_alert(
                    settings,
                    "🚨 HỒNG HÀ DATAHUB\n"
                    "Worker đồng bộ gặp lỗi ngoài dự kiến.\n"
                    f"Loại lỗi: {type(exc).__name__}\n"
                    "Hãy kiểm tra log trên VPS.",
                )
            sync_unhealthy = True
        try:
            cleanup_result = cleanup_audit_history_if_due(settings)
            if cleanup_result is not None:
                logger.info(
                    "Audit cleanup completed: %s",
                    json.dumps(cleanup_result, default=str),
                )
        except Exception:
            logger.exception("Audit cleanup failed")
        await asyncio.sleep(settings.pancake_sync_interval_seconds)


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
