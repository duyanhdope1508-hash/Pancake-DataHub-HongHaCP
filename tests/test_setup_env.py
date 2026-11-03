from pathlib import Path

import pytest

from app.setup_env import build_env, write_env


def test_build_env_contains_required_settings() -> None:
    content = build_env("secret-api-key", "database-password")
    assert "PANCAKE_API_KEY=secret-api-key" in content
    assert "POSTGRES_PASSWORD=database-password" in content
    assert "@127.0.0.1:15432/pancake_data" in content
    assert "PANCAKE_API_BASE_URL=https://pos.pages.fm/api/v1" in content
    assert "PANCAKE_PAGES_CONNECTORS_FILE=secrets/pancake_pages_connectors.json" in content
    assert "PANCAKE_MAX_PAGES=1" in content


def test_write_env_refuses_to_replace_existing_file(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("existing=true\n", encoding="utf-8")

    with pytest.raises(FileExistsError):
        write_env(tmp_path, "valid-api-key-value")

    assert env_path.read_text(encoding="utf-8") == "existing=true\n"


def test_write_env_creates_git_ignored_secret_file(tmp_path: Path) -> None:
    env_path = write_env(tmp_path, "valid-api-key-value")
    content = env_path.read_text(encoding="utf-8")

    assert "PANCAKE_API_KEY=valid-api-key-value" in content
    assert "POSTGRES_PASSWORD=" in content
    assert "replace_with_your_key" not in content


def test_write_env_rejects_multiline_key(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        write_env(tmp_path, "valid-key\ninjected=true")

