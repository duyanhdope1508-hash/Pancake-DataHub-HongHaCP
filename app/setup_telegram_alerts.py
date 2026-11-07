import asyncio
import getpass
import sys
from typing import Any

from app.config import get_settings
from app.telegram_alerts import (
    TelegramAlertConfig,
    TelegramApiError,
    TelegramBotClient,
    write_telegram_alert_config,
)


def _latest_update_id(updates: list[dict[str, Any]]) -> int | None:
    ids = [item.get("update_id") for item in updates]
    numeric_ids = [value for value in ids if isinstance(value, int)]
    return max(numeric_ids) if numeric_ids else None


def _chat_from_updates(updates: list[dict[str, Any]]) -> dict[str, Any] | None:
    for update in reversed(updates):
        for key in ("message", "channel_post"):
            message = update.get(key)
            if not isinstance(message, dict):
                continue
            chat = message.get("chat")
            if isinstance(chat, dict) and chat.get("id") is not None:
                return chat
    return None


def _chat_label(chat: dict[str, Any]) -> str:
    name = (
        chat.get("title")
        or chat.get("username")
        or " ".join(
            str(chat.get(key) or "").strip() for key in ("first_name", "last_name")
        ).strip()
        or "Telegram chat"
    )
    return f"{name} | Chat ID: {chat.get('id')}"


async def _configure() -> None:
    settings = get_settings()
    print("CÀI CẢNH BÁO TELEGRAM")
    print("Bot token chỉ được lưu trong file bí mật, không hiển thị ra màn hình.")
    bot_token = getpass.getpass("Bot token từ @BotFather (ẩn): ").strip()
    if len(bot_token) < 20 or ":" not in bot_token:
        raise SystemExit("Token không đúng định dạng; chưa lưu thay đổi.")

    client = TelegramBotClient(bot_token)
    try:
        bot = await client.get_me()
        previous_updates = await client.get_updates()
    except TelegramApiError as exc:
        raise SystemExit(f"Không thể xác nhận bot: {exc}. Token chưa được lưu.") from None

    username = str(bot.get("username") or "").strip()
    if not username:
        raise SystemExit("Telegram không trả về username của bot; token chưa được lưu.")
    previous_update_id = _latest_update_id(previous_updates)
    offset = previous_update_id + 1 if previous_update_id is not None else None

    print(f"Bot đã xác nhận: @{username}")
    print(f"Mở https://t.me/{username}, nhấn Start hoặc gửi /start.")
    input("Sau khi đã gửi /start, quay lại đây và nhấn Enter: ")

    try:
        updates = await client.get_updates(offset=offset, timeout_seconds=30)
    except TelegramApiError as exc:
        raise SystemExit(f"Không thể đọc tin nhắn mới: {exc}. Chưa lưu thay đổi.") from None
    chat = _chat_from_updates(updates)
    if chat is None:
        raise SystemExit("Chưa thấy tin nhắn mới. Chạy lại và gửi /start đúng bot.")

    print(f"Chat nhận cảnh báo: {_chat_label(chat)}")
    if input("Gõ LUU để xác nhận: ").strip().upper() != "LUU":
        raise SystemExit("Đã hủy; chưa lưu thay đổi.")

    config = TelegramAlertConfig(bot_token=bot_token, chat_id=str(chat["id"]))
    write_telegram_alert_config(settings.telegram_alerts_file, config)
    try:
        await client.send_message(
            config.chat_id,
            "✅ HỒNG HÀ DATAHUB\nCảnh báo Telegram đã được kết nối thành công.",
        )
    except TelegramApiError as exc:
        raise SystemExit(f"Đã lưu nhưng gửi tin thử thất bại: {exc}.") from None
    print("Đã lưu an toàn và gửi tin nhắn thử thành công.")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(_configure())


if __name__ == "__main__":
    main()
