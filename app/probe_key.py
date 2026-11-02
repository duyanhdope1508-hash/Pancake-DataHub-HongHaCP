import asyncio
import getpass
from typing import Any

from app.config import get_settings
from app.pancake import PancakeApiError, PancakeClient


def summarize_shops(shops: list[dict[str, Any]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for shop in shops:
        shop_id = shop.get("id") or shop.get("shop_id")
        if shop_id is None:
            continue
        name = shop.get("name") or shop.get("shop_name") or shop.get("display_name")
        result.append(
            {
                "shop_id": str(shop_id),
                "shop_name": str(name) if name else f"Shop {shop_id}",
            }
        )
    return result


async def discover_shops(base_url: str, api_key: str) -> list[dict[str, str]]:
    async with PancakeClient(base_url, api_key) as client:
        return summarize_shops(await client.list_shops())


def main() -> None:
    print("Dán API key của cửa hàng mới rồi nhấn Enter.")
    print("Ký tự nhập sẽ được ẩn và key không được lưu vào máy.")
    api_key = getpass.getpass("API key (ẩn): ").strip()
    if len(api_key) < 10:
        raise SystemExit("API key không hợp lệ hoặc quá ngắn.")

    try:
        shops = asyncio.run(discover_shops(get_settings().pancake_api_base_url, api_key))
    except PancakeApiError as exc:
        raise SystemExit(f"Pancake từ chối yêu cầu: {exc}") from None

    print("\nCác cửa hàng API key này truy cập được:")
    for shop in shops:
        print(f"- {shop['shop_name']} | Shop ID: {shop['shop_id']}")


if __name__ == "__main__":
    main()
