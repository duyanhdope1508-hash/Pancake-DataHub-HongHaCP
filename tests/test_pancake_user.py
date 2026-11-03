import httpx
import pytest

from app.pancake_pages import PancakePagesApiError
from app.pancake_user import PancakeUserClient, extract_generated_page_token


def test_extracts_generated_token_from_common_response_envelopes() -> None:
    assert extract_generated_page_token(
        {"success": True, "data": {"page_access_token": "valid-generated-token"}}
    ) == "valid-generated-token"


async def test_user_api_errors_do_not_expose_token(monkeypatch) -> None:
    secret = "user-token-that-must-not-leak"
    client = PancakeUserClient(secret)

    async def reject_request(*_args, **_kwargs):
        request = httpx.Request("GET", "https://pages.fm/api/v1/pages")
        return httpx.Response(
            200,
            request=request,
            json={"success": False, "message": f"Invalid token {secret}"},
        )

    monkeypatch.setattr(client._client, "get", reject_request)
    try:
        with pytest.raises(PancakePagesApiError) as error:
            await client.list_pages()
        assert "Invalid token [hidden]" in str(error.value)
        assert secret not in str(error.value)
    finally:
        await client._client.aclose()
