from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from app.db import SessionLocal
from app.models import CoreCustomer, CoreOrder, CoreOrderItem, RawOrder


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


def transform_raw_orders() -> dict[str, int]:
    orders_transformed = 0
    customers_transformed = 0
    items_transformed = 0

    with SessionLocal() as session:
        raw_orders = session.scalars(select(RawOrder)).all()

        for raw_order in raw_orders:
            payload = raw_order.payload
            customer = payload.get("customer") if isinstance(payload.get("customer"), dict) else {}
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
                }
                session.execute(
                    insert(CoreCustomer)
                    .values(**customer_values)
                    .on_conflict_do_update(
                        index_elements=[
                            CoreCustomer.shop_id,
                            CoreCustomer.source_customer_id,
                        ],
                        set_=customer_values,
                    )
                )
                customers_transformed += 1

            shipping = (
                payload.get("shipping_address")
                if isinstance(payload.get("shipping_address"), dict)
                else {}
            )
            full_address = (
                shipping.get("new_full_address")
                or shipping.get("full_address")
                or shipping.get("address")
            )
            order_values = {
                "shop_id": raw_order.shop_id,
                "source_order_id": raw_order.source_order_id,
                "source_customer_id": customer_id,
                "status": payload.get("status") if isinstance(payload.get("status"), int) else None,
                "status_name": _string(payload.get("status_name")),
                "inserted_at": parse_datetime(payload.get("inserted_at")),
                "source_updated_at": parse_datetime(payload.get("updated_at")),
                "total_price": parse_decimal(payload.get("total_price")),
                "total_quantity": parse_decimal(payload.get("total_quantity")),
                "currency": _string(payload.get("order_currency")),
                "shipping_name": _string(shipping.get("full_name")),
                "shipping_phone": _string(shipping.get("phone_number")),
                "shipping_address": _string(full_address),
            }
            session.execute(
                insert(CoreOrder)
                .values(**order_values)
                .on_conflict_do_update(
                    index_elements=[CoreOrder.shop_id, CoreOrder.source_order_id],
                    set_=order_values,
                )
            )
            orders_transformed += 1

            session.execute(
                delete(CoreOrderItem).where(
                    CoreOrderItem.shop_id == raw_order.shop_id,
                    CoreOrderItem.source_order_id == raw_order.source_order_id,
                )
            )
            items = payload.get("items") if isinstance(payload.get("items"), list) else []
            for line_number, item in enumerate(items, start=1):
                if not isinstance(item, dict):
                    continue
                variation_info = (
                    item.get("variation_info")
                    if isinstance(item.get("variation_info"), dict)
                    else {}
                )
                session.add(
                    CoreOrderItem(
                        shop_id=raw_order.shop_id,
                        source_order_id=raw_order.source_order_id,
                        line_number=line_number,
                        source_item_id=_string(item.get("id")),
                        product_name=_string(variation_info.get("name")),
                        quantity=parse_decimal(item.get("quantity")),
                        unit_price=parse_decimal(variation_info.get("retail_price")),
                        total_discount=parse_decimal(item.get("total_discount")),
                    )
                )
                items_transformed += 1

        session.commit()

    return {
        "orders_transformed": orders_transformed,
        "customers_transformed": customers_transformed,
        "items_transformed": items_transformed,
    }

