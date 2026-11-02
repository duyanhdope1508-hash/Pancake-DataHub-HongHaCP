from typing import Any

from app.config import Settings
from app.pancake import PancakeClient

ID_FIELD_CANDIDATES = ("id", "order_id", "source_order_id")
UPDATE_FIELD_CANDIDATES = ("updated_at", "update_time", "modified_at", "last_updated_at")


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    fields = sorted({str(key) for record in records for key in record})
    return {
        "sample_count": len(records),
        "fields": fields,
        "id_fields_present": [field for field in ID_FIELD_CANDIDATES if field in fields],
        "update_fields_present": [
            field for field in UPDATE_FIELD_CANDIDATES if field in fields
        ],
    }


def _shop_id(shop: dict[str, Any]) -> str | None:
    value = shop.get("id") or shop.get("shop_id")
    return str(value) if value is not None else None


def _shop_name(shop: dict[str, Any], shop_id: str) -> str:
    value = shop.get("name") or shop.get("shop_name") or shop.get("display_name")
    return str(value) if value else f"Shop {shop_id}"


async def inspect_orders(settings: Settings) -> dict[str, Any]:
    allowlist = settings.shop_allowlist
    summaries: list[dict[str, Any]] = []

    async with PancakeClient(
        settings.pancake_api_base_url, settings.require_pancake_key()
    ) as client:
        shops = await client.list_shops()
        for shop in shops:
            shop_id = _shop_id(shop)
            if not shop_id or (allowlist and shop_id not in allowlist):
                continue

            orders = await client.list_orders(
                shop_id,
                page_number=1,
                page_size=min(settings.pancake_page_size, 5),
            )
            summaries.append(
                {
                    "shop_id": shop_id,
                    "shop_name": _shop_name(shop, shop_id),
                    **summarize_records(orders),
                }
            )

    if not summaries:
        raise RuntimeError("No shop matched PANCAKE_SHOP_IDS")
    return {"success": True, "shops": summaries}

