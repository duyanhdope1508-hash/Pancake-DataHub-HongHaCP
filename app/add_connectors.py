import asyncio
import getpass
import sys
from typing import Any

from app.add_connector import write_connectors
from app.config import get_settings
from app.connectors import PancakeConnector, load_connectors
from app.pancake import PancakeApiError
from app.probe_key import discover_shops


def merge_discovered_connector(
    connectors: list[PancakeConnector],
    *,
    shops: list[dict[str, Any]],
    api_key: str,
) -> tuple[list[PancakeConnector], PancakeConnector | None]:
    assigned_shop_ids = {
        shop_id for connector in connectors for shop_id in connector.shop_ids
    }
    new_shop_ids = sorted(
        {
            str(shop.get("shop_id") or "").strip()
            for shop in shops
            if str(shop.get("shop_id") or "").strip() not in assigned_shop_ids
        }
    )
    if not new_shop_ids:
        return connectors, None

    existing_names = {connector.name for connector in connectors}
    base_name = f"shop-{new_shop_ids[0]}"
    name = base_name
    suffix = 2
    while name in existing_names:
        name = f"{base_name}-{suffix}"
        suffix += 1

    connector = PancakeConnector(
        name=name,
        shop_ids=frozenset(new_shop_ids),
        api_key=api_key,
    )
    return [*connectors, connector], connector


def _shop_label(shop: dict[str, Any]) -> str:
    shop_id = str(shop.get("shop_id") or "").strip()
    shop_name = str(shop.get("shop_name") or f"Shop {shop_id}").strip()
    return f"{shop_name} | Shop ID: {shop_id}"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    settings = get_settings()
    try:
        connectors = load_connectors(settings)
    except (OSError, TypeError, ValueError) as exc:
        raise SystemExit(f"Không thể đọc cấu hình connector: {exc}") from None

    print("THÊM NHIỀU CỬA HÀNG PANCAKE")
    print("Dán từng API key rồi nhấn Enter. Ký tự sẽ được ẩn.")
    print("Nhấn Enter tại ô API key trống khi đã nhập xong.")

    added_connectors = 0
    added_shops = 0
    key_number = 1
    while True:
        api_key = getpass.getpass(f"API key #{key_number} (ẩn): ").strip()
        if not api_key:
            break
        if len(api_key) < 10:
            print("Key quá ngắn, chưa lưu. Hãy nhập lại.")
            continue

        try:
            shops = asyncio.run(discover_shops(settings.pancake_api_base_url, api_key))
        except PancakeApiError as exc:
            print(f"Pancake từ chối key này: {exc}. Key chưa được lưu.")
            key_number += 1
            continue

        connectors, added_connector = merge_discovered_connector(
            connectors,
            shops=shops,
            api_key=api_key,
        )
        if added_connector is None:
            print("Mọi cửa hàng key này truy cập được đều đã có; không thay đổi cấu hình.")
            key_number += 1
            continue

        write_connectors(settings.pancake_connectors_file, connectors)
        added_connectors += 1
        added_shops += len(added_connector.shop_ids)
        print("Đã lưu an toàn:")
        for shop in shops:
            if str(shop.get("shop_id")) in added_connector.shop_ids:
                print(f"- {_shop_label(shop)}")
        key_number += 1

    print(
        f"Hoàn tất: thêm {added_shops} cửa hàng từ {added_connectors} API key. "
        f"Hiện có {len(connectors)} connector."
    )


if __name__ == "__main__":
    main()
