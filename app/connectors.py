import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import Settings


@dataclass(frozen=True, slots=True)
class PancakeConnector:
    name: str
    shop_ids: frozenset[str]
    api_key: str = field(repr=False)


def _clean_key(value: Any, *, source: str) -> str:
    key = str(value or "").strip()
    if not key or key == "replace_with_your_key" or len(key) < 10:
        raise ValueError(f"Invalid API key in {source}")
    return key


def _clean_shop_ids(value: Any, *, source: str) -> frozenset[str]:
    if not isinstance(value, list):
        raise TypeError(f"shop_ids must be a list in {source}")
    shop_ids = frozenset(str(item).strip() for item in value if str(item).strip())
    if not shop_ids:
        raise ValueError(f"shop_ids cannot be empty in {source}")
    return shop_ids


def _from_file(path: Path) -> list[PancakeConnector]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in connector file: {path}") from exc

    records = payload.get("connectors") if isinstance(payload, dict) else None
    if not isinstance(records, list) or not records:
        raise ValueError(f"Connector file has no connectors: {path}")

    connectors: list[PancakeConnector] = []
    names: set[str] = set()
    assigned_shops: set[str] = set()
    for index, record in enumerate(records, start=1):
        source = f"connector #{index} in {path}"
        if not isinstance(record, dict):
            raise TypeError(f"Invalid {source}")
        name = str(record.get("name") or "").strip()
        if not name or name in names:
            raise ValueError(f"Connector name is missing or duplicated in {source}")
        shop_ids = _clean_shop_ids(record.get("shop_ids"), source=source)
        overlap = assigned_shops.intersection(shop_ids)
        if overlap:
            raise ValueError(f"Shop ID is assigned to multiple connectors: {sorted(overlap)}")

        connectors.append(
            PancakeConnector(
                name=name,
                api_key=_clean_key(record.get("api_key"), source=source),
                shop_ids=shop_ids,
            )
        )
        names.add(name)
        assigned_shops.update(shop_ids)
    return connectors


def load_connectors(settings: Settings) -> list[PancakeConnector]:
    path = settings.pancake_connectors_file
    if path.is_file():
        return _from_file(path)

    return [
        PancakeConnector(
            name="legacy-env",
            api_key=settings.require_pancake_key(),
            shop_ids=frozenset(settings.shop_allowlist),
        )
    ]
