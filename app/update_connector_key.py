import argparse
import asyncio
import getpass

from app.add_connector import write_connectors
from app.config import get_settings
from app.connectors import PancakeConnector, load_connectors
from app.pancake import PancakeApiError
from app.probe_key import discover_shops


def replace_connector_key(
    connectors: list[PancakeConnector],
    *,
    shop_id: str,
    api_key: str,
) -> list[PancakeConnector]:
    clean_shop_id = shop_id.strip()
    matches = [connector for connector in connectors if clean_shop_id in connector.shop_ids]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one connector for Shop ID: {clean_shop_id}")

    target = matches[0]
    return [
        PancakeConnector(
            name=connector.name,
            shop_ids=connector.shop_ids,
            api_key=api_key if connector is target else connector.api_key,
        )
        for connector in connectors
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Replace a Pancake connector API key")
    parser.add_argument("--shop-id", required=True, help="Pancake Shop ID")
    args = parser.parse_args()

    requested_shop_id = args.shop_id.strip()
    print("Dán API key mới rồi nhấn Enter. Ký tự nhập sẽ được ẩn.")
    print("Key chỉ được lưu sau khi Pancake xác nhận đúng Shop ID.")
    api_key = getpass.getpass("API key mới (ẩn): ").strip()
    if len(api_key) < 10:
        raise SystemExit("API key không hợp lệ hoặc quá ngắn.")

    settings = get_settings()
    try:
        visible_shops = asyncio.run(discover_shops(settings.pancake_api_base_url, api_key))
    except PancakeApiError as exc:
        raise SystemExit(f"Pancake từ chối key mới: {exc}") from None

    matched_shop = next(
        (shop for shop in visible_shops if shop["shop_id"] == requested_shop_id),
        None,
    )
    if matched_shop is None:
        raise SystemExit("Key mới không truy cập được Shop ID yêu cầu; cấu hình không đổi.")

    connectors = load_connectors(settings)
    target = next(
        (connector for connector in connectors if requested_shop_id in connector.shop_ids),
        None,
    )
    if target is None:
        raise SystemExit("Shop ID chưa có trong cấu hình connector; cấu hình không đổi.")

    visible_ids = {shop["shop_id"] for shop in visible_shops}
    missing_ids = target.shop_ids - visible_ids
    if missing_ids:
        raise SystemExit(
            "Key mới không truy cập được mọi shop của connector hiện tại; cấu hình không đổi."
        )

    updated = replace_connector_key(
        connectors,
        shop_id=requested_shop_id,
        api_key=api_key,
    )
    write_connectors(settings.pancake_connectors_file, updated)
    print(
        f"Đã thay key an toàn cho {matched_shop['shop_name']} "
        f"(Shop ID: {requested_shop_id})."
    )


if __name__ == "__main__":
    main()
