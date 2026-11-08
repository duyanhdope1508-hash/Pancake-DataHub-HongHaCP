from datetime import UTC, datetime
from unittest.mock import Mock

from app.audit import (
    add_audit_event,
    cleanup_audit_history,
    list_audit_logs,
    list_security_alerts,
)
from app.models import AuditLog


def test_cleanup_aggregates_old_detail_events_before_deleting() -> None:
    session = Mock()
    session.execute.side_effect = [
        Mock(),
        Mock(rowcount=2),
        Mock(rowcount=150),
        Mock(rowcount=12),
    ]
    now = datetime(2026, 11, 6, 8, 0, tzinfo=UTC)

    result = cleanup_audit_history(
        session,
        detail_retention_days=90,
        general_retention_days=365,
        now=now,
    )

    assert result == {
        "summaries_upserted": 2,
        "detail_events_deleted": 150,
        "general_events_deleted": 12,
    }
    aggregate_statement = str(session.execute.call_args_list[1].args[0])
    assert "orders.view_detail.daily" in aggregate_statement
    assert "ON CONFLICT (id) DO UPDATE" in aggregate_statement
    session.flush.assert_called_once_with()


def test_order_detail_audit_is_deduplicated_within_window() -> None:
    session = Mock()
    session.scalar.return_value = "existing-event"
    now = datetime(2026, 11, 6, 8, 0, tzinfo=UTC)

    event = add_audit_event(
        session,
        actor_user_id="staff-1",
        action="orders.view_detail",
        resource_type="order",
        resource_id="shop-1:order-1",
        result="success",
        metadata={"shop_id": "shop-1"},
        ip_address="192.0.2.25",
        user_agent="Browser",
        deduplicate_seconds=600,
        now=now,
    )

    assert event is None
    session.add.assert_not_called()
    session.execute.assert_called_once()


def test_order_detail_audit_is_recorded_after_dedup_window() -> None:
    session = Mock()
    session.scalar.return_value = None
    now = datetime(2026, 11, 6, 8, 0, tzinfo=UTC)

    event = add_audit_event(
        session,
        actor_user_id="staff-1",
        action="orders.view_detail",
        resource_type="order",
        resource_id="shop-1:order-1",
        result="success",
        metadata={"shop_id": "shop-1"},
        ip_address="192.0.2.25",
        user_agent="Browser",
        deduplicate_seconds=600,
        now=now,
    )

    assert event is not None
    assert event.created_at == now
    session.add.assert_called_once_with(event)
    session.flush.assert_called_once_with()


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
    session.execute.side_effect = [
        Mock(all=Mock(return_value=[(audit_log, "admin", "Daniel Ng")])),
        Mock(all=Mock(return_value=[("user-1", "admin", "Daniel Ng")])),
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
    assert result["actors"] == [
        {"user_id": "user-1", "username": "admin", "display_name": "Daniel Ng"}
    ]
    assert result["results"] == ["auth.login", "orders.export"]
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
    session.execute.side_effect = [
        Mock(all=Mock(return_value=[])),
        Mock(all=Mock(return_value=[])),
    ]
    session.scalars.return_value.all.return_value = ["staff.update"]

    result = list_audit_logs(
        session,
        page_number=2,
        page_size=25,
        action="staff.update",
        actor_user_id="staff-1",
        result="success",
        ip_address="192.0.2.1",
        date_from=datetime(2026, 11, 1, tzinfo=UTC),
        date_to=datetime(2026, 11, 6, tzinfo=UTC),
    )

    assert result["items"] == []
    assert result["pagination"]["page_number"] == 2


def test_regular_admin_audit_scope_excludes_admin_and_system_actors() -> None:
    session = Mock()
    session.scalar.return_value = 0
    session.execute.side_effect = [
        Mock(all=Mock(return_value=[])),
        Mock(all=Mock(return_value=[])),
    ]
    session.scalars.return_value.all.return_value = []

    result = list_audit_logs(
        session,
        actor_user_id="root-user-id",
        visible_actor_roles=("staff",),
    )

    count_sql = str(session.scalar.call_args.args[0])
    rows_sql = str(session.execute.call_args_list[0].args[0])
    actors_sql = str(session.execute.call_args_list[1].args[0])
    option_sql = [str(call.args[0]) for call in session.scalars.call_args_list]

    assert result["items"] == []
    assert "auth_users.role IN" in count_sql
    assert "audit_logs.actor_user_id =" in count_sql
    assert "auth_users.role IN" in rows_sql
    assert "auth_users.role IN" in actors_sql
    assert all("auth_users.role IN" in statement for statement in option_sql)


def test_security_alerts_return_recent_actor_and_usage() -> None:
    session = Mock()
    session.scalar.return_value = 1
    alert = AuditLog(
        id="alert-1",
        actor_user_id="staff-1",
        action="security.high_usage",
        resource_type="api",
        resource_id="orders.list.rows.burst",
        result="warning",
        metadata_json={"used": 240, "limit": 300, "percent": 80},
        ip_address="192.0.2.25",
        user_agent="Mozilla/5.0 Chrome/130.0 Windows",
        created_at=datetime(2026, 11, 6, 8, 0, tzinfo=UTC),
    )
    session.execute.return_value.all.return_value = [
        (alert, "staff", "Nhân viên A")
    ]

    result = list_security_alerts(
        session,
        hours=24,
        limit=20,
        now=datetime(2026, 11, 6, 9, 0, tzinfo=UTC),
    )

    assert result["total"] == 1
    assert result["hours"] == 24
    assert result["items"][0]["actor_username"] == "staff"
    assert result["items"][0]["metadata"]["percent"] == 80


def test_regular_admin_security_alerts_only_include_staff() -> None:
    session = Mock()
    session.scalar.return_value = 0
    session.execute.return_value.all.return_value = []

    result = list_security_alerts(
        session,
        visible_actor_roles=("staff",),
        now=datetime(2026, 11, 6, 9, 0, tzinfo=UTC),
    )

    count_sql = str(session.scalar.call_args.args[0])
    rows_sql = str(session.execute.call_args.args[0])
    assert result["items"] == []
    assert "auth_users.role IN" in count_sql
    assert "auth_users.role IN" in rows_sql
