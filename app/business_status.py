from datetime import datetime
from typing import Any

from sqlalchemy import case, func, or_

from app.models import CoreOrder

BUSINESS_STATUS_LABELS = {
    "not_sent": "Chưa gửi",
    "in_transit": "Đang giao",
    "delivered": "Giao thành công",
    "returned": "Hoàn",
    "canceled": "Hủy",
}

BUSINESS_STATUS_ORDER = tuple(BUSINESS_STATUS_LABELS)


def classify_business_status(
    *,
    status: int | None,
    status_name: str | None,
    delivery_status: str | None,
    sent_to_carrier_at: datetime | None,
) -> str:
    order_state = (status_name or "").strip().lower()
    delivery_state = (delivery_status or "").strip().lower()

    if status == 6 or order_state == "canceled":
        return "canceled"
    if status in {4, 5} or order_state in {"returning", "returned"}:
        return "returned"
    if status in {3, 16} or order_state in {"delivered", "received_money"}:
        return "delivered"
    if delivery_state == "canceled":
        return "canceled"
    if delivery_state in {"returning", "returned"}:
        return "returned"
    if delivery_state == "delivered":
        return "delivered"
    if (
        status in {2, 9}
        or order_state in {"shipped", "pending"}
        or delivery_state
        in {
            "request_received",
            "on_the_way",
            "out_for_delivery",
            "undeliverable",
        }
        or sent_to_carrier_at is not None
    ):
        return "in_transit"
    return "not_sent"


def business_status_label(value: str) -> str:
    return BUSINESS_STATUS_LABELS.get(value, value)


def business_status_expression() -> Any:
    order_state = func.lower(func.coalesce(CoreOrder.status_name, ""))
    delivery_state = func.lower(func.coalesce(CoreOrder.delivery_status, ""))
    return case(
        (or_(CoreOrder.status == 6, order_state == "canceled"), "canceled"),
        (
            or_(
                CoreOrder.status.in_([4, 5]),
                order_state.in_(["returning", "returned"]),
            ),
            "returned",
        ),
        (
            or_(
                CoreOrder.status.in_([3, 16]),
                order_state.in_(["delivered", "received_money"]),
            ),
            "delivered",
        ),
        (delivery_state == "canceled", "canceled"),
        (delivery_state.in_(["returning", "returned"]), "returned"),
        (delivery_state == "delivered", "delivered"),
        (
            or_(
                CoreOrder.status.in_([2, 9]),
                order_state.in_(["shipped", "pending"]),
                delivery_state.in_(
                    [
                        "request_received",
                        "on_the_way",
                        "out_for_delivery",
                        "undeliverable",
                    ]
                ),
                CoreOrder.sent_to_carrier_at.is_not(None),
            ),
            "in_transit",
        ),
        else_="not_sent",
    )
