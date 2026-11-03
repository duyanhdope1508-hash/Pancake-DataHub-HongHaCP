import argparse
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
from app.pancake_user import PancakeUserClient, extract_activated_pages


async def discover_pages(user_access_token: str) -> list[dict[str, str]]:
    async with PancakeUserClient(user_access_token) as client:
        payload = await client.list_pages()
    return extract_activated_pages(payload)


async def generate_missing_page_tokens(
    user_access_token: str,
    pages: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    generated: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    async with PancakeUserClient(user_access_token) as client:
        for page in pages:
            try:
                token = await client.generate_page_access_token(page["page_id"])
            except PancakePagesApiError as exc:
                failed.append({**page, "error": str(exc)[:200]})
                continue
            generated.append({**page, "page_access_token": token})
            await asyncio.sleep(0.2)
    return generated, failed


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

    parser = argparse.ArgumentParser(description="Nhập hàng loạt Pancake Page connectors")
    parser.add_argument(
        "--generate-missing",
        action="store_true",
        help="tạo token cho Page chưa có; có thể vô hiệu token cũ nếu Pancake đang ẩn nó",
    )
    args = parser.parse_args()

    print("Dán User Access Token trong Pancake > Cài đặt cá nhân > API Access Token.")
    print("Token tài khoản chỉ dùng trong bộ nhớ để nhập Page, không được lưu vào file.")
    user_access_token = getpass.getpass("User Access Token (ẩn): ").strip()
    if len(user_access_token) < 10:
        raise SystemExit("User Access Token không hợp lệ hoặc quá ngắn.")

    try:
        pages = asyncio.run(discover_pages(user_access_token))
    except PancakePagesApiError as exc:
        raise SystemExit(f"Không thể đọc danh sách Page: {exc}") from None

    if not pages:
        raise SystemExit("Tài khoản không trả về Page đang hoạt động nào.")

    settings = get_settings()
    try:
        existing = load_page_connectors(settings)
        existing_page_ids = {connector.page_id for connector in existing}
        available = [
            page for page in pages if len(page["page_access_token"]) >= 10
        ]
        missing = [
            page
            for page in pages
            if len(page["page_access_token"]) < 10
            and page["page_id"] not in existing_page_ids
        ]

        generated: list[dict[str, str]] = []
        failed: list[dict[str, str]] = []
        if args.generate_missing and missing:
            print(
                f"\nCó {len(missing)} Page chưa trả token. Việc tạo token có thể làm "
                "token cũ của Page mất hiệu lực nếu Pancake đang ẩn token đó."
            )
            confirmation = input("Gõ TAO TOKEN để tiếp tục: ").strip()
            if confirmation != "TAO TOKEN":
                raise SystemExit("Đã hủy; chưa tạo hoặc thay đổi token nào.")
            generated, failed = asyncio.run(
                generate_missing_page_tokens(user_access_token, missing)
            )

        connectors, added = merge_discovered_pages(
            existing, [*available, *generated]
        )
    except (OSError, TypeError, ValueError) as exc:
        raise SystemExit(str(exc)) from None

    if added:
        write_page_connectors(settings.pancake_pages_connectors_file, connectors)

    print(
        f"Đã thấy {len(pages)} Page hoạt động; {len(available)} Page có sẵn token; "
        f"tạo mới {len(generated)} token; thêm {len(added)} connector:"
    )
    for page in added:
        print(f"- {page['page_name']} | Page ID: {page['page_id']}")
    if failed:
        print(f"Có {len(failed)} Page không thể tạo token:")
        for page in failed:
            print(f"- {page['page_name']} | {page['error']}")
    elif missing and not args.generate_missing:
        print(
            f"Còn {len(missing)} Page chưa có token. Chạy lại với --generate-missing "
            "nếu muốn tạo hàng loạt."
        )
    print(f"Tổng số Page connector đang lưu: {len(connectors)}.")


if __name__ == "__main__":
    main()
