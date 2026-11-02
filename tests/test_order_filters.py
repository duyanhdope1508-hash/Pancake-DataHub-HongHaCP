from app.order_filters import order_filters


def test_order_filters_is_callable() -> None:
    assert callable(order_filters)

