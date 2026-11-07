import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx


class TelegramApiError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class TelegramAlertConfig:
    chat_id: str
    bot_token: str = field(repr=False)


def load_telegram_alert_config(path: Path) -> TelegramAlertConfig | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Telegram alert configuration is invalid") from exc
    if not isinstance(payload, dict):
        raise TypeError("Telegram alert configuration is invalid")

    bot_token = str(payload.get("bot_token") or "").strip()
    chat_id = str(payload.get("chat_id") or "").strip()
    if len(bot_token) < 20 or ":" not in bot_token or not chat_id:
        raise ValueError("Telegram alert configuration is incomplete")
    return TelegramAlertConfig(bot_token=bot_token, chat_id=chat_id)


def write_telegram_alert_config(path: Path, config: TelegramAlertConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(
            {"bot_token": config.bot_token, "chat_id": config.chat_id},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary_path.chmod(0o600)
    temporary_path.replace(path)
    path.chmod(0o600)


class TelegramBotClient:
    def __init__(
        self,
        bot_token: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._bot_token = bot_token
        self._transport = transport

    async def _request(
        self,
        method: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout_seconds: float = 15.0,
    ) -> Any:
        url = f"https://api.telegram.org/bot{self._bot_token}/{method}"
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(timeout_seconds),
                transport=self._transport,
            ) as client:
                response = await client.post(url, json=payload or {})
        except httpx.RequestError as exc:
            raise TelegramApiError("Could not connect to Telegram") from exc

        if response.status_code >= 400:
            raise TelegramApiError("Telegram rejected the request")
        try:
            body = response.json()
        except ValueError as exc:
            raise TelegramApiError("Telegram returned an invalid response") from exc
        if not isinstance(body, dict) or body.get("ok") is not True:
            raise TelegramApiError("Telegram rejected the request")
        return body.get("result")

    async def get_me(self) -> dict[str, Any]:
        result = await self._request("getMe")
        if not isinstance(result, dict):
            raise TelegramApiError("Telegram returned an invalid bot profile")
        return result

    async def get_updates(
        self,
        *,
        offset: int | None = None,
        timeout_seconds: int = 0,
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": timeout_seconds}
        if offset is not None:
            payload["offset"] = offset
        result = await self._request(
            "getUpdates",
            payload,
            timeout_seconds=max(15.0, float(timeout_seconds + 10)),
        )
        if not isinstance(result, list):
            raise TelegramApiError("Telegram returned invalid updates")
        return [item for item in result if isinstance(item, dict)]

    async def send_message(self, chat_id: str, text: str) -> None:
        await self._request(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": text[:4096],
                "disable_web_page_preview": True,
                "protect_content": True,
            },
        )


async def send_telegram_alert(path: Path, text: str) -> bool | None:
    try:
        config = load_telegram_alert_config(path)
    except (TypeError, ValueError):
        return False
    if config is None:
        return None
    try:
        await TelegramBotClient(config.bot_token).send_message(config.chat_id, text)
    except TelegramApiError:
        return False
    return True
