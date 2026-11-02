from collections.abc import Sequence

from sqlalchemy import Engine, text

MIGRATIONS: Sequence[tuple[str, Sequence[str]]] = (
    (
        "20261102_001_add_core_order_page",
        (
            "ALTER TABLE core_orders ADD COLUMN IF NOT EXISTS source_page_id VARCHAR(128)",
            "ALTER TABLE core_orders ADD COLUMN IF NOT EXISTS page_name TEXT",
            (
                "CREATE INDEX IF NOT EXISTS ix_core_orders_shop_page "
                "ON core_orders (shop_id, source_page_id)"
            ),
        ),
    ),
    (
        "20261102_002_add_sync_connector_name",
        (
            "ALTER TABLE sync_runs ADD COLUMN IF NOT EXISTS connector_name VARCHAR(128)",
            (
                "CREATE INDEX IF NOT EXISTS ix_sync_runs_connector_started "
                "ON sync_runs (connector_name, started_at)"
            ),
        ),
    ),
    (
        "20261102_003_add_order_fulfillment_fields",
        (
            "ALTER TABLE core_orders ADD COLUMN IF NOT EXISTS tracking_code VARCHAR(255)",
            "ALTER TABLE core_orders ADD COLUMN IF NOT EXISTS tracking_link TEXT",
            "ALTER TABLE core_orders ADD COLUMN IF NOT EXISTS shipping_fee NUMERIC(18, 2)",
            "ALTER TABLE core_orders ADD COLUMN IF NOT EXISTS carrier_name TEXT",
            "ALTER TABLE core_orders ADD COLUMN IF NOT EXISTS delivery_status VARCHAR(128)",
            "ALTER TABLE core_orders ADD COLUMN IF NOT EXISTS sent_to_carrier_at TIMESTAMPTZ",
            "ALTER TABLE core_orders ADD COLUMN IF NOT EXISTS returned_reason TEXT",
            "ALTER TABLE core_orders ADD COLUMN IF NOT EXISTS return_fee NUMERIC(18, 2)",
            (
                "CREATE INDEX IF NOT EXISTS ix_core_orders_tracking_code "
                "ON core_orders (tracking_code)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS ix_core_orders_delivery_status "
                "ON core_orders (shop_id, delivery_status)"
            ),
        ),
    ),
)


def apply_migrations(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    migration_id VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )

        for migration_id, statements in MIGRATIONS:
            already_applied = connection.scalar(
                text(
                    "SELECT EXISTS(SELECT 1 FROM schema_migrations "
                    "WHERE migration_id = :migration_id)"
                ),
                {"migration_id": migration_id},
            )
            if already_applied:
                continue

            for statement in statements:
                connection.execute(text(statement))
            connection.execute(
                text(
                    "INSERT INTO schema_migrations (migration_id) "
                    "VALUES (:migration_id)"
                ),
                {"migration_id": migration_id},
            )

