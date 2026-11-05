from datetime import UTC, datetime

from app.business_status import business_status_label, classify_business_status


def classify(
    status: int | None,
    status_name: str | None,
    delivery_status: str | None = None,
    *,
    sent: bool = False,
) -> str:
    return classify_business_status(
        status=status,
        status_name=status_name,
        delivery_status=delivery_status,
        sent_to_carrier_at=datetime.now(UTC) if sent else None,
    )


def test_final_order_status_has_priority_over_stale_carrier_status() -> None:
    assert classify(6, "canceled", "delivered") == "canceled"
    assert classify(5, "returned", "delivered") == "returned"
    assert classify(3, "delivered", "returning") == "delivered"


def test_delivery_status_fills_missing_order_state() -> None:
    assert classify(None, None, "canceled") == "canceled"
    assert classify(None, None, "returned") == "returned"
    assert classify(None, None, "delivered") == "delivered"
    assert classify(None, None, "on_the_way") == "in_transit"


def test_shipping_signals_distinguish_in_transit_from_not_sent() -> None:
    assert classify(9, "pending", "request_received") == "in_transit"
    assert classify(None, None, sent=True) == "in_transit"
    assert classify(0, "new") == "not_sent"
    assert business_status_label("not_sent") == "Chưa gửi"
