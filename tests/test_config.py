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

