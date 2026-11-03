import asyncio
from collections.abc import Mapping
from typing import Any, Self
from urllib.parse import quote

import httpx

from app.pancake_pages import PancakePagesApiError


class PancakeUserClient:
    def __init__(self, access_token: str, *, timeout_seconds: float = 30.0):
        self._access_token = access_token
        self._client = httpx.AsyncClient(
            base_url="https://pages.fm/api/v1",
            timeout=httpx.Timeout(timeout_seconds),
            headers={"Accept": "application/json", "User-Agent": "pancake-data-hub/0.1"},
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._client.aclose()

    async def list_pages(self) -> dict[str, Any]:
        params = {
            "access_token": self._access_token,
            "fields": "activated{id,name,username,settings{page_access_token}}",
        }
        for attempt in range(4):
            try:
                response = await self._client.get("/pages", params=params)
            except httpx.RequestError as exc:
                raise PancakePagesApiError("Could not connect to the Pancake user API") from exc

            if response.status_code < 400:
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise PancakePagesApiError(
                        "Pancake user API returned a non-JSON response"
                    ) from exc
                if not isinstance(payload, dict):
                    raise PancakePagesApiError("Pancake user API returned an invalid response")
                if payload.get("success") is False:
                    details = self._safe_error_details(payload)
                    suffix = f" ({details})" if details else ""
                    raise PancakePagesApiError(f"Pancake rejected the user token{suffix}")
                return payload

            retryable = response.status_code == 429 or response.status_code >= 500
            if retryable and attempt < 3:
                await asyncio.sleep(2**attempt)
                continue
            raise PancakePagesApiError(
                f"Pancake user API request failed with HTTP {response.status_code}"
            )

        raise PancakePagesApiError("Pancake user API request failed after retries")

    async def generate_page_access_token(self, page_id: str) -> str:
        safe_page_id = quote(page_id, safe="")
        params = {"access_token": self._access_token, "page_id": page_id}
        try:
            response = await self._client.post(
                f"/pages/{safe_page_id}/generate_page_access_token",
                params=params,
            )
        except httpx.RequestError as exc:
            raise PancakePagesApiError("Could not connect to the Pancake user API") from exc

        if response.status_code >= 400:
            raise PancakePagesApiError(
                f"Generate Page token failed with HTTP {response.status_code}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise PancakePagesApiError(
                "Generate Page token returned a non-JSON response"
            ) from exc
        if isinstance(payload, Mapping) and payload.get("success") is False:
            details = self._safe_error_details(payload)
            suffix = f" ({details})" if details else ""
            raise PancakePagesApiError(f"Pancake rejected token generation{suffix}")

        token = extract_generated_page_token(payload)
        if not token:
            raise PancakePagesApiError("Pancake did not return a Page Access Token")
        return token

    def _safe_error_details(self, payload: Mapping[str, Any]) -> str:
        details: list[str] = []
        for key in ("error_code", "message_code", "error", "message"):
            value = payload.get(key)
            if value is None or isinstance(value, (dict, list)):
                continue
            safe_value = str(value).replace(self._access_token, "[hidden]")[:200]
            if safe_value:
                details.append(f"{key}={safe_value}")
        return ", ".join(details)


def extract_activated_pages(payload: Mapping[str, Any]) -> list[dict[str, str]]:
    pages = payload.get("pages")
    if not isinstance(pages, Mapping):
        pages = payload.get("categorized")
    if not isinstance(pages, Mapping):
        return []

    activated = pages.get("activated")
    if not isinstance(activated, list):
        return []

    result: list[dict[str, str]] = []
    for page in activated:
        if not isinstance(page, Mapping):
            continue
        page_id = str(page.get("id") or "").strip()
        settings = page.get("settings")
        token = ""
        if isinstance(settings, Mapping):
            token = str(settings.get("page_access_token") or "").strip()
        if not token:
            token = str(page.get("page_access_token") or "").strip()
        if not page_id:
            continue
        page_name = str(page.get("name") or page.get("username") or page_id).strip()
        result.append(
            {
                "page_id": page_id,
                "page_name": page_name,
                "page_access_token": token,
            }
        )
    return result


def extract_available_page_tokens(payload: Mapping[str, Any]) -> list[dict[str, str]]:
    return [
        page
        for page in extract_activated_pages(payload)
        if len(page["page_access_token"]) >= 10
    ]


def extract_generated_page_token(payload: Any) -> str:
    if not isinstance(payload, Mapping):
        return ""
    direct = str(payload.get("page_access_token") or "").strip()
    if len(direct) >= 10:
        return direct
    for key in ("data", "page", "settings"):
        nested = payload.get(key)
        if isinstance(nested, Mapping):
            token = extract_generated_page_token(nested)
            if token:
                return token
    return ""
