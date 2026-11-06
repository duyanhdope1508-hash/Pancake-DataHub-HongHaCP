from datetime import UTC, datetime
from unittest.mock import Mock

from app.audit import list_audit_logs
from app.models import AuditLog


def test_audit_log_listing_is_paginated_and_safe() -> None:
    session = Mock()
    session.scalar.return_value = 2
    audit_log = AuditLog(
        id="audit-1",
        actor_user_id="user-1",
        action="orders.export",
        resource_type="orders",
        resource_id=None,
        result="success",
        metadata_json={"order_count": 12},
        ip_address="192.0.2.25",
        user_agent="Mozilla/5.0 Chrome/130.0 Windows",
        created_at=datetime(2026, 11, 6, 8, 0, tzinfo=UTC),
    )
    session.execute.return_value.all.return_value = [
        (audit_log, "admin", "Daniel Ng")
    ]
    session.scalars.return_value.all.return_value = [
        "auth.login",
        "orders.export",
    ]

    result = list_audit_logs(session, page_number=1, page_size=50)

    assert result["pagination"] == {
        "page_number": 1,
        "page_size": 50,
        "total_items": 2,
        "total_pages": 1,
    }
    assert result["actions"] == ["auth.login", "orders.export"]
    assert result["items"][0] == {
        "id": "audit-1",
        "actor_username": "admin",
        "actor_display_name": "Daniel Ng",
        "action": "orders.export",
        "resource_type": "orders",
        "resource_id": None,
        "result": "success",
        "metadata": {"order_count": 12},
        "ip_address": "192.0.2.25",
        "user_agent": "Mozilla/5.0 Chrome/130.0 Windows",
        "created_at": datetime(2026, 11, 6, 8, 0, tzinfo=UTC),
    }


def test_audit_log_listing_supports_action_filter() -> None:
    session = Mock()
    session.scalar.return_value = 0
    session.execute.return_value.all.return_value = []
    session.scalars.return_value.all.return_value = ["staff.update"]

    result = list_audit_logs(
        session,
        page_number=2,
        page_size=25,
        action="staff.update",
    )

    assert result["items"] == []
    assert result["pagination"]["page_number"] == 2
