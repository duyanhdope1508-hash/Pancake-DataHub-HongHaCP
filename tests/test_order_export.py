from datetime import UTC, datetime

import pytest

from app.order_export import ExportLimitExceeded, _excel_datetime


def test_export_limit_error_preserves_counts() -> None:
    error = ExportLimitExceeded(100_001, 100_000)
    assert error.total_orders == 100_001
    assert error.max_orders == 100_000


def test_excel_datetime_removes_timezone_after_local_conversion() -> None:
    value = _excel_datetime(datetime(2026, 11, 5, 0, 0, tzinfo=UTC))
    assert value == datetime(2026, 11, 5, 7, 0)
    assert value.tzinfo is None


def test_excel_datetime_keeps_missing_value() -> None:
    assert _excel_datetime(None) is None


def test_xlsxwriter_dependency_is_available() -> None:
    pytest.importorskip("xlsxwriter")
