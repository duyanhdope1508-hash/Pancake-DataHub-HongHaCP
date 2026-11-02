from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CoreOrder


def order_filters(session: Session) -> dict[str, Any]:
    total_orders = session.scalar(select(func.count()).select_from(CoreOrder)) or 0

    page_rows = session.execute(
        select(
            CoreOrder.source_page_id,
            CoreOrder.page_name,
            func.count().label("order_count"),
        )
        .where(CoreOrder.source_page_id.is_not(None))
        .group_by(CoreOrder.source_page_id, CoreOrder.page_name)
        .order_by(CoreOrder.page_name.asc().nullslast(), CoreOrder.source_page_id.asc())
    ).all()

    status_rows = session.execute(
        select(
            CoreOrder.status,
            CoreOrder.status_name,
            func.count().label("order_count"),
        )
        .where(CoreOrder.status.is_not(None))
        .group_by(CoreOrder.status, CoreOrder.status_name)
        .order_by(CoreOrder.status.asc())
    ).all()

    return {
        "total_orders": total_orders,
        "pages": [
            {
                "page_id": page_id,
                "page_name": page_name,
                "order_count": order_count,
            }
            for page_id, page_name, order_count in page_rows
        ],
        "statuses": [
            {
                "status": status,
                "status_name": status_name,
                "order_count": order_count,
            }
            for status, status_name, order_count in status_rows
        ],
    }

