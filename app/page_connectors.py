import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import Settings


@dataclass(frozen=True, slots=True)
class PancakePageConnector:
    page_id: str
    page_access_token: str = field(repr=False)


def clean_page_id(value: Any) -> str:
    page_id = str(value or "").strip()
    if not page_id or re.fullmatch(r"[A-Za-z0-9_.-]+", page_id) is None:
        raise ValueError("Invalid Pancake Page ID")
    return page_id


def clean_page_access_token(value: Any, *, source: str) -> str:
    token = str(value or "").strip()
    if len(token) < 10 or token == "replace_with_your_token":
        raise ValueError(f"Invalid Page Access Token in {source}")
    return token


def load_page_connectors(settings: Settings) -> list[PancakePageConnector]:
    path = settings.pancake_pages_connectors_file
    if not path.is_file():
        return []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in Pancake Pages connector file: {path}") from exc

    records = payload.get("connectors") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        raise TypeError(f"Pancake Pages connector file has no connector list: {path}")

    connectors: list[PancakePageConnector] = []
    page_ids: set[str] = set()
    for index, record in enumerate(records, start=1):
        source = f"connector #{index} in {path}"
        if not isinstance(record, dict):
            raise TypeError(f"Invalid {source}")
        page_id = clean_page_id(record.get("page_id"))
        if page_id in page_ids:
            raise ValueError(f"Page ID is duplicated in {source}: {page_id}")
        connectors.append(
            PancakePageConnector(
                page_id=page_id,
                page_access_token=clean_page_access_token(
                    record.get("page_access_token"), source=source
                ),
            )
        )
        page_ids.add(page_id)
    return connectors


def write_page_connectors(path: Path, connectors: list[PancakePageConnector]) -> None:
    payload = {
        "connectors": [
            {
                "page_id": connector.page_id,
                "page_access_token": connector.page_access_token,
            }
            for connector in connectors
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f"{path.name}.tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def merge_page_connector(
    connectors: list[PancakePageConnector],
    *,
    page_id: str,
    page_access_token: str,
) -> list[PancakePageConnector]:
    clean_id = clean_page_id(page_id)
    if any(connector.page_id == clean_id for connector in connectors):
        raise ValueError(f"Page ID is already configured: {clean_id}")
    return [
        *connectors,
        PancakePageConnector(
            page_id=clean_id,
            page_access_token=clean_page_access_token(
                page_access_token, source=f"Page {clean_id}"
            ),
        ),
    ]
