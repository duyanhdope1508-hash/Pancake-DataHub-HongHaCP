from datetime import datetime
from typing import Any

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import (
    CoreCustomer,
    CoreOrder,
    CoreOrderItem,
    PancakePageCustomer,
    RawOrder,
    Shop,
    SyncRun,
)


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _scoped_count(session: Any, model: Any, shop_ids: tuple[str, ...] | None) -> int:
    statement = select(func.count()).select_from(model)
    if shop_ids is not None:
        statement = statement.where(model.shop_id.in_(shop_ids))
    return session.scalar(statement) or 0


def database_status(shop_ids: tuple[str, ...] | None = None) -> dict[str, Any]:
    with SessionLocal() as session:
        shop_statement = select(func.count()).select_from(Shop)
        if shop_ids is not None:
            shop_statement = shop_statement.where(Shop.id.in_(shop_ids))
        shop_count = session.scalar(shop_statement) or 0
        order_count = _scoped_count(session, RawOrder, shop_ids)
        core_customer_count = _scoped_count(session, CoreCustomer, shop_ids)
        core_order_count = _scoped_count(session, CoreOrder, shop_ids)
        core_item_count = _scoped_count(session, CoreOrderItem, shop_ids)
        page_customer_count = (
            session.scalar(select(func.count()).select_from(PancakePageCustomer)) or 0
            if shop_ids is None
            else 0
        )
        latest_statement = select(SyncRun)
        if shop_ids is not None:
            latest_statement = latest_statement.where(SyncRun.shop_id.in_(shop_ids))
        latest_run = session.scalar(
            latest_statement.order_by(SyncRun.started_at.desc()).limit(1)
        )

        latest: dict[str, Any] | None = None
        if latest_run:
            latest = {
                "id": latest_run.id,
                "connector": latest_run.connector_name,
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
            "page_customers": page_customer_count,
            "latest_sync": latest,
        }

