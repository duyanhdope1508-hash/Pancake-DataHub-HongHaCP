import asyncio
import getpass
import sys

from app.config import get_settings
from app.page_connectors import (
    load_page_connectors,
    merge_page_connector,
    write_page_connectors,
)
from app.pancake_pages import PancakePagesApiError, PancakePagesClient


async def verify_page_token(page_id: str, page_access_token: str) -> int:
    async with PancakePagesClient(page_access_token) as client:
        conversations = await client.list_conversations(page_id)
    return len(conversations)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    page_id = input("Page ID: ").strip()
    if not page_id:
        raise SystemExit("Page ID không được để trống.")

    print("Dán Public API access token rồi nhấn Enter. Ký tự sẽ được ẩn.")
    page_access_token = getpass.getpass("Page Access Token (ẩn): ").strip()
    if len(page_access_token) < 10:
        raise SystemExit("Page Access Token không hợp lệ hoặc quá ngắn.")

    try:
        conversation_count = asyncio.run(verify_page_token(page_id, page_access_token))
    except PancakePagesApiError as exc:
        raise SystemExit(f"Pancake Pages từ chối token: {exc}") from None

    settings = get_settings()
    try:
        connectors = merge_page_connector(
            load_page_connectors(settings),
            page_id=page_id,
            page_access_token=page_access_token,
        )
    except (OSError, TypeError, ValueError) as exc:
        raise SystemExit(str(exc)) from None

    write_page_connectors(settings.pancake_pages_connectors_file, connectors)
    print(
        f"Đã lưu an toàn Page {page_id}; API trả {conversation_count} hội thoại gần nhất. "
        f"Tổng số Page connector: {len(connectors)}."
    )


if __name__ == "__main__":
    main()
