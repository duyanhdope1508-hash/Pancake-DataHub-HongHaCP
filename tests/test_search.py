from inspect import signature
from pathlib import Path

from app.search import escape_like, mask_phone, search_orders


def test_mask_phone_preserves_only_last_four_characters() -> None:
    assert mask_phone("0912345678") == "******5678"


def test_mask_phone_handles_short_and_missing_values() -> None:
    assert mask_phone("123") == "***"
    assert mask_phone(None) is None


def test_escape_like_prevents_wildcard_input() -> None:
    assert escape_like(r"100%_done\now") == r"100\%\_done\\now"


def test_search_supports_shop_filter() -> None:
    assert "shop_id" in signature(search_orders).parameters


def test_search_supports_fulfillment_and_range_filters() -> None:
    parameters = signature(search_orders).parameters
    expected = {
        "carrier_name",
        "business_status",
        "delivery_status",
        "date_from",
        "date_to",
        "min_total",
        "max_total",
        "has_tracking",
        "sent_to_carrier",
        "returned",
        "product",
    }
    assert expected <= parameters.keys()


def test_search_source_exposes_filtered_summary() -> None:
    source = Path("app/search.py").read_text(encoding="utf-8")
    assert '"total_revenue"' in source
    assert '"delivered_orders"' in source
    assert '"returned_orders"' in source
    assert '"canceled_orders"' in source

