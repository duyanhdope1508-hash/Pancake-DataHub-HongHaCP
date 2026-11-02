from datetime import datetime
from typing import Any

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import CoreCustomer, CoreOrder, CoreOrderItem, RawOrder, Shop, SyncRun


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def database_status() -> dict[str, Any]:
    with SessionLocal() as session:
        shop_count = session.scalar(select(func.count()).select_from(Shop)) or 0
        order_count = session.scalar(select(func.count()).select_from(RawOrder)) or 0
        core_customer_count = (
            session.scalar(select(func.count()).select_from(CoreCustomer)) or 0
        )
        core_order_count = session.scalar(select(func.count()).select_from(CoreOrder)) or 0
        core_item_count = (
            session.scalar(select(func.count()).select_from(CoreOrderItem)) or 0
        )
        latest_run = session.scalar(
            select(SyncRun).order_by(SyncRun.started_at.desc()).limit(1)
        )

        latest: dict[str, Any] | None = None
        if latest_run:
            latest = {
                "id": latest_run.id,
                "shop_id": latest_run.shop_id,
                "status": latest_run.status,
                "rows_seen": latest_run.rows_seen,
                "rows_written": latest_run.rows_written,
                "started_at": _isoformat(latest_run.started_at),
                "finished_at": _isoformat(latest_run.finished_at),
                "has_error": bool(latest_run.error),
            }

        return {
            "shops": shop_count,
            "raw_orders": order_count,
            "core_customers": core_customer_count,
            "core_orders": core_order_count,
            "core_order_items": core_item_count,
            "latest_sync": latest,
        }

