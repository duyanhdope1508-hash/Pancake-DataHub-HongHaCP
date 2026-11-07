import json
import os

import httpx
import pytest

from app.telegram_alerts import (
    TelegramAlertConfig,
    TelegramApiError,
    TelegramBotClient,
    load_telegram_alert_config,
    write_telegram_alert_config,
)


def test_telegram_alert_config_round_trip_is_private(tmp_path) -> None:
    path = tmp_path / "telegram_alerts.json"
    config = TelegramAlertConfig(bot_token="123456789:secret-bot-token-value", chat_id="42")

    write_telegram_alert_config(path, config)

    assert load_telegram_alert_config(path) == config
    if os.name != "nt":
        assert path.stat().st_mode & 0o777 == 0o600
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["chat_id"] == "42"


async def test_send_message_uses_official_bot_api_without_exposing_token() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    client = TelegramBotClient(
        "123456789:secret-bot-token-value",
        transport=httpx.MockTransport(handler),
    )

    await client.send_message("42", "test alert")

    assert requests[0].url.path.endswith("/sendMessage")
    assert json.loads(requests[0].content)["chat_id"] == "42"


async def test_telegram_rejection_returns_safe_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"ok": False, "description": "bad token"})

    client = TelegramBotClient(
        "123456789:secret-bot-token-value",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(TelegramApiError, match="Telegram rejected the request") as error:
        await client.get_me()

    assert "secret-bot-token-value" not in str(error.value)
