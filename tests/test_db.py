from app.db import database_engine_options


def test_database_engine_uses_bounded_resilient_pool() -> None:
    options = database_engine_options()

    assert options["pool_pre_ping"] is True
    assert options["pool_size"] >= 1
    assert options["max_overflow"] >= 0
    assert options["pool_timeout"] >= 1
    assert options["pool_recycle"] >= 60
    assert options["pool_use_lifo"] is True
