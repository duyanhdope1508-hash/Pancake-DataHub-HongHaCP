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


async def run_forever(settings: Settings) -> None:
    init_db()
    logger.info(
        "Pancake sync worker started with interval=%s seconds",
        settings.pancake_sync_interval_seconds,
    )
    while True:
        try:
            result = await run_cycle(settings)
            logger.info("Sync cycle completed: %s", json.dumps(result, default=str))
        except Exception:
            logger.exception("Sync cycle failed")
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
