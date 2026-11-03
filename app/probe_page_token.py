import argparse
import asyncio
import getpass
import sys

from app.pancake_pages import (
    PancakePagesApiError,
    PancakePagesClient,
    count_global_ids,
    names_missing_global_id,
)


async def probe_page_token(
    page_id: str,
    page_access_token: str,
    *,
    max_conversations: int,
    include_missing_names: bool = False,
) -> dict[str, int | list[str]]:
    conversations_checked = 0
    customer_profiles = 0
    global_ids_found = 0
    conversations_failed = 0
    missing_names: list[str] = []

    async with PancakePagesClient(page_access_token) as client:
        conversations = await client.list_conversations(page_id)
        inbox_conversations = [
            conversation
            for conversation in conversations
            if str(conversation.get("type") or "").upper() == "INBOX"
            and str(conversation.get("id") or "").strip()
        ]
        candidates = inbox_conversations or conversations

        for conversation in candidates[:max_conversations]:
            conversation_id = str(conversation.get("id") or "").strip()
            if not conversation_id:
                continue
            try:
                payload = await client.get_messages(page_id, conversation_id)
            except PancakePagesApiError:
                conversations_failed += 1
                continue
            profiles, found = count_global_ids(payload)
            conversations_checked += 1
            customer_profiles += profiles
            global_ids_found += found
            if include_missing_names:
                missing_names.extend(names_missing_global_id(payload))
            await asyncio.sleep(0.22)

    return {
        "conversations_checked": conversations_checked,
        "customer_profiles": customer_profiles,
        "global_ids_found": global_ids_found,
        "conversations_failed": conversations_failed,
        "missing_global_id_names": list(dict.fromkeys(missing_names)),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Kiểm tra Pancake Page Access Token và độ phủ global Facebook ID"
    )
    parser.add_argument("--max-conversations", type=int, default=10)
    parser.add_argument(
        "--show-missing-names",
        action="store_true",
        help="chỉ hiện cục bộ tên khách chưa có global_id, không hiện ID",
    )
    args = parser.parse_args()
    if not 1 <= args.max_conversations <= 60:
        raise SystemExit("--max-conversations phải nằm trong khoảng 1-60.")

    page_id = input("Page ID: ").strip()
    if not page_id:
        raise SystemExit("Page ID không được để trống.")

    print("Dán Public API access token rồi nhấn Enter. Ký tự sẽ được ẩn.")
    page_access_token = getpass.getpass("Page Access Token (ẩn): ").strip()
    if len(page_access_token) < 10:
        raise SystemExit("Page Access Token không hợp lệ hoặc quá ngắn.")

    try:
        result = asyncio.run(
            probe_page_token(
                page_id,
                page_access_token,
                max_conversations=args.max_conversations,
                include_missing_names=args.show_missing_names,
            )
        )
    except PancakePagesApiError as exc:
        raise SystemExit(f"Không thể kiểm tra token: {exc}") from None

    if result["conversations_checked"] == 0:
        raise SystemExit(
            "Token hợp lệ nhưng chưa đọc được hội thoại nào để kiểm tra global_id."
        )

    print("\nKết quả kiểm tra an toàn:")
    print(f"- Hội thoại đã kiểm tra: {result['conversations_checked']}")
    print(f"- Hồ sơ khách trong phản hồi: {result['customer_profiles']}")
    print(f"- Hồ sơ có global_id: {result['global_ids_found']}")
    print(f"- Hội thoại lỗi/bị bỏ qua: {result['conversations_failed']}")
    missing_names = result["missing_global_id_names"]
    if args.show_missing_names and isinstance(missing_names, list) and missing_names:
        print("\nTên khách chưa có global_id (chỉ hiển thị trên máy này):")
        for name in missing_names:
            print(f"- {name}")
    print("Token và ID khách không được hiển thị hoặc lưu vào file.")


if __name__ == "__main__":
    main()
