from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Shop(Base):
    __tablename__ = "pancake_shops"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RawOrder(Base):
    __tablename__ = "raw_pancake_orders"

    shop_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("pancake_shops.id"), primary_key=True
    )
    source_order_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source_updated_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    connector_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    shop_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    rows_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_written: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MasterCustomer(Base):
    __tablename__ = "master_customers"
    __table_args__ = (
        Index("ix_master_customers_phone", "normalized_phone"),
        Index("ix_master_customers_name", "display_name"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    normalized_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    primary_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CustomerIdentity(Base):
    __tablename__ = "customer_identities"
    __table_args__ = (
        UniqueConstraint(
            "identity_type",
            "identity_value",
            "scope",
            name="uq_customer_identity_type_value_scope",
        ),
        Index("ix_customer_identities_master", "master_customer_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    master_customer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "master_customers.id",
            name="fk_customer_identities_master_customer",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    identity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    identity_value: Mapped[str] = mapped_column(String(512), nullable=False)
    scope: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PancakePageCustomer(Base):
    __tablename__ = "pancake_page_customers"
    __table_args__ = (
        Index("ix_page_customers_psid", "page_id", "psid"),
        Index("ix_page_customers_global_id", "global_id"),
        Index("ix_page_customers_name", "name"),
    )

    page_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    page_customer_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    source_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    psid: Mapped[str | None] = mapped_column(String(255), nullable=True)
    global_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CoreCustomer(Base):
    __tablename__ = "core_customers"
    __table_args__ = (
        Index("ix_core_customers_shop_phone", "shop_id", "normalized_phone"),
    )

    shop_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("pancake_shops.id"), primary_key=True
    )
    source_customer_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    master_customer_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "master_customers.id",
            name="fk_core_customers_master_customer",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    normalized_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    primary_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    transformed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CoreOrder(Base):
    __tablename__ = "core_orders"
    __table_args__ = (
        Index("ix_core_orders_shop_status", "shop_id", "status"),
        Index("ix_core_orders_shop_updated", "shop_id", "source_updated_at"),
        Index("ix_core_orders_shop_customer", "shop_id", "source_customer_id"),
        Index("ix_core_orders_shop_page", "shop_id", "source_page_id"),
    )

    shop_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("pancake_shops.id"), primary_key=True
    )
    source_order_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    master_customer_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "master_customers.id",
            name="fk_core_orders_master_customer",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    source_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_page_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    page_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    inserted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    total_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 3), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    shipping_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    shipping_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    shipping_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    tracking_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tracking_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    shipping_fee: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    carrier_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_status: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sent_to_carrier_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    returned_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    return_fee: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    transformed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CoreOrderItem(Base):
    __tablename__ = "core_order_items"
    __table_args__ = (
        Index("ix_core_order_items_order", "shop_id", "source_order_id"),
    )

    shop_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_order_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    line_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_item_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    product_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 3), nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    total_discount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    transformed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

