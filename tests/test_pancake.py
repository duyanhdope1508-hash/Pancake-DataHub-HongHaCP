import httpx
import pytest

from app.pancake import PancakeApiError, PancakeClient, extract_collection


def test_extracts_direct_collection() -> None:
    assert extract_collection([{"id": 1}], "orders") == [{"id": 1}]


def test_extracts_named_collection() -> None:
    payload = {"success": True, "shops": [{"id": 123, "name": "Shop A"}]}
    assert extract_collection(payload, "shops") == [{"id": 123, "name": "Shop A"}]


def test_extracts_nested_data_collection() -> None:
    payload = {"data": {"orders": [{"id": "DH001"}]}}
    assert extract_collection(payload, "orders") == [{"id": "DH001"}]


def test_ignores_non_object_items() -> None:
    payload = {"orders": [None, "bad", {"id": 1}]}
    assert extract_collection(payload, "orders") == [{"id": 1}]


async def test_network_errors_do_not_expose_api_key(monkeypatch) -> None:
    secret = "secret-key-that-must-not-leak"
    client = PancakeClient("https://example.invalid", secret)
    calls = 0

    async def fail_request(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        request = httpx.Request("GET", f"https://example.invalid/shops?api_key={secret}")
        raise httpx.ConnectError("connection failed", request=request)

    async def skip_backoff(_seconds):
        return None

    monkeypatch.setattr(client._client, "get", fail_request)
    monkeypatch.setattr("app.pancake.asyncio.sleep", skip_backoff)
    try:
        with pytest.raises(PancakeApiError) as error:
            await client.list_shops()
        assert calls == 4
        assert secret not in str(error.value)
    finally:
        await client._client.aclose()

