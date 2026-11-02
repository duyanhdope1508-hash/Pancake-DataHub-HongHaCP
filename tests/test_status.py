from datetime import UTC, datetime

from app.status import _isoformat


def test_isoformat_for_timestamp() -> None:
    value = datetime(2026, 11, 2, 12, 30, tzinfo=UTC)
    assert _isoformat(value) == "2026-11-02T12:30:00+00:00"


def test_isoformat_for_missing_timestamp() -> None:
    assert _isoformat(None) is None

