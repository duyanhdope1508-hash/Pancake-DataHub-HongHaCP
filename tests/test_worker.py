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

    monkeypatch.setattr(worker, "sync_all", fake_sync)
    monkeypatch.setattr(worker, "transform_raw_orders", fake_transform)

    result = await worker.run_cycle(Settings(_env_file=None))

    assert events == ["sync", "transform"]
    assert result == {
        "sync": {"success": True},
        "transform": {"orders_transformed": 3},
    }
