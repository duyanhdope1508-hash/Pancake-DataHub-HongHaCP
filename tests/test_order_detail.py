from types import SimpleNamespace

from app.order_detail import receipt_status, serialize_order_detail


def test_order_detail_returns_full_contact_data_after_authentication() -> None:
    order = SimpleNamespace(
        shop_id="shop-1",
        source_order_id="order-1",
        source_page_id="page-1",
        page_name="Page One",
        status=1,
        status_name="confirmed",
        total_price=100_000,
        total_quantity=2,
        currency="VND",
        inserted_at=None,
        source_updated_at=None,
        shipping_name="Receiver",
        shipping_phone="0987654321",
        shipping_address="Hanoi",
        tracking_code="TRACK-1",
        tracking_link="https://tracking.example/TRACK-1",
        shipping_fee=30_000,
        carrier_name="Carrier",
        delivery_status="on_the_way",
        sent_to_carrier_at=None,
        returned_reason=None,
        return_fee=0,
    )
    customer = SimpleNamespace(name="Customer", primary_phone="0912345678")
    items = [
        SimpleNamespace(
            line_number=1,
            source_item_id="item-1",
            product_name="Product",
            quantity=2,
            unit_price=50_000,
            total_discount=0,
        )
    ]

    result = serialize_order_detail(order, customer, items, shop_name="Shop One")

    assert result["shop_name"] == "Shop One"
    assert result["customer"]["phone"] == "0912345678"
    assert result["shipping"]["address"] == "Hanoi"
    assert result["shipping"]["phone"] == "0987654321"
    assert result["shipping"]["tracking_code"] == "TRACK-1"
    assert result["shipping"]["delivery_status_label"] == "Đang vận chuyển"
    assert result["business_status"] == "in_transit"
    assert result["business_status_label"] == "Đang giao"
    assert result["items"][0]["product_name"] == "Product"


def test_receipt_status_follows_final_order_state() -> None:
    assert receipt_status("delivered") == "received"
    assert receipt_status("returning") == "returning"
    assert receipt_status("returned") == "returned"
    assert receipt_status("canceled") == "canceled"
    assert receipt_status("shipped") == "pending"

