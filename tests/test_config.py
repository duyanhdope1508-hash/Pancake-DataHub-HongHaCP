import pytest
from pydantic import ValidationError

from app.config import Settings


def test_sync_defaults_to_one_page() -> None:
    settings = Settings(_env_file=None)
    assert settings.pancake_start_page == 1
    assert settings.pancake_max_pages == 1
    assert settings.pancake_sync_concurrency == 4
    assert settings.pancake_resume_backfill is False
    assert settings.pancake_sync_interval_seconds == 300
    assert settings.auth_session_hours == 12
    assert settings.auth_cookie_secure is False
    assert settings.auth_login_max_failures == 5
    assert settings.auth_login_window_seconds == 900
    assert settings.auth_login_lock_seconds == 900
    assert settings.auth_staff_max_sessions == 2
    assert settings.staff_order_rows_per_hour == 2_000
    assert settings.staff_order_details_per_hour == 120
    assert settings.staff_exports_per_hour == 5
    assert settings.staff_export_rows_per_day == 2_000
    assert settings.audit_detail_dedup_seconds == 600


def test_sync_page_limit_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, pancake_max_pages=0)


def test_sync_interval_must_be_at_least_thirty_seconds() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, pancake_sync_interval_seconds=29)


def test_sync_concurrency_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, pancake_sync_concurrency=0)


def test_sync_start_page_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, pancake_start_page=0)

