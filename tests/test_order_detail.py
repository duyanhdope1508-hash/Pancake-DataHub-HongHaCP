from types import SimpleNamespace

from app.order_detail import serialize_order_detail


def test_order_detail_masks_phone_and_omits_address() -> None:
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

    result = serialize_order_detail(order, customer, items)

    assert result["customer"]["phone_masked"] == "******5678"
    assert "shipping_address" not in result
    assert "primary_phone" not in str(result)
    assert result["items"][0]["product_name"] == "Product"

