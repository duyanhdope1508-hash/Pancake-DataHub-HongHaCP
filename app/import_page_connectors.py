import asyncio
import getpass
import sys

from app.config import get_settings
from app.page_connectors import (
    PancakePageConnector,
    load_page_connectors,
    merge_page_connector,
    write_page_connectors,
)
from app.pancake_pages import PancakePagesApiError
from app.pancake_user import PancakeUserClient, extract_available_page_tokens


async def discover_page_tokens(user_access_token: str) -> list[dict[str, str]]:
    async with PancakeUserClient(user_access_token) as client:
        payload = await client.list_pages()
    return extract_available_page_tokens(payload)


def merge_discovered_pages(
    connectors: list[PancakePageConnector],
    discovered: list[dict[str, str]],
) -> tuple[list[PancakePageConnector], list[dict[str, str]]]:
    merged = list(connectors)
    existing_page_ids = {connector.page_id for connector in connectors}
    added: list[dict[str, str]] = []
    for page in discovered:
        if page["page_id"] in existing_page_ids:
            continue
        merged = merge_page_connector(
            merged,
            page_id=page["page_id"],
            page_access_token=page["page_access_token"],
        )
        existing_page_ids.add(page["page_id"])
        added.append(page)
    return merged, added


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("Dán User Access Token trong Pancake > Cài đặt cá nhân > API Access Token.")
    print("Token tài khoản chỉ dùng trong bộ nhớ để nhập Page, không được lưu vào file.")
    user_access_token = getpass.getpass("User Access Token (ẩn): ").strip()
    if len(user_access_token) < 10:
        raise SystemExit("User Access Token không hợp lệ hoặc quá ngắn.")

    try:
        discovered = asyncio.run(discover_page_tokens(user_access_token))
    except PancakePagesApiError as exc:
        raise SystemExit(f"Không thể đọc danh sách Page: {exc}") from None

    if not discovered:
        raise SystemExit(
            "Không tìm thấy Page Access Token nào. Hãy kiểm tra tài khoản có quyền admin Page."
        )

    settings = get_settings()
    try:
        connectors, added = merge_discovered_pages(
            load_page_connectors(settings), discovered
        )
    except (OSError, TypeError, ValueError) as exc:
        raise SystemExit(str(exc)) from None

    if added:
        write_page_connectors(settings.pancake_pages_connectors_file, connectors)

    print(f"Đã tìm thấy {len(discovered)} Page có token; thêm mới {len(added)} Page:")
    for page in added:
        print(f"- {page['page_name']} | Page ID: {page['page_id']}")
    print(f"Tổng số Page connector đang lưu: {len(connectors)}.")


if __name__ == "__main__":
    main()
