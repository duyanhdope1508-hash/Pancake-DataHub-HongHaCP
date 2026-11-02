from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models import CoreCustomer, CoreOrder
from app.transform import normalize_phone


def mask_phone(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 4:
        return "*" * len(value)
    return ("*" * (len(value) - 4)) + value[-4:]


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_orders(
    session: Session,
    *,
    query: str | None = None,
    shop_id: str | None = None,
    page_id: str | None = None,
    status: int | None = None,
    page_number: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    statement = select(CoreOrder, CoreCustomer).outerjoin(
        CoreCustomer,
        and_(
            CoreCustomer.shop_id == CoreOrder.shop_id,
            CoreCustomer.source_customer_id == CoreOrder.source_customer_id,
        ),
    )

    clean_query = query.strip() if query else ""
    if clean_query:
        escaped_query = escape_like(clean_query)
        search_conditions = [
            CoreOrder.source_order_id.ilike(f"%{escaped_query}%", escape="\\"),
            CoreOrder.tracking_code.ilike(f"%{escaped_query}%", escape="\\"),
            CoreCustomer.name.ilike(f"%{escaped_query}%", escape="\\"),
        ]
        normalized_query = normalize_phone(clean_query)
        if normalized_query:
            search_conditions.append(
                CoreCustomer.normalized_phone.ilike(f"%{normalized_query}%")
            )
        statement = statement.where(or_(*search_conditions))

    if shop_id:
        statement = statement.where(CoreOrder.shop_id == shop_id)
    if page_id:
        statement = statement.where(CoreOrder.source_page_id == page_id)
    if status is not None:
        statement = statement.where(CoreOrder.status == status)

    total = session.scalar(
        select(func.count()).select_from(statement.order_by(None).subquery())
    ) or 0
    offset = (page_number - 1) * page_size
    rows = session.execute(
        statement.order_by(CoreOrder.source_updated_at.desc().nullslast())
        .offset(offset)
        .limit(page_size)
    ).all()

    items: list[dict[str, Any]] = []
    for order, customer in rows:
        items.append(
            {
                "shop_id": order.shop_id,
                "order_id": order.source_order_id,
                "page_id": order.source_page_id,
                "page_name": order.page_name,
                "status": order.status,
                "status_name": order.status_name,
                "tracking_code": order.tracking_code,
                "delivery_status": order.delivery_status,
                "total_price": order.total_price,
                "total_quantity": order.total_quantity,
                "currency": order.currency,
                "inserted_at": order.inserted_at,
                "updated_at": order.source_updated_at,
                "customer_name": customer.name if customer else None,
                "customer_phone_masked": (
                    mask_phone(customer.primary_phone) if customer else None
                ),
            }
        )

    return {
        "items": items,
        "pagination": {
            "page_number": page_number,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }

