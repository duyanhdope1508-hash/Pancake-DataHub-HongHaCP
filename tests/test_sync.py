from pathlib import Path

from sqlalchemy.dialects import postgresql

from app.config import Settings
from app.models import SyncRun
from app.sync import _raw_order_upsert, _resume_page, _scan_page_limit


def test_resume_is_disabled_by_default() -> None:
    settings = Settings(_env_file=None, pancake_start_page=3)
    latest = SyncRun(status="cancelled", start_page=1, rows_seen=500)

    assert _resume_page(settings, latest) == 3


def test_resume_skips_completed_backfill() -> None:
    settings = Settings(_env_file=None, pancake_resume_backfill=True)
    latest = SyncRun(status="success", start_page=1, rows_seen=500)

    assert _resume_page(settings, latest) is None


def test_resume_continues_after_last_committed_page() -> None:
    settings = Settings(
        _env_file=None,
        pancake_page_size=100,
        pancake_resume_backfill=True,
    )
    latest = SyncRun(status="cancelled", start_page=1, rows_seen=35_600)

    assert _resume_page(settings, latest) == 357


def test_resume_uses_the_previous_run_start_page() -> None:
    settings = Settings(
        _env_file=None,
        pancake_page_size=100,
        pancake_resume_backfill=True,
    )
    latest = SyncRun(status="cancelled", start_page=582, rows_seen=200)

    assert _resume_page(settings, latest) == 584


def test_resume_continues_after_stale_running_run() -> None:
    settings = Settings(
        _env_file=None,
        pancake_resume_backfill=True,
        pancake_page_size=100,
        pancake_start_page=1,
    )
    latest = SyncRun(status="running", start_page=1, rows_seen=13_200)

    assert _resume_page(settings, latest) == 133


def test_incremental_sync_scans_beyond_the_first_page() -> None:
    settings = Settings(
        _env_file=None,
        pancake_start_page=1,
        pancake_max_pages=1,
        pancake_incremental_max_pages=100,
    )

    assert _scan_page_limit(settings, 1) == 100


def test_backfill_keeps_its_explicit_page_limit() -> None:
    settings = Settings(
        _env_file=None,
        pancake_max_pages=100_000,
        pancake_resume_backfill=True,
    )

    assert _scan_page_limit(settings, 357) == 100_000


def test_raw_order_upsert_only_updates_changed_payloads() -> None:
    statement = _raw_order_upsert(
        shop_id="shop-1",
        order_id="order-1",
        order={"id": "order-1", "status": 1},
        source_updated_at="2026-11-08T00:00:00Z",
    )

    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "IS DISTINCT FROM" in compiled
    assert "RETURNING raw_pancake_orders.source_order_id" in compiled


def test_sync_updates_run_progress_once_per_page() -> None:
    source = Path("app/sync.py").read_text(encoding="utf-8")

    assert 'page_seen = len(orders)' in source
    assert 'run.rows_seen += page_seen' in source
    assert 'run.rows_seen += 1' not in source
