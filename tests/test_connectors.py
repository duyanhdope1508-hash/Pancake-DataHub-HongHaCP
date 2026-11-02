import json
from pathlib import Path

import pytest

from app.config import Settings
from app.connectors import load_connectors


def test_falls_back_to_legacy_environment() -> None:
    settings = Settings(
        _env_file=None,
        pancake_api_key="a-valid-legacy-key",
        pancake_shop_ids="shop-1,shop-2",
        pancake_connectors_file=Path("missing-connectors.json"),
    )

    connectors = load_connectors(settings)

    assert len(connectors) == 1
    assert connectors[0].name == "legacy-env"
    assert connectors[0].shop_ids == frozenset({"shop-1", "shop-2"})
    assert "a-valid-legacy-key" not in repr(connectors[0])


def test_loads_multiple_connectors_from_secret_file(tmp_path: Path) -> None:
    path = tmp_path / "connectors.json"
    path.write_text(
        json.dumps(
            {
                "connectors": [
                    {"name": "one", "shop_ids": ["1"], "api_key": "valid-key-one"},
                    {"name": "two", "shop_ids": ["2"], "api_key": "valid-key-two"},
                ]
            }
        ),
        encoding="utf-8",
    )
    settings = Settings(_env_file=None, pancake_connectors_file=path)

    connectors = load_connectors(settings)

    assert [connector.name for connector in connectors] == ["one", "two"]
    assert connectors[1].shop_ids == frozenset({"2"})


def test_rejects_shop_assigned_to_multiple_connectors(tmp_path: Path) -> None:
    path = tmp_path / "connectors.json"
    path.write_text(
        json.dumps(
            {
                "connectors": [
                    {"name": "one", "shop_ids": ["1"], "api_key": "valid-key-one"},
                    {"name": "two", "shop_ids": ["1"], "api_key": "valid-key-two"},
                ]
            }
        ),
        encoding="utf-8",
    )
    settings = Settings(_env_file=None, pancake_connectors_file=path)

    with pytest.raises(ValueError, match="multiple connectors"):
        load_connectors(settings)
