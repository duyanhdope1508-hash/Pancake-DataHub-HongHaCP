from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import and_, delete, func, or_, select, tuple_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.business_status import classify_business_status
from app.db import SessionLocal
from app.models import CoreCustomer, CoreOrder, CoreOrderItem, RawOrder

TRANSFORM_BATCH_SIZE = 500


def parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip())
    except ValueError:
        return None


def parse_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def normalize_phone(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    digits = "".join(character for character in value if character.isdigit())
    return digits or None


def normalize_customer_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).lower()


def build_order_search_text(*values: Any) -> str:
    return " ".join(
        str(value).strip()
        for value in values
        if value is not None and str(value).strip()
    )


def _first_string(value: Any) -> str | None:
    if not isinstance(value, list):
        return None
    for item in value:
        if isinstance(item, str) and item.strip():
            return item.strip()
    return None


def _string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def extract_page(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    page = payload.get("page") if isinstance(payload.get("page"), dict) else {}
    page_id = _string(payload.get("page_id")) or _string(page.get("id"))
    return page_id, _string(page.get("name"))


def _upsert_batch(
    session: Session,
    model: type[CoreCustomer] | type[CoreOrder],
    values: list[dict[str, Any]],
    *,
    conflict_columns: list[Any],
) -> None:
    if not values:
        return
    statement = insert(model).values(values)
    primary_key_names = {column.name for column in conflict_columns}
    update_values = {
        key: getattr(statement.excluded, key)
        for key in values[0]
        if key not in primary_key_names
    }
    session.execute(
        statement.on_conflict_do_update(
            index_elements=conflict_columns,
            set_=update_values,
        )
    )


def transform_raw_orders(*, full: bool = False) -> dict[str, int | str]:
    orders_transformed = 0
    customers_transformed = 0
    items_transformed = 0
    batches_processed = 0

    with SessionLocal() as session:
        if full:
            compacted_orders = session.scalar(
                select(func.count()).select_from(RawOrder).where(
                    RawOrder.payload.is_(None)
                )
            )
            if compacted_orders:
                raise RuntimeError(
                    "Full raw rebuild is unavailable after payload compaction; "
                    "restore a pre-compaction backup or run a Pancake backfill first."
                )
            session.execute(delete(CoreOrderItem))
        last_shop_id: str | None = None
        last_order_id: str | None = None

        while True:
            statement = select(RawOrder).where(RawOrder.payload.is_not(None))
            if not full:
                statement = statement.outerjoin(
                    CoreOrder,
                    and_(
                        CoreOrder.shop_id == RawOrder.shop_id,
                        CoreOrder.source_order_id == RawOrder.source_order_id,
                    ),
                ).where(
                    or_(
                        CoreOrder.source_order_id.is_(None),
                        RawOrder.ingested_at > CoreOrder.transformed_at,
                    )
                )
            statement = statement.order_by(
                RawOrder.shop_id.asc(), RawOrder.source_order_id.asc()
            ).limit(TRANSFORM_BATCH_SIZE)
            if last_shop_id is not None and last_order_id is not None:
                statement = statement.where(
                    or_(
                        RawOrder.shop_id > last_shop_id,
                        and_(
                            RawOrder.shop_id == last_shop_id,
                            RawOrder.source_order_id > last_order_id,
                        ),
                    )
                )
            raw_orders = list(session.scalars(statement).all())
            if not raw_orders:
                break

            customer_batch: dict[tuple[str, str], dict[str, Any]] = {}
            order_batch: list[dict[str, Any]] = []
            item_batch: list[dict[str, Any]] = []
            transformed_at = datetime.now(UTC)

            for raw_order in raw_orders:
                payload = raw_order.payload
                if payload is None:  # Defensive guard for static type checkers.
                    continue
                customer = (
                    payload.get("customer")
                    if isinstance(payload.get("customer"), dict)
                    else {}
                )
                customer_id = _string(customer.get("id"))

                if customer_id:
                    primary_phone = _first_string(customer.get("phone_numbers"))
                    customer_values = {
                        "shop_id": raw_order.shop_id,
                        "source_customer_id": customer_id,
                        "name": _string(customer.get("name")),
                        "primary_phone": primary_phone,
                        "normalized_phone": normalize_phone(primary_phone),
                        "primary_email": _first_string(customer.get("emails")),
                        "source_updated_at": parse_datetime(customer.get("updated_at")),
                        "transformed_at": transformed_at,
                    }
                    customer_batch[(raw_order.shop_id, customer_id)] = customer_values
                    customers_transformed += 1

                shipping = (
                    payload.get("shipping_address")
                    if isinstance(payload.get("shipping_address"), dict)
                    else {}
                )
                partner = (
                    payload.get("partner") if isinstance(payload.get("partner"), dict) else {}
                )
                full_address = (
                    shipping.get("new_full_address")
                    or shipping.get("full_address")
                    or shipping.get("address")
                )
                page_id, page_name = extract_page(payload)
                status = (
                    payload.get("status")
                    if isinstance(payload.get("status"), int)
                    else None
                )
                status_name = _string(payload.get("status_name"))
                delivery_status = _string(partner.get("partner_status"))
                sent_to_carrier_at = (
                    parse_datetime(payload.get("time_send_partner"))
                    or parse_datetime(partner.get("picked_up_at"))
                )
                tracking_code = (
                    _string(partner.get("extend_code"))
                    or _string(partner.get("order_number_vtp"))
                    or _string(partner.get("order_id_ghn"))
                    or _string(partner.get("custom_partner_id"))
                )
                shipping_name = _string(shipping.get("full_name"))
                shipping_phone = _string(shipping.get("phone_number"))
                customer_name = _string(customer.get("name"))
                customer_phone = _first_string(customer.get("phone_numbers"))
                customer_name_search = normalize_customer_name(
                    customer_name or shipping_name
                )
                customer_group_key = (
                    normalize_phone(customer_phone)
                    or customer_name_search
                    or customer_id
                    or raw_order.source_order_id
                )
                items = payload.get("items") if isinstance(payload.get("items"), list) else []
                product_names = [
                    _string(item["variation_info"].get("name"))
                    for item in items
                    if isinstance(item, dict)
                    and isinstance(item.get("variation_info"), dict)
                ]
                order_batch.append(
                    {
                        "shop_id": raw_order.shop_id,
                        "source_order_id": raw_order.source_order_id,
                        "source_customer_id": customer_id,
                        "source_page_id": page_id,
                        "page_name": page_name,
                        "status": status,
                        "status_name": status_name,
                        "business_status": classify_business_status(
                            status=status,
                            status_name=status_name,
                            delivery_status=delivery_status,
                            sent_to_carrier_at=sent_to_carrier_at,
                        ),
                        "inserted_at": parse_datetime(payload.get("inserted_at")),
                        "source_updated_at": parse_datetime(payload.get("updated_at")),
                        "total_price": parse_decimal(payload.get("total_price")),
                        "total_quantity": parse_decimal(payload.get("total_quantity")),
                        "currency": _string(payload.get("order_currency")),
                        "shipping_name": shipping_name,
                        "shipping_phone": shipping_phone,
                        "shipping_address": _string(full_address),
                        "tracking_code": tracking_code,
                        "tracking_link": _string(payload.get("tracking_link")),
                        "shipping_fee": parse_decimal(payload.get("shipping_fee")),
                        "carrier_name": (
                            _string(partner.get("partner_name"))
                            or _string(partner.get("service_partner"))
                        ),
                        "delivery_status": delivery_status,
                        "sent_to_carrier_at": sent_to_carrier_at,
                        "returned_reason": (
                            _string(payload.get("returned_reason_name"))
                            or _string(payload.get("returned_reason"))
                        ),
                        "return_fee": parse_decimal(payload.get("return_fee")),
                        "customer_name_search": customer_name_search,
                        "customer_group_key": customer_group_key,
                        "search_text": build_order_search_text(
                            raw_order.source_order_id,
                            tracking_code,
                            shipping_name,
                            shipping_phone,
                            full_address,
                            customer_name,
                            normalize_phone(customer_phone),
                            *product_names,
                        ),
                        "transformed_at": transformed_at,
                    }
                )
                orders_transformed += 1

                for line_number, item in enumerate(items, start=1):
                    if not isinstance(item, dict):
                        continue
                    variation_info = (
                        item.get("variation_info")
                        if isinstance(item.get("variation_info"), dict)
                        else {}
                    )
                    item_batch.append(
                        {
                            "shop_id": raw_order.shop_id,
                            "source_order_id": raw_order.source_order_id,
                            "line_number": line_number,
                            "source_item_id": _string(item.get("id")),
                            "product_name": _string(variation_info.get("name")),
                            "quantity": parse_decimal(item.get("quantity")),
                            "unit_price": parse_decimal(variation_info.get("retail_price")),
                            "total_discount": parse_decimal(item.get("total_discount")),
                            "transformed_at": transformed_at,
                        }
                    )
                    items_transformed += 1

            _upsert_batch(
                session,
                CoreCustomer,
                list(customer_batch.values()),
                conflict_columns=[
                    CoreCustomer.shop_id,
                    CoreCustomer.source_customer_id,
                ],
            )
            _upsert_batch(
                session,
                CoreOrder,
                order_batch,
                conflict_columns=[CoreOrder.shop_id, CoreOrder.source_order_id],
            )
            if not full:
                order_keys = [
                    (raw_order.shop_id, raw_order.source_order_id)
                    for raw_order in raw_orders
                ]
                session.execute(
                    delete(CoreOrderItem).where(
                        tuple_(
                            CoreOrderItem.shop_id,
                            CoreOrderItem.source_order_id,
                        ).in_(order_keys)
                    )
                )
            if item_batch:
                session.execute(insert(CoreOrderItem).values(item_batch))

            order_keys = [
                (raw_order.shop_id, raw_order.source_order_id)
                for raw_order in raw_orders
            ]
            session.execute(
                update(RawOrder)
                .where(
                    tuple_(RawOrder.shop_id, RawOrder.source_order_id).in_(order_keys),
                    RawOrder.payload_hash.is_not(None),
                )
                .values(payload=None, compacted_at=transformed_at)
            )

            last_order = raw_orders[-1]
            last_shop_id = last_order.shop_id
            last_order_id = last_order.source_order_id
            batches_processed += 1
            if not full:
                session.commit()

        session.commit()

    return {
        "mode": "full" if full else "incremental",
        "batches_processed": batches_processed,
        "orders_transformed": orders_transformed,
        "customers_transformed": customers_transformed,
        "items_transformed": items_transformed,
    }

