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


def test_sensitive_responses_have_browser_security_headers() -> None:
    response = main._add_security_headers(Response(), no_store=True, hsts=True)

    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Cache-Control"] == "no-store, max-age=0"
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert "camera=()" in response.headers["Permissions-Policy"]


def test_audit_client_uses_server_observed_ip_and_bounds_user_agent() -> None:
    request = SimpleNamespace(
        client=SimpleNamespace(host="192.0.2.10"),
        headers={"user-agent": "browser/1.0 " + ("x" * 600)},
    )

    ip_address, user_agent = main._audit_client(request)

    assert ip_address == "192.0.2.10"
    assert user_agent is not None
    assert len(user_agent) == 512


@pytest.mark.asyncio
async def test_manual_sync_returns_safe_summary(monkeypatch) -> None:
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

    result = await main.sync_now(_request_for("admin"))

    assert result == {
        "status": "completed",
        "success": True,
        "shops_processed": 26,
        "connectors_failed": 0,
        "rows_seen": 100,
        "rows_written": 100,
        "orders_transformed": 4,
    }


@pytest.mark.asyncio
async def test_manual_sync_rejects_overlapping_cycle(monkeypatch) -> None:
    async def fake_run_cycle(_settings) -> dict:
        return {"status": "skipped", "reason": "already_running"}

    monkeypatch.setattr(main, "run_cycle", fake_run_cycle)

    with pytest.raises(HTTPException) as exc_info:
        await main.sync_now(_request_for("admin"))

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_manual_sync_is_admin_only(monkeypatch) -> None:
    mocked_run_cycle = Mock()
    monkeypatch.setattr(main, "run_cycle", mocked_run_cycle)

    with pytest.raises(HTTPException) as exc_info:
        await main.sync_now(_request_for("staff"))

    assert exc_info.value.status_code == 403
    mocked_run_cycle.assert_not_called()
