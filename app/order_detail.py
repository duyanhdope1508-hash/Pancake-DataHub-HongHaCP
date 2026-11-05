from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.business_status import business_status_label, classify_business_status
from app.models import CoreCustomer, CoreOrder, CoreOrderItem
from app.search import mask_phone


class OrderNotFoundError(LookupError):
    pass


class AmbiguousOrderError(LookupError):
    pass


def receipt_status(status_name: str | None) -> str:
    return {
        "delivered": "received",
        "returning": "returning",
        "returned": "returned",
        "canceled": "canceled",
    }.get(status_name or "", "pending")


def serialize_order_detail(
    order: CoreOrder,
    customer: CoreCustomer | None,
    items: list[CoreOrderItem],
) -> dict[str, Any]:
    normalized_status = classify_business_status(
        status=order.status,
        status_name=order.status_name,
        delivery_status=order.delivery_status,
        sent_to_carrier_at=order.sent_to_carrier_at,
    )
    return {
        "shop_id": order.shop_id,
        "order_id": order.source_order_id,
        "page_id": order.source_page_id,
        "page_name": order.page_name,
        "status": order.status,
        "status_name": order.status_name,
        "business_status": normalized_status,
        "business_status_label": business_status_label(normalized_status),
        "total_price": order.total_price,
        "total_quantity": order.total_quantity,
        "currency": order.currency,
        "inserted_at": order.inserted_at,
        "updated_at": order.source_updated_at,
        "shipping": {
            "recipient_name": order.shipping_name,
            "phone_masked": mask_phone(order.shipping_phone),
            "address": order.shipping_address,
            "tracking_code": order.tracking_code,
            "tracking_link": order.tracking_link,
            "shipping_fee": order.shipping_fee,
            "carrier_name": order.carrier_name,
            "delivery_status": order.delivery_status,
            "sent_to_carrier": bool(order.sent_to_carrier_at),
            "sent_to_carrier_at": order.sent_to_carrier_at,
            "receipt_status": receipt_status(order.status_name),
            "returned_reason": order.returned_reason,
            "return_fee": order.return_fee,
        },
        "customer": {
            "name": customer.name if customer else None,
            "phone_masked": mask_phone(customer.primary_phone) if customer else None,
        },
        "items": [
            {
                "line_number": item.line_number,
                "item_id": item.source_item_id,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_discount": item.total_discount,
            }
            for item in items
        ],
    }


def get_order_detail(
    session: Session,
    *,
    order_id: str,
    shop_id: str | None = None,
) -> dict[str, Any]:
    statement = (
        select(CoreOrder, CoreCustomer)
        .outerjoin(
            CoreCustomer,
            and_(
                CoreCustomer.shop_id == CoreOrder.shop_id,
                CoreCustomer.source_customer_id == CoreOrder.source_customer_id,
            ),
        )
        .where(CoreOrder.source_order_id == order_id)
    )
    if shop_id:
        statement = statement.where(CoreOrder.shop_id == shop_id)

    rows = session.execute(statement).all()
    if not rows:
        raise OrderNotFoundError(order_id)
    if len(rows) > 1:
        raise AmbiguousOrderError(order_id)

    order, customer = rows[0]
    items = list(
        session.scalars(
            select(CoreOrderItem)
            .where(
                CoreOrderItem.shop_id == order.shop_id,
                CoreOrderItem.source_order_id == order.source_order_id,
            )
            .order_by(CoreOrderItem.line_number.asc())
        ).all()
    )
    return serialize_order_detail(order, customer, items)

