from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from typing import Any

from sqlalchemy import and_, func, or_, select, tuple_
from sqlalchemy.orm import Session, aliased

from app.business_status import (
    business_status_expression,
    business_status_label,
    classify_business_status,
)
from app.delivery_status import delivery_status_label
from app.models import CoreCustomer, CoreOrder, CoreOrderItem, Shop
from app.transform import normalize_customer_name


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
    order_keys: list[tuple[str, str]] | None = None,
    include_customer: bool = True,
) -> Any:
    if include_customer:
        statement = select(CoreOrder, CoreCustomer).outerjoin(
            CoreCustomer,
            and_(
                CoreCustomer.shop_id == CoreOrder.shop_id,
                CoreCustomer.source_customer_id == CoreOrder.source_customer_id,
            ),
        )
    else:
        statement = select(CoreOrder)

    shop_ids = _filter_values(shop_id)
    has_shop_constraint = shop_id is not None
    clean_query = query.strip() if query else ""
    if clean_query:
        escaped_query = escape_like(clean_query)
        normalized_name = normalize_customer_name(clean_query)
        exact_order = aliased(CoreOrder)
        exact_name_exists = (
            select(1)
            .select_from(exact_order)
            .where(exact_order.customer_name_search == normalized_name)
        )
        if has_shop_constraint:
            exact_name_exists = exact_name_exists.where(exact_order.shop_id.in_(shop_ids))
        exact_name_exists = exact_name_exists.exists()
        statement = statement.where(
            or_(
                CoreOrder.customer_name_search == normalized_name,
                and_(
                    ~exact_name_exists,
                    CoreOrder.search_text.ilike(
                        f"%{escaped_query}%", escape="\\"
                    ),
                ),
            )
        )

    if has_shop_constraint:
        statement = statement.where(CoreOrder.shop_id.in_(shop_ids))
    if order_keys is not None:
        statement = statement.where(
            tuple_(CoreOrder.shop_id, CoreOrder.source_order_id).in_(order_keys)
        )
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
    include_summary: bool = True,
    sort_by: str = "recent",
    known_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    filter_arguments = {
        "query": query,
        "shop_id": shop_id,
        "page_id": page_id,
        "status": status,
        "business_status": business_status,
        "carrier_name": carrier_name,
        "delivery_status": delivery_status,
        "date_from": date_from,
        "date_to": date_to,
        "min_total": min_total,
        "max_total": max_total,
        "has_tracking": has_tracking,
        "sent_to_carrier": sent_to_carrier,
        "returned": returned,
        "product": product,
    }
    statement = filtered_orders_statement(**filter_arguments)
    aggregate_statement = filtered_orders_statement(
        **filter_arguments,
        include_customer=False,
    )

    summary = None
    if include_summary:
        summary = (
            dict(known_summary)
            if known_summary is not None
            else summarize_filtered_orders(session, aggregate_statement)
        )
    if summary is not None:
        total = summary["total_orders"]
    elif known_summary is not None:
        total = known_summary["total_orders"]
    else:
        count_source = aggregate_statement.with_only_columns(
            CoreOrder.shop_id,
            CoreOrder.source_order_id,
            maintain_column_froms=True,
        ).order_by(None).subquery()
        total = session.scalar(select(func.count()).select_from(count_source)) or 0

    offset = (page_number - 1) * page_size
    if sort_by == "customer":
        ordering = (
            CoreOrder.customer_group_key.asc(),
            CoreOrder.source_updated_at.desc().nullslast(),
        )
    elif sort_by == "oldest":
        ordering = (CoreOrder.source_updated_at.asc().nullslast(),)
    elif sort_by == "value_desc":
        ordering = (
            CoreOrder.total_price.desc().nullslast(),
            CoreOrder.source_updated_at.desc().nullslast(),
        )
    else:
        ordering = (CoreOrder.source_updated_at.desc().nullslast(),)
    rows = session.execute(
        statement.order_by(*ordering).offset(offset).limit(page_size)
    ).all()
    shop_names = dict(
        session.execute(
            select(Shop.id, Shop.name).where(
                Shop.id.in_({order.shop_id for order, _customer in rows})
            )
        ).all()
    )

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
                "shop_name": shop_names.get(order.shop_id, order.shop_id),
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
                "delivery_status_label": delivery_status_label(order.delivery_status),
                "sent_to_carrier_at": order.sent_to_carrier_at,
                "returned_reason": order.returned_reason,
                "total_price": order.total_price,
                "total_quantity": order.total_quantity,
                "currency": order.currency,
                "inserted_at": order.inserted_at,
                "updated_at": order.source_updated_at,
                "customer_name": customer.name if customer else None,
                "customer_phone": (
                    customer.primary_phone
                    if customer and customer.primary_phone
                    else order.shipping_phone
                ),
                "customer_group_token": sha256(
                    order.customer_group_key.encode("utf-8")
                ).hexdigest()[:12],
            }
        )

    return {
        "items": items,
        "summary": summary,
        "pagination": {
            "page_number": page_number,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


def summarize_filtered_orders(session: Session, statement: Any) -> dict[str, Any]:
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
    return {
        "total_orders": summary.total_orders,
        "total_revenue": summary.total_revenue,
        "delivered_orders": summary.delivered_orders,
        "returned_orders": summary.returned_orders,
        "canceled_orders": summary.canceled_orders,
    }


def summarize_orders(session: Session, **filters: Any) -> dict[str, Any]:
    return summarize_filtered_orders(
        session,
        filtered_orders_statement(**filters, include_customer=False),
    )

