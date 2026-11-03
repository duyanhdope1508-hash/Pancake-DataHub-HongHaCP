import asyncio
from collections.abc import Mapping
from typing import Any, Self
from urllib.parse import quote

import httpx

from app.pancake import extract_collection


class PancakePagesApiError(RuntimeError):
    pass


class PancakePagesClient:
    def __init__(self, page_access_token: str, *, timeout_seconds: float = 30.0):
        self._page_access_token = page_access_token
        self._client = httpx.AsyncClient(
            base_url="https://pages.fm/api/public_api",
            timeout=httpx.Timeout(timeout_seconds),
            headers={"Accept": "application/json", "User-Agent": "pancake-data-hub/0.1"},
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        request_params = dict(params or {})
        request_params["page_access_token"] = self._page_access_token

        for attempt in range(4):
            try:
                response = await self._client.get(path, params=request_params)
            except httpx.RequestError as exc:
                raise PancakePagesApiError("Could not connect to the Pancake Pages API") from exc

            if response.status_code < 400:
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise PancakePagesApiError(
                        "Pancake Pages returned a non-JSON response"
                    ) from exc
                if isinstance(payload, Mapping) and payload.get("success") is False:
                    raise PancakePagesApiError("Pancake Pages rejected the request")
                return payload

            retryable = response.status_code == 429 or response.status_code >= 500
            if retryable and attempt < 3:
                await asyncio.sleep(2**attempt)
                continue
            raise PancakePagesApiError(
                f"Pancake Pages API request failed with HTTP {response.status_code}"
            )

        raise PancakePagesApiError("Pancake Pages API request failed after retries")

    async def list_conversations(self, page_id: str) -> list[dict[str, Any]]:
        safe_page_id = quote(page_id, safe="")
        payload = await self._get(f"/v2/pages/{safe_page_id}/conversations")
        return extract_collection(payload, "conversations")

    async def get_messages(self, page_id: str, conversation_id: str) -> dict[str, Any]:
        safe_page_id = quote(page_id, safe="")
        safe_conversation_id = quote(conversation_id, safe="")
        payload = await self._get(
            f"/v1/pages/{safe_page_id}/conversations/{safe_conversation_id}/messages"
        )
        if not isinstance(payload, dict):
            raise PancakePagesApiError("Pancake Pages returned an invalid messages response")
        return payload


def count_global_ids(payload: Mapping[str, Any]) -> tuple[int, int]:
    customers = extract_collection(payload, "customers")
    found = sum(bool(str(customer.get("global_id") or "").strip()) for customer in customers)
    return len(customers), found
