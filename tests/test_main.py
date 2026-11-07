import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException, Response

from app import main
from app.main import app
from app.models import User


@pytest.fixture(autouse=True)
def disable_audit_writes(monkeypatch) -> None:
    monkeypatch.setattr(main, "_record_audit", Mock())


def _request_for(role: str) -> SimpleNamespace:
    user = User(
        id=f"{role}-1",
        username=role,
        display_name=role.title(),
        password_hash="hash",
        role=role,
        is_active=True,
    )
    return SimpleNamespace(state=SimpleNamespace(current_user=user))


def test_system_status_route_is_registered() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/system-status" in paths
    assert "/api/sync" in paths
    assert "/api/orders/summary" in paths
    assert "/api/orders/export" in paths
    assert "/api/auth/login" in paths
    assert "/api/auth/logout" in paths
    assert "/api/auth/me" in paths
    assert "/api/auth/change-password" in paths
    assert "/api/admin/users" in paths
    assert "/api/admin/audit-logs" in paths
    export_methods = {
        method
        for route in app.routes
        if route.path == "/api/orders/export"
        for method in route.methods
    }
    assert {"GET", "POST"} <= export_methods


def test_trusted_hosts_are_configurable() -> None:
    settings = main.get_settings()

    assert settings.trusted_host_list


def test_selected_export_requires_at_least_one_order() -> None:
    payload = main.ExportOrdersRequest(selection_mode="selected")

    with pytest.raises(HTTPException) as exc_info:
        main.export_selected_orders(_request_for("admin"), payload)

    assert exc_info.value.status_code == 422


def test_selected_export_deduplicates_keys_and_ignores_stale_filters(monkeypatch) -> None:
    export_response = Mock(return_value="response")
    monkeypatch.setattr(main, "_export_orders_response", export_response)
    payload = main.ExportOrdersRequest(
        selection_mode="selected",
        q="a filter that changed after selection",
        orders=[
            main.ExportOrderKey(shop_id="shop-1", order_id="order-1"),
            main.ExportOrderKey(shop_id="shop-1", order_id="order-1"),
            main.ExportOrderKey(shop_id="shop-2", order_id="order-2"),
        ],
    )
    request = _request_for("admin")

    result = main.export_selected_orders(request, payload)

    assert result == "response"
    export_response.assert_called_once_with(
        request,
        filters={},
        order_keys=[("shop-1", "order-1"), ("shop-2", "order-2")],
        selection_mode="selected",
    )


def test_sensitive_responses_have_browser_security_headers() -> None:
    response = main._add_security_headers(Response(), no_store=True, hsts=True)

    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Cache-Control"] == "no-store, max-age=0"
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert "camera=()" in response.headers["Permissions-Policy"]


def test_frontend_assets_disable_browser_and_proxy_cache() -> None:
    assert main._should_disable_browser_cache("/") is True
    assert main._should_disable_browser_cache("/api/orders") is True
    assert main._should_disable_browser_cache("/assets/app.js") is True
    assert main._should_disable_browser_cache("/health") is False


def test_system_status_cache_shares_expensive_counts(monkeypatch) -> None:
    calls: list[tuple[str, ...] | None] = []

    def fake_database_status(shop_ids):
        calls.append(shop_ids)
        return {"core_orders": 10}

    monkeypatch.setattr(main, "database_status", fake_database_status)
    main._cached_database_status.cache_clear()
    try:
        first = main._cached_database_status(1, None)
        second = main._cached_database_status(1, None)
        scoped = main._cached_database_status(1, ("shop-1",))
    finally:
        main._cached_database_status.cache_clear()

    assert first == second == {"core_orders": 10}
    assert scoped == {"core_orders": 10}
    assert calls == [None, ("shop-1",)]


def test_audit_client_uses_server_observed_ip_and_bounds_user_agent() -> None:
    request = SimpleNamespace(
        client=SimpleNamespace(host="192.0.2.10"),
        headers={"user-agent": "browser/1.0 " + ("x" * 600)},
    )

    ip_address, user_agent = main._audit_client(request)

    assert ip_address == "192.0.2.10"
    assert user_agent is not None
    assert len(user_agent) == 512


def test_staff_read_quota_counts_requested_order_rows() -> None:
    user = User(
        id="staff-1",
        username="staff",
        display_name="Staff",
        password_hash="hash",
        role="staff",
        is_active=True,
    )
    request = SimpleNamespace(
        method="GET",
        url=SimpleNamespace(path="/api/orders"),
        query_params={"page_size": "100"},
    )

    assert main._read_quota_policy(request, user) == (
        "orders.list.rows",
        100,
        2_000,
        3_600,
    )


@pytest.mark.asyncio
async def test_manual_sync_starts_background_job_and_returns_immediately(monkeypatch) -> None:
    async def fake_run_cycle(_settings) -> dict:
        return {
            "status": "completed",
            "sync": {
                "success": True,
                "shops_processed": 26,
                "connectors_failed": 0,
                "rows_seen": 100,
                "rows_written": 100,
            },
            "transform": {"orders_transformed": 4},
        }

    monkeypatch.setattr(main, "run_cycle", fake_run_cycle)
    monkeypatch.setattr(main, "_manual_sync_task", None)
    monkeypatch.setattr(main, "_manual_sync_state", {"status": "idle"})

    result = await main.sync_now(_request_for("admin"))

    assert result["status"] == "started"
    assert "started_at" in result
    assert main._manual_sync_task is not None
    await main._manual_sync_task

    assert main.manual_sync_status(_request_for("admin")) == {
        "status": "completed",
        "success": True,
        "shops_processed": 26,
        "connectors_failed": 0,
        "rows_seen": 100,
        "rows_written": 100,
        "orders_transformed": 4,
        "finished_at": main._manual_sync_state["finished_at"],
    }


@pytest.mark.asyncio
async def test_manual_sync_rejects_overlapping_cycle(monkeypatch) -> None:
    blocker = asyncio.Event()

    async def running_job() -> None:
        await blocker.wait()

    active_task = asyncio.create_task(running_job())
    monkeypatch.setattr(main, "_manual_sync_task", active_task)

    try:
        with pytest.raises(HTTPException) as exc_info:
            await main.sync_now(_request_for("admin"))

        assert exc_info.value.status_code == 409
    finally:
        blocker.set()
        await active_task


@pytest.mark.asyncio
async def test_manual_sync_is_admin_only(monkeypatch) -> None:
    mocked_run_cycle = Mock()
    monkeypatch.setattr(main, "run_cycle", mocked_run_cycle)

    with pytest.raises(HTTPException) as exc_info:
        await main.sync_now(_request_for("staff"))

    assert exc_info.value.status_code == 403
    mocked_run_cycle.assert_not_called()


def test_manual_sync_status_is_admin_only() -> None:
    with pytest.raises(HTTPException) as exc_info:
        main.manual_sync_status(_request_for("staff"))

    assert exc_info.value.status_code == 403
