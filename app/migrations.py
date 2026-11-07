from collections.abc import Sequence

from sqlalchemy import Connection, text

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
    (
        "20261103_005_add_pancake_page_customers",
        (
            """
            CREATE TABLE IF NOT EXISTS pancake_page_customers (
                page_id VARCHAR(128) NOT NULL,
                page_customer_id VARCHAR(255) NOT NULL,
                source_customer_id VARCHAR(255),
                psid VARCHAR(255),
                global_id VARCHAR(255),
                name TEXT,
                conversation_id VARCHAR(255),
                raw_payload JSONB NOT NULL,
                first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (page_id, page_customer_id)
            )
            """,
            (
                "CREATE INDEX IF NOT EXISTS ix_page_customers_psid "
                "ON pancake_page_customers (page_id, psid)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS ix_page_customers_global_id "
                "ON pancake_page_customers (global_id)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS ix_page_customers_name "
                "ON pancake_page_customers (name)"
            ),
        ),
    ),
    (
        "20261105_006_add_resumable_sync_cursor",
        (
            "ALTER TABLE sync_runs ADD COLUMN IF NOT EXISTS start_page INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE sync_runs ADD COLUMN IF NOT EXISTS page_limit INTEGER NOT NULL DEFAULT 1",
            (
                "CREATE INDEX IF NOT EXISTS ix_sync_runs_shop_started "
                "ON sync_runs (shop_id, started_at)"
            ),
        ),
    ),
    (
        "20261105_007_add_order_filter_indexes",
        (
            (
                "CREATE INDEX IF NOT EXISTS ix_core_orders_carrier_name "
                "ON core_orders (carrier_name)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS ix_core_orders_delivery_status_only "
                "ON core_orders (delivery_status)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS ix_core_orders_inserted_at "
                "ON core_orders (inserted_at)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS ix_core_orders_total_price "
                "ON core_orders (total_price)"
            ),
        ),
    ),
    (
        "20261105_008_materialize_business_status",
        (
            (
                "ALTER TABLE core_orders ADD COLUMN IF NOT EXISTS "
                "business_status VARCHAR(32)"
            ),
            """
            UPDATE core_orders
            SET business_status = CASE
                WHEN status = 6 OR LOWER(COALESCE(status_name, '')) = 'canceled'
                    THEN 'canceled'
                WHEN status IN (4, 5)
                    OR LOWER(COALESCE(status_name, '')) IN ('returning', 'returned')
                    THEN 'returned'
                WHEN status IN (3, 16)
                    OR LOWER(COALESCE(status_name, '')) IN ('delivered', 'received_money')
                    THEN 'delivered'
                WHEN LOWER(COALESCE(delivery_status, '')) = 'canceled'
                    THEN 'canceled'
                WHEN LOWER(COALESCE(delivery_status, '')) IN ('returning', 'returned')
                    THEN 'returned'
                WHEN LOWER(COALESCE(delivery_status, '')) = 'delivered'
                    THEN 'delivered'
                WHEN status IN (2, 9)
                    OR LOWER(COALESCE(status_name, '')) IN ('shipped', 'pending')
                    OR LOWER(COALESCE(delivery_status, '')) IN (
                        'request_received', 'on_the_way', 'out_for_delivery', 'undeliverable'
                    )
                    OR sent_to_carrier_at IS NOT NULL
                    THEN 'in_transit'
                ELSE 'not_sent'
            END
            WHERE business_status IS NULL
            """,
            (
                "ALTER TABLE core_orders ALTER COLUMN business_status "
                "SET DEFAULT 'not_sent'"
            ),
            "ALTER TABLE core_orders ALTER COLUMN business_status SET NOT NULL",
            (
                "CREATE INDEX IF NOT EXISTS ix_core_orders_business_status "
                "ON core_orders (business_status)"
            ),
        ),
    ),
    (
        "20261105_009_add_trigram_search_indexes",
        (
            "CREATE EXTENSION IF NOT EXISTS pg_trgm",
            (
                "CREATE INDEX IF NOT EXISTS ix_core_orders_order_id_trgm "
                "ON core_orders USING gin (source_order_id gin_trgm_ops)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS ix_core_orders_tracking_code_trgm "
                "ON core_orders USING gin (tracking_code gin_trgm_ops)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS ix_core_orders_shipping_name_trgm "
                "ON core_orders USING gin (shipping_name gin_trgm_ops)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS ix_core_orders_shipping_phone_trgm "
                "ON core_orders USING gin (shipping_phone gin_trgm_ops)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS ix_core_orders_shipping_address_trgm "
                "ON core_orders USING gin (shipping_address gin_trgm_ops)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS ix_core_customers_name_trgm "
                "ON core_customers USING gin (name gin_trgm_ops)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS ix_core_customers_phone_trgm "
                "ON core_customers USING gin (normalized_phone gin_trgm_ops)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS ix_core_order_items_product_name_trgm "
                "ON core_order_items USING gin (product_name gin_trgm_ops)"
            ),
        ),
    ),
    (
        "20261105_010_add_order_search_document",
        (
            "ALTER TABLE core_orders ADD COLUMN IF NOT EXISTS search_text TEXT",
            """
            UPDATE core_orders AS orders
            SET search_text = CONCAT_WS(
                ' ',
                orders.source_order_id,
                orders.tracking_code,
                orders.shipping_name,
                orders.shipping_phone,
                orders.shipping_address,
                (
                    SELECT customers.name
                    FROM core_customers AS customers
                    WHERE customers.shop_id = orders.shop_id
                      AND customers.source_customer_id = orders.source_customer_id
                ),
                (
                    SELECT customers.normalized_phone
                    FROM core_customers AS customers
                    WHERE customers.shop_id = orders.shop_id
                      AND customers.source_customer_id = orders.source_customer_id
                ),
                (
                    SELECT STRING_AGG(items.product_name, ' ')
                    FROM core_order_items AS items
                    WHERE items.shop_id = orders.shop_id
                      AND items.source_order_id = orders.source_order_id
                )
            )
            WHERE search_text IS NULL
            """,
            "ALTER TABLE core_orders ALTER COLUMN search_text SET DEFAULT ''",
            "ALTER TABLE core_orders ALTER COLUMN search_text SET NOT NULL",
            (
                "CREATE INDEX IF NOT EXISTS ix_core_orders_search_text_trgm "
                "ON core_orders USING gin (search_text gin_trgm_ops)"
            ),
            "DROP INDEX IF EXISTS ix_core_orders_order_id_trgm",
            "DROP INDEX IF EXISTS ix_core_orders_tracking_code_trgm",
            "DROP INDEX IF EXISTS ix_core_orders_shipping_name_trgm",
            "DROP INDEX IF EXISTS ix_core_orders_shipping_phone_trgm",
            "DROP INDEX IF EXISTS ix_core_orders_shipping_address_trgm",
            "DROP INDEX IF EXISTS ix_core_customers_name_trgm",
            "DROP INDEX IF EXISTS ix_core_customers_phone_trgm",
            "DROP INDEX IF EXISTS ix_core_order_items_product_name_trgm",
        ),
    ),
    (
        "20261105_011_index_recent_orders",
        (
            (
                "CREATE INDEX IF NOT EXISTS ix_core_orders_source_updated_desc "
                "ON core_orders (source_updated_at DESC NULLS LAST)"
            ),
        ),
    ),
    (
        "20261105_012_add_exact_customer_name_search",
        (
            (
                "ALTER TABLE core_orders ADD COLUMN IF NOT EXISTS "
                "customer_name_search TEXT"
            ),
            """
            UPDATE core_orders AS orders
            SET customer_name_search = LOWER(
                REGEXP_REPLACE(
                    BTRIM(
                        COALESCE(
                            (
                                SELECT customers.name
                                FROM core_customers AS customers
                                WHERE customers.shop_id = orders.shop_id
                                  AND customers.source_customer_id = orders.source_customer_id
                            ),
                            orders.shipping_name,
                            ''
                        )
                    ),
                    '\\s+',
                    ' ',
                    'g'
                )
            )
            WHERE customer_name_search IS NULL
            """,
            (
                "ALTER TABLE core_orders ALTER COLUMN customer_name_search "
                "SET DEFAULT ''"
            ),
            "ALTER TABLE core_orders ALTER COLUMN customer_name_search SET NOT NULL",
            (
                "CREATE INDEX IF NOT EXISTS ix_core_orders_customer_name_search "
                "ON core_orders (customer_name_search)"
            ),
        ),
    ),
    (
        "20261105_013_add_customer_group_sort_key",
        (
            (
                "ALTER TABLE core_orders ADD COLUMN IF NOT EXISTS "
                "customer_group_key TEXT"
            ),
            """
            UPDATE core_orders
            SET customer_group_key = COALESCE(
                NULLIF(customer_name_search, ''),
                source_customer_id,
                source_order_id
            )
            WHERE customer_group_key IS NULL
            """,
            """
            UPDATE core_orders AS orders
            SET customer_group_key = customers.normalized_phone
            FROM core_customers AS customers
            WHERE customers.shop_id = orders.shop_id
              AND customers.source_customer_id = orders.source_customer_id
              AND customers.normalized_phone IS NOT NULL
              AND customers.normalized_phone <> ''
            """,
            "ALTER TABLE core_orders ALTER COLUMN customer_group_key SET DEFAULT ''",
            "ALTER TABLE core_orders ALTER COLUMN customer_group_key SET NOT NULL",
            (
                "CREATE INDEX IF NOT EXISTS ix_core_orders_customer_group_updated "
                "ON core_orders (customer_group_key, source_updated_at DESC NULLS LAST)"
            ),
        ),
    ),
    (
        "20261105_014_add_auth_foundation",
        (
            """
            CREATE TABLE IF NOT EXISTS auth_users (
                id VARCHAR(36) PRIMARY KEY,
                username VARCHAR(128) NOT NULL UNIQUE,
                display_name VARCHAR(255) NOT NULL,
                password_hash TEXT NOT NULL,
                role VARCHAR(32) NOT NULL DEFAULT 'staff',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                last_login_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT ck_auth_users_role CHECK (role IN ('admin', 'staff'))
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS auth_user_shop_access (
                user_id VARCHAR(36) NOT NULL,
                shop_id VARCHAR(64) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (user_id, shop_id),
                CONSTRAINT fk_auth_user_shop_access_user
                    FOREIGN KEY (user_id) REFERENCES auth_users (id) ON DELETE CASCADE,
                CONSTRAINT fk_auth_user_shop_access_shop
                    FOREIGN KEY (shop_id) REFERENCES pancake_shops (id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS auth_sessions (
                id VARCHAR(36) PRIMARY KEY,
                token_hash VARCHAR(64) NOT NULL UNIQUE,
                user_id VARCHAR(36) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMPTZ NOT NULL,
                revoked_at TIMESTAMPTZ,
                CONSTRAINT fk_auth_sessions_user
                    FOREIGN KEY (user_id) REFERENCES auth_users (id) ON DELETE CASCADE
            )
            """,
            (
                "CREATE INDEX IF NOT EXISTS ix_auth_sessions_user_expires "
                "ON auth_sessions (user_id, expires_at)"
            ),
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id VARCHAR(36) PRIMARY KEY,
                actor_user_id VARCHAR(36),
                action VARCHAR(128) NOT NULL,
                resource_type VARCHAR(64),
                resource_id VARCHAR(255),
                result VARCHAR(32) NOT NULL DEFAULT 'success',
                metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                ip_address VARCHAR(64),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT fk_audit_logs_actor
                    FOREIGN KEY (actor_user_id) REFERENCES auth_users (id) ON DELETE SET NULL
            )
            """,
            (
                "CREATE INDEX IF NOT EXISTS ix_audit_logs_actor_created "
                "ON audit_logs (actor_user_id, created_at)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS ix_audit_logs_action_created "
                "ON audit_logs (action, created_at)"
            ),
        ),
    ),
    (
        "20261106_015_require_temporary_password_change",
        (
            (
                "ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS "
                "must_change_password BOOLEAN NOT NULL DEFAULT FALSE"
            ),
        ),
    ),
    (
        "20261106_016_add_login_throttling",
        (
            """
            CREATE TABLE IF NOT EXISTS auth_login_throttles (
                key_hash VARCHAR(64) PRIMARY KEY,
                failure_count INTEGER NOT NULL DEFAULT 0,
                window_started_at TIMESTAMPTZ NOT NULL,
                blocked_until TIMESTAMPTZ,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            (
                "CREATE INDEX IF NOT EXISTS ix_auth_login_throttles_updated "
                "ON auth_login_throttles (updated_at)"
            ),
        ),
    ),
    (
        "20261106_017_add_session_csrf_token",
        (
            "ALTER TABLE auth_sessions ADD COLUMN IF NOT EXISTS csrf_token_hash VARCHAR(64)",
            (
                "UPDATE auth_sessions SET csrf_token_hash = repeat('0', 64) "
                "WHERE csrf_token_hash IS NULL"
            ),
            "ALTER TABLE auth_sessions ALTER COLUMN csrf_token_hash SET NOT NULL",
        ),
    ),
    (
        "20261106_018_add_audit_user_agent",
        (
            "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS user_agent VARCHAR(512)",
        ),
    ),
    (
        "20261106_019_add_usage_quotas",
        (
            """
            CREATE TABLE IF NOT EXISTS auth_usage_quotas (
                key_hash VARCHAR(64) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                action VARCHAR(128) NOT NULL,
                window_started_at TIMESTAMPTZ NOT NULL,
                usage_count INTEGER NOT NULL DEFAULT 0,
                last_denied_at TIMESTAMPTZ,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT fk_auth_usage_quotas_user
                    FOREIGN KEY (user_id) REFERENCES auth_users (id) ON DELETE CASCADE
            )
            """,
            (
                "CREATE INDEX IF NOT EXISTS ix_auth_usage_quotas_user_updated "
                "ON auth_usage_quotas (user_id, updated_at)"
            ),
        ),
    ),
    (
        "20261106_020_index_audit_created_at",
        (
            "CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs (created_at)",
        ),
    ),
    (
        "20261108_021_add_staff_soft_delete",
        (
            "ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
            (
                "CREATE INDEX IF NOT EXISTS ix_auth_users_active_staff "
                "ON auth_users (role, deleted_at)"
            ),
        ),
    ),
)


def apply_migrations(connection: Connection) -> None:
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

