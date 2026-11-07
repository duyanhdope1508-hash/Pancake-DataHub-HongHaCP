from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

from app.abuse import consume_quota
from app.models import UsageQuota


def test_new_quota_bucket_counts_usage() -> None:
    session = Mock()
    now = datetime(2026, 11, 6, 8, 0, tzinfo=UTC)
    bucket = UsageQuota(
        key_hash="c" * 64,
        user_id="staff-1",
        action="orders.list.rows",
        window_started_at=now,
        usage_count=0,
    )
    session.scalar.return_value = bucket

    decision = consume_quota(
        session,
        user_id="staff-1",
        action="orders.list.rows",
        amount=20,
        limit=2_000,
        window_seconds=3_600,
        now=now,
    )

    assert decision.allowed is True
    assert decision.used == 20
    assert bucket.usage_count == 20
    session.execute.assert_called_once()


def test_quota_denial_does_not_increase_usage_and_is_log_throttled() -> None:
    now = datetime(2026, 11, 6, 8, 30, tzinfo=UTC)
    bucket = UsageQuota(
        key_hash="a" * 64,
        user_id="staff-1",
        action="orders.view_detail",
        window_started_at=now - timedelta(minutes=30),
        usage_count=120,
    )
    session = Mock()
    session.scalar.return_value = bucket

    first = consume_quota(
        session,
        user_id="staff-1",
        action="orders.view_detail",
        amount=1,
        limit=120,
        window_seconds=3_600,
        now=now,
    )
    second = consume_quota(
        session,
        user_id="staff-1",
        action="orders.view_detail",
        amount=1,
        limit=120,
        window_seconds=3_600,
        now=now + timedelta(minutes=1),
    )

    assert first.allowed is False
    assert first.should_log_denial is True
    assert second.allowed is False
    assert second.should_log_denial is False
    assert bucket.usage_count == 120


def test_expired_quota_window_resets_before_counting() -> None:
    now = datetime(2026, 11, 6, 10, 0, tzinfo=UTC)
    bucket = UsageQuota(
        key_hash="b" * 64,
        user_id="staff-1",
        action="orders.list.rows",
        window_started_at=now - timedelta(hours=2),
        usage_count=2_000,
        last_denied_at=now - timedelta(hours=1),
    )
    session = Mock()
    session.scalar.return_value = bucket

    decision = consume_quota(
        session,
        user_id="staff-1",
        action="orders.list.rows",
        amount=20,
        limit=2_000,
        window_seconds=3_600,
        now=now,
    )

    assert decision.allowed is True
    assert bucket.usage_count == 20
    assert bucket.last_denied_at is None


def test_quota_alerts_once_when_eighty_percent_is_crossed() -> None:
    now = datetime(2026, 11, 6, 10, 0, tzinfo=UTC)
    bucket = UsageQuota(
        key_hash="d" * 64,
        user_id="staff-1",
        action="orders.list.rows.burst",
        window_started_at=now,
        usage_count=220,
    )
    session = Mock()
    session.scalar.return_value = bucket

    first = consume_quota(
        session,
        user_id="staff-1",
        action="orders.list.rows.burst",
        amount=20,
        limit=300,
        window_seconds=300,
        now=now,
    )
    second = consume_quota(
        session,
        user_id="staff-1",
        action="orders.list.rows.burst",
        amount=20,
        limit=300,
        window_seconds=300,
        now=now + timedelta(seconds=1),
    )

    assert first.should_alert is True
    assert first.used == 240
    assert second.should_alert is False
