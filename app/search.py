from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.business_status import (
    business_status_expression,
    business_status_label,
    classify_business_status,
)
from app.models import CoreCustomer, CoreOrder, CoreOrderItem


def mask_phone(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 4:
        return "*" * len(value)
    return ("*" * (len(value) - 4)) + value[-4:]


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _filter_values[FilterValue](
    value: FilterValue | list[FilterValue] | None,
) -> list[FilterValue]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _has_text(column: Any) -> Any:
    return and_(column.is_not(None), column != "")


def filtered_orders_statement(
    *,
    query: str | None = None,
    shop_id: str | list[str] | None = None,
    page_id: str | list[str] | None = None,
    status: int | list[int] | None = None,
    business_status: str | list[str] | None = None,
    carrier_name: str | list[str] | None = None,
    delivery_status: str | list[str] | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    min_total: Decimal | None = None,
    max_total: Decimal | None = None,
    has_tracking: bool | None = None,
    sent_to_carrier: bool | None = None,
    returned: bool | None = None,
    product: str | None = None,
) -> Any:
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
        statement = statement.where(
            CoreOrder.search_text.ilike(f"%{escaped_query}%", escape="\\")
        )

    shop_ids = _filter_values(shop_id)
    if shop_ids:
        statement = statement.where(CoreOrder.shop_id.in_(shop_ids))
    page_ids = _filter_values(page_id)
    if page_ids:
        statement = statement.where(CoreOrder.source_page_id.in_(page_ids))
    statuses = _filter_values(status)
    if statuses:
        statement = statement.where(CoreOrder.status.in_(statuses))
    business_statuses = _filter_values(business_status)
    if business_statuses:
        statement = statement.where(
            business_status_expression().in_(business_statuses)
        )
    carriers = _filter_values(carrier_name)
    if carriers:
        statement = statement.where(CoreOrder.carrier_name.in_(carriers))
    delivery_statuses = _filter_values(delivery_status)
    if delivery_statuses:
        statement = statement.where(CoreOrder.delivery_status.in_(delivery_statuses))
    if date_from is not None:
        statement = statement.where(CoreOrder.inserted_at >= date_from)
    if date_to is not None:
        statement = statement.where(CoreOrder.inserted_at <= date_to)
    if min_total is not None:
        statement = statement.where(CoreOrder.total_price >= min_total)
    if max_total is not None:
        statement = statement.where(CoreOrder.total_price <= max_total)
    if has_tracking is not None:
        tracking_condition = _has_text(CoreOrder.tracking_code)
        statement = statement.where(
            tracking_condition if has_tracking else ~tracking_condition
        )
    if sent_to_carrier is not None:
        sent_condition = CoreOrder.sent_to_carrier_at.is_not(None)
        statement = statement.where(
            sent_condition if sent_to_carrier else ~sent_condition
        )
    if returned is not None:
        returned_condition = or_(
            _has_text(CoreOrder.returned_reason),
            func.coalesce(CoreOrder.return_fee, 0) > 0,
            func.coalesce(CoreOrder.status_name, "").ilike("%hoàn%"),
            func.coalesce(CoreOrder.delivery_status, "").ilike("%hoàn%"),
        )
        statement = statement.where(
            returned_condition if returned else ~returned_condition
        )

    clean_product = product.strip() if product else ""
    if clean_product:
        escaped_product = escape_like(clean_product)
        statement = statement.where(
            select(1)
            .where(
                CoreOrderItem.shop_id == CoreOrder.shop_id,
                CoreOrderItem.source_order_id == CoreOrder.source_order_id,
                CoreOrderItem.product_name.ilike(
                    f"%{escaped_product}%", escape="\\"
                ),
            )
            .exists()
        )

    return statement


def search_orders(
    session: Session,
    *,
    query: str | None = None,
    shop_id: str | list[str] | None = None,
    page_id: str | list[str] | None = None,
    status: int | list[int] | None = None,
    business_status: str | list[str] | None = None,
    carrier_name: str | list[str] | None = None,
    delivery_status: str | list[str] | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    min_total: Decimal | None = None,
    max_total: Decimal | None = None,
    has_tracking: bool | None = None,
    sent_to_carrier: bool | None = None,
    returned: bool | None = None,
    product: str | None = None,
    page_number: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    statement = filtered_orders_statement(
        query=query,
        shop_id=shop_id,
        page_id=page_id,
        status=status,
        business_status=business_status,
        carrier_name=carrier_name,
        delivery_status=delivery_status,
        date_from=date_from,
        date_to=date_to,
        min_total=min_total,
        max_total=max_total,
        has_tracking=has_tracking,
        sent_to_carrier=sent_to_carrier,
        returned=returned,
        product=product,
    )

    summary_source = statement.with_only_columns(
        CoreOrder.total_price,
        business_status_expression().label("business_status"),
        maintain_column_froms=True,
    ).order_by(None).subquery()
    summary = session.execute(
        select(
            func.count().label("total_orders"),
            func.coalesce(func.sum(summary_source.c.total_price), 0).label(
                "total_revenue"
            ),
            func.count()
            .filter(summary_source.c.business_status == "delivered")
            .label("delivered_orders"),
            func.count()
            .filter(summary_source.c.business_status == "returned")
            .label("returned_orders"),
            func.count()
            .filter(summary_source.c.business_status == "canceled")
            .label("canceled_orders"),
        ).select_from(summary_source)
    ).one()
    total = summary.total_orders
    offset = (page_number - 1) * page_size
    rows = session.execute(
        statement.order_by(CoreOrder.source_updated_at.desc().nullslast())
        .offset(offset)
        .limit(page_size)
    ).all()

    items: list[dict[str, Any]] = []
    for order, customer in rows:
        normalized_status = classify_business_status(
            status=order.status,
            status_name=order.status_name,
            delivery_status=order.delivery_status,
            sent_to_carrier_at=order.sent_to_carrier_at,
        )
        items.append(
            {
                "shop_id": order.shop_id,
                "order_id": order.source_order_id,
                "page_id": order.source_page_id,
                "page_name": order.page_name,
                "status": order.status,
                "status_name": order.status_name,
                "business_status": normalized_status,
                "business_status_label": business_status_label(normalized_status),
                "tracking_code": order.tracking_code,
                "carrier_name": order.carrier_name,
                "delivery_status": order.delivery_status,
                "sent_to_carrier_at": order.sent_to_carrier_at,
                "returned_reason": order.returned_reason,
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
        "summary": {
            "total_orders": summary.total_orders,
            "total_revenue": summary.total_revenue,
            "delivered_orders": summary.delivered_orders,
            "returned_orders": summary.returned_orders,
            "canceled_orders": summary.canceled_orders,
        },
        "pagination": {
            "page_number": page_number,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }

