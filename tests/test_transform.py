from decimal import Decimal

from app.transform import extract_page, normalize_phone, parse_datetime, parse_decimal


def test_normalize_phone_keeps_digits_only() -> None:
    assert normalize_phone("(+84) 912-345-678") == "84912345678"


def test_normalize_phone_handles_missing_value() -> None:
    assert normalize_phone(None) is None
    assert normalize_phone("---") is None


def test_parse_datetime_accepts_utc_suffix() -> None:
    result = parse_datetime("2026-11-02T12:30:00Z")
    assert result is not None
    assert result.isoformat() == "2026-11-02T12:30:00+00:00"


def test_parse_datetime_rejects_invalid_value() -> None:
    assert parse_datetime("not-a-date") is None


def test_parse_decimal_preserves_precision() -> None:
    assert parse_decimal("12345.67") == Decimal("12345.67")
    assert parse_decimal(True) is None


def test_extract_page_uses_top_level_id_and_nested_name() -> None:
    assert extract_page(
        {"page_id": "page-123", "page": {"id": "fallback", "name": "Main Page"}}
    ) == ("page-123", "Main Page")


def test_extract_page_falls_back_to_nested_id() -> None:
    assert extract_page({"page": {"id": 123, "name": "Main Page"}}) == (
        "123",
        "Main Page",
    )

