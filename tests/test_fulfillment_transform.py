from app.transform import parse_datetime, parse_decimal


def test_fulfillment_values_use_existing_parsers() -> None:
    assert parse_decimal("30000") is not None
    assert parse_datetime("2026-11-02T10:00:00Z") is not None
