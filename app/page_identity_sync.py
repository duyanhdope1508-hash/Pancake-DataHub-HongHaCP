import asyncio
from collections.abc import Mapping
from typing import Any

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert

from app.config import Settings
from app.db import SessionLocal, init_db
from app.models import PancakePageCustomer
from app.page_connectors import PancakePageConnector, load_page_connectors
from app.pancake import extract_collection
from app.pancake_pages import PancakePagesApiError, PancakePagesClient


def _text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def extract_page_customer_records(
    page_id: str,
    conversation_id: str,
    payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for customer in extract_collection(payload, "customers"):
        page_customer_id = _text(customer.get("id"))
        psid = _text(customer.get("fb_id")) or _text(customer.get("psid"))
        if not page_customer_id and not psid:
            continue
        records.append(
            {
                "page_id": page_id,
                "page_customer_id": page_customer_id or f"psid:{psid}",
                "source_customer_id": _text(customer.get("customer_id")),
                "psid": psid,
                "global_id": _text(customer.get("global_id")),
                "name": _text(customer.get("name")),
                "conversation_id": conversation_id,
                "raw_payload": dict(customer),
            }
        )
    return records


async def _fetch_connector(
    connector: PancakePageConnector,
    *,
    max_conversations: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records: dict[tuple[str, str], dict[str, Any]] = {}
    conversations_checked = 0
    conversations_failed = 0
    try:
        async with PancakePagesClient(connector.page_access_token) as client:
            conversations = await client.list_conversations(connector.page_id)
            inbox = [
                conversation
                for conversation in conversations
                if str(conversation.get("type") or "").upper() == "INBOX"
            ]
            candidates = inbox or conversations
            for conversation in candidates[:max_conversations]:
                conversation_id = _text(conversation.get("id"))
                if not conversation_id:
                    continue
                try:
                    payload = await client.get_messages(
                        connector.page_id, conversation_id
                    )
                except PancakePagesApiError:
                    conversations_failed += 1
                    continue
                conversations_checked += 1
                for record in extract_page_customer_records(
                    connector.page_id, conversation_id, payload
                ):
                    records[(record["page_id"], record["page_customer_id"])] = record
                await asyncio.sleep(0.22)
    except PancakePagesApiError:
        return [], {
            "page_id": connector.page_id,
            "status": "failed",
            "conversations_checked": 0,
            "conversations_failed": 1,
            "customers_found": 0,
        }

    return list(records.values()), {
        "page_id": connector.page_id,
        "status": "success",
        "conversations_checked": conversations_checked,
        "conversations_failed": conversations_failed,
        "customers_found": len(records),
    }


def _upsert_page_customers(records: list[dict[str, Any]]) -> int:
    if not records:
        return 0
    with SessionLocal.begin() as session:
        statement = insert(PancakePageCustomer).values(records)
        session.execute(
            statement.on_conflict_do_update(
                index_elements=[
                    PancakePageCustomer.page_id,
                    PancakePageCustomer.page_customer_id,
                ],
                set_={
                    "source_customer_id": statement.excluded.source_customer_id,
                    "psid": statement.excluded.psid,
                    "global_id": statement.excluded.global_id,
                    "name": statement.excluded.name,
                    "conversation_id": statement.excluded.conversation_id,
                    "raw_payload": statement.excluded.raw_payload,
                    "updated_at": func.now(),
                },
            )
        )
    return len(records)


async def sync_page_identities(
    settings: Settings,
    *,
    max_conversations: int = 60,
) -> dict[str, Any]:
    connectors = load_page_connectors(settings)
    if not connectors:
        raise RuntimeError("No Pancake Pages connectors are configured")

    results = await asyncio.gather(
        *(
            _fetch_connector(connector, max_conversations=max_conversations)
            for connector in connectors
        )
    )
    records_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    page_results: list[dict[str, Any]] = []
    for records, page_result in results:
        page_results.append(page_result)
        for record in records:
            records_by_key[(record["page_id"], record["page_customer_id"])] = record

    init_db()
    written = _upsert_page_customers(list(records_by_key.values()))
    return {
        "pages_configured": len(connectors),
        "pages_succeeded": sum(result["status"] == "success" for result in page_results),
        "pages_failed": sum(result["status"] == "failed" for result in page_results),
        "conversations_checked": sum(
            result["conversations_checked"] for result in page_results
        ),
        "customers_written": written,
        "pages": page_results,
    }
