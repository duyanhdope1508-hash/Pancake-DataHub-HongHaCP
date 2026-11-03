from sqlalchemy import UniqueConstraint

from app.models import CoreCustomer, CoreOrder, CustomerIdentity, MasterCustomer


def test_customer_identity_tables_have_expected_columns() -> None:
    assert {
        "id",
        "display_name",
        "primary_phone",
        "normalized_phone",
        "primary_email",
        "created_at",
        "updated_at",
    }.issubset(MasterCustomer.__table__.columns.keys())
    assert {
        "master_customer_id",
        "identity_type",
        "identity_value",
        "scope",
        "source",
        "confidence",
        "is_verified",
    }.issubset(CustomerIdentity.__table__.columns.keys())


def test_customer_identity_key_is_unique_within_scope() -> None:
    constraints = {
        constraint.name
        for constraint in CustomerIdentity.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert "uq_customer_identity_type_value_scope" in constraints


def test_source_customers_and_orders_can_link_to_master_customer() -> None:
    assert "master_customer_id" in CoreCustomer.__table__.columns
    assert "master_customer_id" in CoreOrder.__table__.columns
