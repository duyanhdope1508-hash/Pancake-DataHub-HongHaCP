from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app import main
from app.main import app
from app.models import User


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
