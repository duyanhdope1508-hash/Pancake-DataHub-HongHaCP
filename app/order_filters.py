from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CoreOrder, Shop


def order_filters(session: Session) -> dict[str, Any]:
    total_orders = session.scalar(select(func.count()).select_from(CoreOrder)) or 0

    shop_rows = session.execute(
        select(
            CoreOrder.shop_id,
            Shop.name,
            func.count().label("order_count"),
        )
        .outerjoin(Shop, Shop.id == CoreOrder.shop_id)
        .group_by(CoreOrder.shop_id, Shop.name)
        .order_by(Shop.name.asc().nullslast(), CoreOrder.shop_id.asc())
    ).all()

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

    carrier_rows = session.execute(
        select(CoreOrder.carrier_name, func.count().label("order_count"))
        .where(CoreOrder.carrier_name.is_not(None), CoreOrder.carrier_name != "")
        .group_by(CoreOrder.carrier_name)
        .order_by(CoreOrder.carrier_name.asc())
    ).all()

    delivery_status_rows = session.execute(
        select(CoreOrder.delivery_status, func.count().label("order_count"))
        .where(
            CoreOrder.delivery_status.is_not(None),
            CoreOrder.delivery_status != "",
        )
        .group_by(CoreOrder.delivery_status)
        .order_by(CoreOrder.delivery_status.asc())
    ).all()

    date_range = session.execute(
        select(func.min(CoreOrder.inserted_at), func.max(CoreOrder.inserted_at))
    ).one()

    return {
        "total_orders": total_orders,
        "shops": [
            {
                "shop_id": shop_id,
                "shop_name": shop_name,
                "order_count": order_count,
            }
            for shop_id, shop_name, order_count in shop_rows
        ],
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
        "carriers": [
            {"carrier_name": carrier_name, "order_count": order_count}
            for carrier_name, order_count in carrier_rows
        ],
        "delivery_statuses": [
            {"delivery_status": delivery_status, "order_count": order_count}
            for delivery_status, order_count in delivery_status_rows
        ],
        "date_range": {
            "from": date_range[0],
            "to": date_range[1],
        },
    }

