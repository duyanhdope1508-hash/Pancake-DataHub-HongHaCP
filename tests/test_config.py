import pytest
from pydantic import ValidationError

from app.config import Settings


def test_sync_defaults_to_one_page() -> None:
    settings = Settings(_env_file=None)
    assert settings.database_pool_size == 5
    assert settings.database_max_overflow == 2
    assert settings.database_pool_timeout_seconds == 15
    assert settings.database_pool_recycle_seconds == 1_800
    assert settings.pancake_start_page == 1
    assert settings.pancake_max_pages == 1
    assert settings.pancake_incremental_max_pages == 100
    assert settings.pancake_incremental_unchanged_pages == 2
    assert settings.telegram_alerts_file.as_posix() == "secrets/telegram_alerts.json"
    assert settings.pancake_sync_concurrency == 4
    assert settings.pancake_resume_backfill is False
    assert settings.pancake_sync_interval_seconds == 43_200
    assert settings.auth_session_hours == 12
    assert settings.auth_cookie_secure is False
    assert settings.trusted_hosts == "*"
    assert settings.auth_login_max_failures == 5
    assert settings.auth_login_window_seconds == 900
    assert settings.auth_login_lock_seconds == 900
    assert settings.staff_order_rows_per_5_minutes == 300
    assert settings.auth_staff_max_sessions == 2
    assert settings.staff_order_rows_per_hour == 2_000
    assert settings.staff_order_details_per_hour == 120
    assert settings.staff_exports_per_hour == 5
    assert settings.staff_export_rows_per_day == 2_000
    assert settings.export_temp_dir.is_absolute()
    assert settings.audit_detail_dedup_seconds == 600
    assert settings.audit_detail_retention_days == 90
    assert settings.audit_general_retention_days == 365
    assert settings.audit_cleanup_interval_seconds == 86_400


def test_sync_page_limit_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, pancake_max_pages=0)


def test_database_pool_size_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_pool_size=0)


def test_incremental_page_limit_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, pancake_incremental_max_pages=0)


def test_sync_interval_must_be_at_least_thirty_seconds() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, pancake_sync_interval_seconds=29)


def test_sync_concurrency_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, pancake_sync_concurrency=0)


def test_sync_start_page_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, pancake_start_page=0)


def test_trusted_hosts_are_parsed_from_comma_separated_setting() -> None:
    settings = Settings(
        _env_file=None,
        trusted_hosts="data.example.com, api, localhost",
    )

    assert settings.trusted_host_list == ["data.example.com", "api", "localhost"]


def test_empty_trusted_hosts_falls_back_to_wildcard() -> None:
    settings = Settings(_env_file=None, trusted_hosts=" , ")

    assert settings.trusted_host_list == ["*"]
