from datetime import UTC, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert

from app.config import Settings
from app.db import SessionLocal
from app.models import RawOrder, Shop, SyncRun
from app.pancake import PancakeClient


def _record_id(record: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return None


def _shop_name(shop: dict[str, Any], shop_id: str) -> str:
    for key in ("name", "shop_name", "display_name"):
        value = shop.get(key)
        if value:
            return str(value)
    return f"Shop {shop_id}"


async def probe(settings: Settings) -> list[dict[str, str]]:
    async with PancakeClient(
        settings.pancake_api_base_url, settings.require_pancake_key()
    ) as client:
        shops = await client.list_shops()

    result: list[dict[str, str]] = []
    for shop in shops:
        shop_id = _record_id(shop, "id", "shop_id")
        if shop_id:
            result.append({"id": shop_id, "name": _shop_name(shop, shop_id)})
    return result


async def sync_all(settings: Settings) -> dict[str, int]:
    api_key = settings.require_pancake_key()
    allowlist = settings.shop_allowlist
    total_seen = 0
    total_written = 0
    total_pages = 0
    shops_processed = 0

    async with PancakeClient(settings.pancake_api_base_url, api_key) as client:
        shops = await client.list_shops()
        for shop_payload in shops:
            shop_id = _record_id(shop_payload, "id", "shop_id")
            if not shop_id or (allowlist and shop_id not in allowlist):
                continue
            shops_processed += 1

            with SessionLocal() as session:
                session.execute(
                    insert(Shop)
                    .values(
                        id=shop_id,
                        name=_shop_name(shop_payload, shop_id),
                        raw_payload=shop_payload,
                    )
                    .on_conflict_do_update(
                        index_elements=[Shop.id],
                        set_={
                            "name": _shop_name(shop_payload, shop_id),
                            "raw_payload": shop_payload,
                            "updated_at": datetime.now(UTC),
                        },
                    )
                )
                run = SyncRun(shop_id=shop_id)
                session.add(run)
                session.commit()

                try:
                    page_number = 1
                    while page_number <= settings.pancake_max_pages:
                        orders = await client.list_orders(
                            shop_id,
                            page_number=page_number,
                            page_size=settings.pancake_page_size,
                        )
                        if not orders:
                            break
                        total_pages += 1

                        page_written = 0
                        for order in orders:
                            total_seen += 1
                            run.rows_seen += 1
                            order_id = _record_id(order, "id", "order_id", "source_order_id")
                            if not order_id:
                                continue

                            source_updated_at = order.get("updated_at") or order.get("update_time")
                            session.execute(
                                insert(RawOrder)
                                .values(
                                    shop_id=shop_id,
                                    source_order_id=order_id,
                                    payload=order,
                                    source_updated_at=(
                                        str(source_updated_at) if source_updated_at else None
                                    ),
                                )
                                .on_conflict_do_update(
                                    index_elements=[RawOrder.shop_id, RawOrder.source_order_id],
                                    set_={
                                        "payload": order,
                                        "source_updated_at": (
                                            str(source_updated_at) if source_updated_at else None
                                        ),
                                        "ingested_at": datetime.now(UTC),
                                    },
                                )
                            )
                            page_written += 1

                        run.rows_written += page_written
                        total_written += page_written
                        session.commit()

                        if len(orders) < settings.pancake_page_size:
                            break
                        page_number += 1

                    run.status = "success"
                    run.finished_at = datetime.now(UTC)
                    session.commit()
                except Exception as exc:
                    session.rollback()
                    failed_run = session.get(SyncRun, run.id)
                    if failed_run:
                        failed_run.status = "failed"
                        failed_run.error = str(exc)[:2000]
                        failed_run.finished_at = datetime.now(UTC)
                        session.commit()
                    raise

    return {
        "shops_processed": shops_processed,
        "pages_processed": total_pages,
        "rows_seen": total_seen,
        "rows_written": total_written,
        "page_limit": settings.pancake_max_pages,
    }

