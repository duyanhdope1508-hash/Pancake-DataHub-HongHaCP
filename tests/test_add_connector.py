import json
from pathlib import Path

import pytest

from app.add_connector import merge_connector, write_connectors
from app.connectors import PancakeConnector


def existing_connector() -> PancakeConnector:
    return PancakeConnector(
        name="legacy-env",
        shop_ids=frozenset({"shop-1"}),
        api_key="valid-existing-key",
    )


def test_merge_connector_preserves_existing_connector() -> None:
    connectors = merge_connector(
        [existing_connector()],
        name="shop-two",
        shop_id="shop-2",
        api_key="valid-new-key",
    )

    assert [connector.name for connector in connectors] == ["legacy-env", "shop-two"]
    assert connectors[1].shop_ids == frozenset({"shop-2"})


def test_merge_connector_rejects_duplicate_shop() -> None:
    with pytest.raises(ValueError, match="already configured"):
        merge_connector(
            [existing_connector()],
            name="duplicate-shop",
            shop_id="shop-1",
            api_key="valid-new-key",
        )


def test_write_connectors_creates_expected_secret_file(tmp_path: Path) -> None:
    path = tmp_path / "pancake_connectors.json"
    write_connectors(path, [existing_connector()])

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == {
        "connectors": [
            {
                "name": "legacy-env",
                "shop_ids": ["shop-1"],
                "api_key": "valid-existing-key",
            }
        ]
    }
    assert not path.with_name("pancake_connectors.json.tmp").exists()
