from datetime import UTC, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert

from app.config import Settings
from app.connectors import PancakeConnector, load_connectors
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


def _connector_allows(connector: PancakeConnector, shop_id: str) -> bool:
    return not connector.shop_ids or shop_id in connector.shop_ids


async def probe(settings: Settings) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for connector in load_connectors(settings):
        try:
            async with PancakeClient(
                settings.pancake_api_base_url, connector.api_key
            ) as client:
                shops = await client.list_shops()
        except Exception as exc:  # noqa: BLE001 - isolate connector failures
            errors.append({"connector": connector.name, "error": str(exc)[:500]})
            continue

        visible_shops: list[dict[str, str]] = []
        for shop in shops:
            shop_id = _record_id(shop, "id", "shop_id")
            if shop_id and _connector_allows(connector, shop_id):
                visible_shops.append(
                    {"id": shop_id, "name": _shop_name(shop, shop_id)}
                )
        results.append({"connector": connector.name, "shops": visible_shops})

    return {"success": not errors, "connectors": results, "errors": errors}


async def sync_all(settings: Settings) -> dict[str, Any]:
    total_seen = 0
    total_written = 0
    total_pages = 0
    shops_processed = 0
    connectors_processed = 0
    errors: list[dict[str, str]] = []

    for connector in load_connectors(settings):
        try:
            async with PancakeClient(
                settings.pancake_api_base_url, connector.api_key
            ) as client:
                try:
                    shops = await client.list_shops()
                except Exception as exc:  # noqa: BLE001 - isolate connector failures
                    errors.append(
                        {"connector": connector.name, "shop_id": "", "error": str(exc)[:500]}
                    )
                    continue

                connectors_processed += 1
                for shop_payload in shops:
                    shop_id = _record_id(shop_payload, "id", "shop_id")
                    if not shop_id or not _connector_allows(connector, shop_id):
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
                        run = SyncRun(connector_name=connector.name, shop_id=shop_id)
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
                                    order_id = _record_id(
                                        order, "id", "order_id", "source_order_id"
                                    )
                                    if not order_id:
                                        continue

                                    source_updated_at = order.get("updated_at") or order.get(
                                        "update_time"
                                    )
                                    session.execute(
                                        insert(RawOrder)
                                        .values(
                                            shop_id=shop_id,
                                            source_order_id=order_id,
                                            payload=order,
                                            source_updated_at=(
                                                str(source_updated_at)
                                                if source_updated_at
                                                else None
                                            ),
                                        )
                                        .on_conflict_do_update(
                                            index_elements=[
                                                RawOrder.shop_id,
                                                RawOrder.source_order_id,
                                            ],
                                            set_={
                                                "payload": order,
                                                "source_updated_at": (
                                                    str(source_updated_at)
                                                    if source_updated_at
                                                    else None
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
                        except Exception as exc:  # noqa: BLE001 - isolate shop failures
                            session.rollback()
                            failed_run = session.get(SyncRun, run.id)
                            if failed_run:
                                failed_run.status = "failed"
                                failed_run.error = str(exc)[:2000]
                                failed_run.finished_at = datetime.now(UTC)
                                session.commit()
                            errors.append(
                                {
                                    "connector": connector.name,
                                    "shop_id": shop_id,
                                    "error": str(exc)[:500],
                                }
                            )
        except Exception as exc:  # noqa: BLE001 - isolate connector failures
            errors.append(
                {"connector": connector.name, "shop_id": "", "error": str(exc)[:500]}
            )

    return {
        "success": not errors,
        "connectors_processed": connectors_processed,
        "connectors_failed": len({error["connector"] for error in errors}),
        "shops_processed": shops_processed,
        "pages_processed": total_pages,
        "rows_seen": total_seen,
        "rows_written": total_written,
        "page_limit": settings.pancake_max_pages,
        "errors": errors,
    }

