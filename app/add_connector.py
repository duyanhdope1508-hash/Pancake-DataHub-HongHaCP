import argparse
import asyncio
import getpass
import json
from pathlib import Path

from app.config import get_settings
from app.connectors import PancakeConnector, load_connectors
from app.pancake import PancakeApiError
from app.probe_key import discover_shops


def merge_connector(
    connectors: list[PancakeConnector],
    *,
    name: str,
    shop_id: str,
    api_key: str,
) -> list[PancakeConnector]:
    clean_name = name.strip()
    clean_shop_id = shop_id.strip()
    if not clean_name:
        raise ValueError("Connector name cannot be empty")
    if not clean_shop_id:
        raise ValueError("Shop ID cannot be empty")
    if any(connector.name == clean_name for connector in connectors):
        raise ValueError(f"Connector name already exists: {clean_name}")
    if any(clean_shop_id in connector.shop_ids for connector in connectors):
        raise ValueError(f"Shop ID is already configured: {clean_shop_id}")

    return [
        *connectors,
        PancakeConnector(
            name=clean_name,
            shop_ids=frozenset({clean_shop_id}),
            api_key=api_key,
        ),
    ]


def write_connectors(path: Path, connectors: list[PancakeConnector]) -> None:
    payload = {
        "connectors": [
            {
                "name": connector.name,
                "shop_ids": sorted(connector.shop_ids),
                "api_key": connector.api_key,
            }
            for connector in connectors
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f"{path.name}.tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.chmod(0o600)
    temporary_path.replace(path)
    path.chmod(0o600)


def main() -> None:
    parser = argparse.ArgumentParser(description="Add a Pancake connector securely")
    parser.add_argument("--name", required=True, help="local connector name")
    parser.add_argument("--shop-id", required=True, help="Pancake Shop ID")
    args = parser.parse_args()

    print("Dán API key của cửa hàng mới rồi nhấn Enter.")
    print("Ký tự nhập sẽ được ẩn; key chỉ được lưu trong file secrets bị Git bỏ qua.")
    api_key = getpass.getpass("API key mới (ẩn): ").strip()
    if len(api_key) < 10:
        raise SystemExit("API key không hợp lệ hoặc quá ngắn.")

    settings = get_settings()
    try:
        visible_shops = asyncio.run(discover_shops(settings.pancake_api_base_url, api_key))
    except PancakeApiError as exc:
        raise SystemExit(f"Pancake từ chối yêu cầu: {exc}") from None

    requested_shop_id = args.shop_id.strip()
    matched_shop = next(
        (shop for shop in visible_shops if shop["shop_id"] == requested_shop_id),
        None,
    )
    if matched_shop is None:
        raise SystemExit("API key không truy cập được Shop ID đã nhập; không thay đổi cấu hình.")

    try:
        connectors = merge_connector(
            load_connectors(settings),
            name=args.name,
            shop_id=requested_shop_id,
            api_key=api_key,
        )
    except (TypeError, ValueError) as exc:
        raise SystemExit(str(exc)) from None

    write_connectors(settings.pancake_connectors_file, connectors)
    print(
        f"Đã thêm {matched_shop['shop_name']} ({requested_shop_id}). "
        f"Tổng số connector: {len(connectors)}."
    )


if __name__ == "__main__":
    main()
