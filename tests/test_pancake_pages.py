import httpx
import pytest

from app.pancake_pages import (
    PancakePagesApiError,
    PancakePagesClient,
    count_global_ids,
    names_missing_global_id,
    profile_test_links_missing_global_id,
)


def test_counts_available_global_ids() -> None:
    assert count_global_ids(
        {
            "customers": [
                {"id": "one", "global_id": "global-one"},
                {"id": "two", "global_id": None},
                {"id": "three"},
            ]
        }
    ) == (3, 1)


def test_counts_nested_customer_collection() -> None:
    assert count_global_ids(
        {"data": {"customers": [{"id": "one", "global_id": "global-one"}]}}
    ) == (1, 1)


def test_lists_only_names_missing_global_id() -> None:
    assert names_missing_global_id(
        {
            "customers": [
                {"name": "Has Global", "global_id": "global-one"},
                {"name": "Missing Global", "global_id": None},
                {"name": "Also Missing"},
            ]
        }
    ) == ["Missing Global", "Also Missing"]


def test_builds_safe_psid_profile_links_only_for_missing_global_id() -> None:
    assert profile_test_links_missing_global_id(
        {
            "customers": [
                {"name": "Has Global", "fb_id": "111", "global_id": "global-one"},
                {"name": "Missing Global", "fb_id": "222", "global_id": None},
                {"name": "Unsafe", "fb_id": "https://not-an-id.example"},
            ]
        }
    ) == ["Missing Global | https://www.facebook.com/222"]


async def test_network_errors_do_not_expose_page_token(monkeypatch) -> None:
    secret = "page-token-that-must-not-leak"
    client = PancakePagesClient(secret)

    async def fail_request(*_args, **_kwargs):
        request = httpx.Request(
            "GET",
            f"https://pages.fm/api/public_api/v2/pages/123/conversations?"
            f"page_access_token={secret}",
        )
        raise httpx.ConnectError("connection failed", request=request)

    monkeypatch.setattr(client._client, "get", fail_request)
    try:
        with pytest.raises(PancakePagesApiError) as error:
            await client.list_conversations("123")
        assert secret not in str(error.value)
    finally:
        await client._client.aclose()


async def test_api_rejection_shows_safe_reason_without_token(monkeypatch) -> None:
    secret = "page-token-that-must-not-leak"
    client = PancakePagesClient(secret)

    async def reject_request(*_args, **_kwargs):
        request = httpx.Request("GET", "https://pages.fm/api/public_api/v2/pages/123")
        return httpx.Response(
            200,
            request=request,
            json={
                "success": False,
                "error_code": 100,
                "message": f"Invalid token {secret}",
            },
        )

    monkeypatch.setattr(client._client, "get", reject_request)
    try:
        with pytest.raises(PancakePagesApiError) as error:
            await client.list_conversations("123")
        assert "error_code=100" in str(error.value)
        assert "Invalid token [hidden]" in str(error.value)
        assert secret not in str(error.value)
    finally:
        await client._client.aclose()
