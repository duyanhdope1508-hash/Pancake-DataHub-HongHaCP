from datetime import UTC, datetime

import pytest

from app.order_export import (
    ExportLimitExceeded,
    _excel_datetime,
    cleanup_export_artifact,
    export_limit_for_role,
)


def test_export_limit_error_preserves_counts() -> None:
    error = ExportLimitExceeded(100_001, 100_000)
    assert error.total_orders == 100_001
    assert error.max_orders == 100_000


def test_staff_export_is_limited_to_five_hundred_orders() -> None:
    assert export_limit_for_role("staff") == 500
    assert export_limit_for_role("admin") == 100_000


def test_excel_datetime_removes_timezone_after_local_conversion() -> None:
    value = _excel_datetime(datetime(2026, 11, 5, 0, 0, tzinfo=UTC))
    assert value == datetime(2026, 11, 5, 7, 0)
    assert value.tzinfo is None


def test_excel_datetime_keeps_missing_value() -> None:
    assert _excel_datetime(None) is None


def test_xlsxwriter_dependency_is_available() -> None:
    pytest.importorskip("xlsxwriter")


def test_export_artifact_cleanup_removes_its_private_directory(tmp_path) -> None:
    export_dir = tmp_path / "pancake-export-test"
    export_dir.mkdir()
    output = export_dir / "orders.xlsx"
    temporary_part = export_dir / "worksheet.xml"
    output.write_bytes(b"xlsx")
    temporary_part.write_bytes(b"xml")

    cleanup_export_artifact(output)

    assert not export_dir.exists()
