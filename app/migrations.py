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
    (
        "20261103_004_add_customer_identity_foundation",
        (
            """
            CREATE TABLE IF NOT EXISTS master_customers (
                id VARCHAR(36) PRIMARY KEY,
                display_name TEXT,
                primary_phone VARCHAR(64),
                normalized_phone VARCHAR(32),
                primary_email TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            (
                "CREATE INDEX IF NOT EXISTS ix_master_customers_phone "
                "ON master_customers (normalized_phone)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS ix_master_customers_name "
                "ON master_customers (display_name)"
            ),
            """
            CREATE TABLE IF NOT EXISTS customer_identities (
                id VARCHAR(36) PRIMARY KEY,
                master_customer_id VARCHAR(36) NOT NULL,
                identity_type VARCHAR(64) NOT NULL,
                identity_value VARCHAR(512) NOT NULL,
                scope VARCHAR(128) NOT NULL DEFAULT '',
                source VARCHAR(64) NOT NULL,
                confidence INTEGER NOT NULL DEFAULT 100,
                is_verified BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT fk_customer_identities_master_customer
                    FOREIGN KEY (master_customer_id)
                    REFERENCES master_customers (id)
                    ON DELETE CASCADE,
                CONSTRAINT uq_customer_identity_type_value_scope
                    UNIQUE (identity_type, identity_value, scope)
            )
            """,
            (
                "CREATE INDEX IF NOT EXISTS ix_customer_identities_master "
                "ON customer_identities (master_customer_id)"
            ),
            "ALTER TABLE core_customers ADD COLUMN IF NOT EXISTS master_customer_id VARCHAR(36)",
            "ALTER TABLE core_orders ADD COLUMN IF NOT EXISTS master_customer_id VARCHAR(36)",
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'fk_core_customers_master_customer'
                ) THEN
                    ALTER TABLE core_customers
                    ADD CONSTRAINT fk_core_customers_master_customer
                    FOREIGN KEY (master_customer_id)
                    REFERENCES master_customers (id)
                    ON DELETE SET NULL;
                END IF;
            END $$
            """,
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'fk_core_orders_master_customer'
                ) THEN
                    ALTER TABLE core_orders
                    ADD CONSTRAINT fk_core_orders_master_customer
                    FOREIGN KEY (master_customer_id)
                    REFERENCES master_customers (id)
                    ON DELETE SET NULL;
                END IF;
            END $$
            """,
            (
                "CREATE INDEX IF NOT EXISTS ix_core_customers_master_customer_id "
                "ON core_customers (master_customer_id)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS ix_core_orders_master_customer_id "
                "ON core_orders (master_customer_id)"
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

