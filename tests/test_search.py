from inspect import signature
from pathlib import Path

from app.search import escape_like, filtered_orders_statement, search_orders


def test_escape_like_prevents_wildcard_input() -> None:
    assert escape_like(r"100%_done\now") == r"100\%\_done\\now"


def test_search_supports_shop_filter() -> None:
    assert "shop_id" in signature(search_orders).parameters


def test_empty_shop_scope_does_not_mean_unrestricted_access() -> None:
    statement = filtered_orders_statement(shop_id=[])

    assert statement.compile().params


def test_search_can_defer_filtered_summary() -> None:
    parameter = signature(search_orders).parameters["include_summary"]
    assert parameter.default is True


def test_search_supports_customer_group_sorting() -> None:
    parameter = signature(search_orders).parameters["sort_by"]
    assert parameter.default == "recent"


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
    assert '"shop_name"' in source


def test_migrations_add_trigram_indexes_for_keyword_search() -> None:
    source = Path("app/migrations.py").read_text(encoding="utf-8")
    assert "CREATE EXTENSION IF NOT EXISTS pg_trgm" in source
    for index_name in (
        "ix_core_orders_order_id_trgm",
        "ix_core_orders_tracking_code_trgm",
        "ix_core_orders_shipping_address_trgm",
        "ix_core_customers_name_trgm",
        "ix_core_customers_phone_trgm",
        "ix_core_order_items_product_name_trgm",
    ):
        assert index_name in source


def test_search_prefers_exact_customer_name_before_broad_text() -> None:
    source = Path("app/search.py").read_text(encoding="utf-8")
    assert "exact_name_exists" in source
    assert "customer_name_search == normalized_name" in source

