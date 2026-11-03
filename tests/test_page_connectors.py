import json
from pathlib import Path

import pytest

from app.config import Settings
from app.page_connectors import (
    PancakePageConnector,
    load_page_connectors,
    merge_page_connector,
    write_page_connectors,
)


def test_missing_page_connector_file_returns_empty_list(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        pancake_pages_connectors_file=tmp_path / "missing.json",
    )
    assert load_page_connectors(settings) == []


def test_loads_page_connectors_without_exposing_token_in_repr(tmp_path: Path) -> None:
    path = tmp_path / "pages.json"
    path.write_text(
        json.dumps(
            {
                "connectors": [
                    {
                        "page_id": "123456",
                        "page_access_token": "valid-page-access-token",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    settings = Settings(_env_file=None, pancake_pages_connectors_file=path)

    connectors = load_page_connectors(settings)

    assert connectors[0].page_id == "123456"
    assert "valid-page-access-token" not in repr(connectors[0])


def test_merge_page_connector_rejects_duplicate_page() -> None:
    existing = PancakePageConnector(
        page_id="123456",
        page_access_token="valid-existing-token",
    )
    with pytest.raises(ValueError, match="already configured"):
        merge_page_connector(
            [existing],
            page_id="123456",
            page_access_token="valid-new-token",
        )


def test_write_page_connectors_is_atomic(tmp_path: Path) -> None:
    path = tmp_path / "pages.json"
    connector = PancakePageConnector(
        page_id="123456",
        page_access_token="valid-page-access-token",
    )

    write_page_connectors(path, [connector])

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["connectors"][0]["page_id"] == "123456"
    assert payload["connectors"][0]["page_access_token"] == "valid-page-access-token"
    assert not path.with_name("pages.json.tmp").exists()
