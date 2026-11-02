import asyncio
from collections.abc import Mapping
from typing import Any, Self

import httpx


class PancakeApiError(RuntimeError):
    pass


def extract_collection(payload: Any, *candidate_keys: str) -> list[dict[str, Any]]:
    """Extract a list from common Pancake response envelopes.

    The POS API has evolved over time, so the POC accepts both direct lists and
    common envelopes such as {"shops": [...]}, {"orders": [...]}, and
    {"data": {"orders": [...]}} without guessing fields inside each record.
    """
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, Mapping):
        return []

    for key in candidate_keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    data = payload.get("data")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, Mapping):
        for key in candidate_keys:
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


class PancakeClient:
    def __init__(self, base_url: str, api_key: str, *, timeout_seconds: float = 30.0):
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout_seconds),
            headers={"Accept": "application/json", "User-Agent": "pancake-data-hub/0.1"},
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        request_params = dict(params or {})
        request_params["api_key"] = self._api_key

        for attempt in range(4):
            response = await self._client.get(path, params=request_params)
            if response.status_code < 400:
                try:
                    return response.json()
                except ValueError as exc:
                    raise PancakeApiError("Pancake returned a non-JSON response") from exc

            retryable = response.status_code == 429 or response.status_code >= 500
            if retryable and attempt < 3:
                await asyncio.sleep(2**attempt)
                continue

            raise PancakeApiError(
                f"Pancake API request failed with HTTP {response.status_code}"
            )

        raise PancakeApiError("Pancake API request failed after retries")

    async def list_shops(self) -> list[dict[str, Any]]:
        payload = await self._get("/shops")
        shops = extract_collection(payload, "shops")
        if not shops:
            raise PancakeApiError("No shops found in the Pancake API response")
        return shops

    async def list_orders(
        self, shop_id: str, *, page_number: int, page_size: int
    ) -> list[dict[str, Any]]:
        payload = await self._get(
            f"/shops/{shop_id}/orders",
            {"page_number": page_number, "page_size": page_size},
        )
        return extract_collection(payload, "orders")

