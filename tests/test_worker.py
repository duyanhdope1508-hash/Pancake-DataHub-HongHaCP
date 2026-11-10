import logging
from contextlib import contextmanager
from unittest.mock import MagicMock

from app import worker
from app.config import Settings


async def test_run_cycle_syncs_before_transform(monkeypatch, caplog) -> None:
    events: list[str] = []

    async def fake_sync(_: Settings) -> dict[str, bool]:
        events.append("sync")
        return {"success": True}

    def fake_transform() -> dict[str, int]:
        events.append("transform")
        return {"orders_transformed": 3}

    def fake_cancel_interrupted() -> int:
        events.append("cleanup")
        return 2

    @contextmanager
    def fake_lock():
        yield True

    monkeypatch.setattr(worker, "sync_all", fake_sync)
    monkeypatch.setattr(worker, "transform_raw_orders", fake_transform)
    monkeypatch.setattr(worker, "sync_cycle_lock", fake_lock)
    monkeypatch.setattr(worker, "cancel_interrupted_sync_runs", fake_cancel_interrupted)

    with caplog.at_level(logging.INFO, logger=worker.__name__):
        result = await worker.run_cycle(Settings(_env_file=None))

    assert events == ["cleanup", "sync", "transform"]
    assert result == {
        "status": "completed",
        "sync": {"success": True},
        "transform": {"orders_transformed": 3},
    }
    assert "Sync phase started" in caplog.text
    assert "Cancelled 2 interrupted sync runs" in caplog.text
    assert "Sync phase completed" in caplog.text
    assert "Transform phase started" in caplog.text
    assert "Transform phase completed" in caplog.text


async def test_run_cycle_skips_when_another_cycle_has_lock(monkeypatch) -> None:
    @contextmanager
    def busy_lock():
        yield False

    async def unexpected_sync(_: Settings) -> dict:
        raise AssertionError("sync must not run while the cycle lock is held")

    monkeypatch.setattr(worker, "sync_cycle_lock", busy_lock)
    monkeypatch.setattr(worker, "sync_all", unexpected_sync)

    result = await worker.run_cycle(Settings(_env_file=None))

    assert result == {"status": "skipped", "reason": "already_running"}


def test_interrupted_sync_runs_are_cancelled_before_new_cycle(monkeypatch) -> None:
    context = MagicMock()
    context.__enter__.return_value.execute.return_value.rowcount = 4
    monkeypatch.setattr(worker, "SessionLocal", lambda: context)

    cancelled = worker.cancel_interrupted_sync_runs()

    assert cancelled == 4
    context.__enter__.return_value.commit.assert_called_once_with()


def test_http_request_logging_is_disabled_to_protect_api_keys() -> None:
    httpx_logger = logging.getLogger("httpx")
    previous_level = httpx_logger.level
    try:
        worker.configure_logging()
        assert httpx_logger.level == logging.WARNING
    finally:
        httpx_logger.setLevel(previous_level)


def test_audit_cleanup_runs_at_most_once_per_interval(monkeypatch) -> None:
    calls: list[int] = []

    def fake_cleanup(_settings: Settings) -> dict[str, int]:
        calls.append(1)
        return {"detail_events_deleted": 10}

    monkeypatch.setattr(worker, "run_audit_cleanup", fake_cleanup)
    monkeypatch.setattr(worker, "_last_audit_cleanup_at", None)
    settings = Settings(_env_file=None, audit_cleanup_interval_seconds=86_400)

    first = worker.cleanup_audit_history_if_due(settings, current_monotonic=100.0)
    second = worker.cleanup_audit_history_if_due(settings, current_monotonic=200.0)
    third = worker.cleanup_audit_history_if_due(settings, current_monotonic=86_501.0)

    assert first == {"detail_events_deleted": 10}
    assert second is None
    assert third == {"detail_events_deleted": 10}
    assert len(calls) == 2


def test_sync_cycle_health_detects_partial_failure() -> None:
    assert worker.sync_cycle_health({"status": "skipped"}) is None
    assert worker.sync_cycle_health(
        {"status": "completed", "sync": {"success": False}}
    ) is False
    assert worker.sync_cycle_health(
        {"status": "completed", "sync": {"success": True}}
    ) is True


def test_sync_failure_message_contains_counts_without_secrets() -> None:
    message = worker.sync_failure_message(
        {
            "status": "completed",
            "sync": {
                "success": False,
                "connectors_failed": 2,
                "shops_processed": 29,
                "errors": [
                    {"connector": "shop-715173157", "error": "No shops found"}
                ],
            },
        },
        Settings(_env_file=None, pancake_sync_interval_seconds=43_200),
    )

    assert "Kết nối lỗi: 2" in message
    assert "Shop đã xử lý: 29" in message
    assert "shop-715173157" in message
    assert "12 giờ" in message
