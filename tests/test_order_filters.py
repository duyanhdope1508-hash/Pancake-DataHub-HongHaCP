from inspect import signature
from pathlib import Path

from app.order_filters import order_filters


def test_order_filters_is_callable() -> None:
    assert callable(order_filters)
    assert "shop_ids" in signature(order_filters).parameters


def test_filter_metadata_includes_fulfillment_dimensions() -> None:
    source = Path("app/order_filters.py").read_text(encoding="utf-8")
    assert '"carriers"' in source
    assert '"business_statuses"' in source
    assert '"delivery_statuses"' in source
    assert '"date_range"' in source

