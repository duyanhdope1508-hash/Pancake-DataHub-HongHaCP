import logging
from contextlib import contextmanager

from app import worker
from app.config import Settings


async def test_run_cycle_syncs_before_transform(monkeypatch) -> None:
    events: list[str] = []

    async def fake_sync(_: Settings) -> dict[str, bool]:
        events.append("sync")
        return {"success": True}

    def fake_transform() -> dict[str, int]:
        events.append("transform")
        return {"orders_transformed": 3}

    @contextmanager
    def fake_lock():
        yield True

    monkeypatch.setattr(worker, "sync_all", fake_sync)
    monkeypatch.setattr(worker, "transform_raw_orders", fake_transform)
    monkeypatch.setattr(worker, "sync_cycle_lock", fake_lock)

    result = await worker.run_cycle(Settings(_env_file=None))

    assert events == ["sync", "transform"]
    assert result == {
        "status": "completed",
        "sync": {"success": True},
        "transform": {"orders_transformed": 3},
    }


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


def test_http_request_logging_is_disabled_to_protect_api_keys() -> None:
    httpx_logger = logging.getLogger("httpx")
    previous_level = httpx_logger.level
    try:
        worker.configure_logging()
        assert httpx_logger.level == logging.WARNING
    finally:
        httpx_logger.setLevel(previous_level)
