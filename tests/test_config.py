import pytest
from pydantic import ValidationError

from app.config import Settings


def test_sync_defaults_to_one_page() -> None:
    settings = Settings(_env_file=None)
    assert settings.pancake_max_pages == 1


def test_sync_page_limit_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, pancake_max_pages=0)

