from app.config import Settings
from app.models import SyncRun
from app.sync import _resume_page


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
