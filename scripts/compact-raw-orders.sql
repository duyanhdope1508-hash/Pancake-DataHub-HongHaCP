\set ON_ERROR_STOP on
\pset pager off
\timing on

SET statement_timeout = 0;
SET lock_timeout = '30s';

SELECT pg_advisory_lock(1735531090);

\echo '1) Verifying exact raw-to-core coverage'
DO $$
DECLARE
    raw_count BIGINT;
    missing_count BIGINT;
    pending_count BIGINT;
    unusable_count BIGINT;
BEGIN
    SELECT
        COUNT(*),
        COUNT(*) FILTER (WHERE c.source_order_id IS NULL),
        COUNT(*) FILTER (
            WHERE c.source_order_id IS NOT NULL
              AND r.ingested_at > c.transformed_at
        ),
        COUNT(*) FILTER (
            WHERE r.payload IS NULL AND r.payload_hash IS NULL
        )
    INTO raw_count, missing_count, pending_count, unusable_count
    FROM raw_pancake_orders AS r
    LEFT JOIN core_orders AS c
      ON c.shop_id = r.shop_id
     AND c.source_order_id = r.source_order_id;

    RAISE NOTICE 'raw=%, missing_core=%, pending_retransform=%, unusable=%',
        raw_count, missing_count, pending_count, unusable_count;
    IF raw_count = 0 THEN
        RAISE EXCEPTION 'Raw table is empty; refusing to compact.';
    END IF;
    IF missing_count <> 0 OR pending_count <> 0 OR unusable_count <> 0 THEN
        RAISE EXCEPTION 'Coverage guard failed; no table was replaced.';
    END IF;
END
$$;

\echo '2) Building compact fingerprint table (the long-running read-only phase)'
DROP TABLE IF EXISTS raw_pancake_orders_compacting;
CREATE TABLE raw_pancake_orders_compacting (
    shop_id VARCHAR(64) NOT NULL,
    source_order_id VARCHAR(128) NOT NULL,
    payload JSONB,
    payload_hash VARCHAR(32) NOT NULL,
    source_updated_at VARCHAR(64),
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    compacted_at TIMESTAMPTZ
);

INSERT INTO raw_pancake_orders_compacting (
    shop_id,
    source_order_id,
    payload,
    payload_hash,
    source_updated_at,
    ingested_at,
    compacted_at
)
SELECT
    r.shop_id,
    r.source_order_id,
    NULL,
    COALESCE(r.payload_hash, MD5(r.payload::TEXT)),
    r.source_updated_at,
    r.ingested_at,
    COALESCE(r.compacted_at, NOW())
FROM raw_pancake_orders AS r;

ALTER TABLE raw_pancake_orders_compacting
    ADD CONSTRAINT raw_pancake_orders_compacting_pkey
    PRIMARY KEY (shop_id, source_order_id);
ALTER TABLE raw_pancake_orders_compacting
    ADD CONSTRAINT raw_pancake_orders_compacting_shop_fkey
    FOREIGN KEY (shop_id) REFERENCES pancake_shops(id);
ANALYZE raw_pancake_orders_compacting;

\echo '3) Atomically replacing the payload table after count verification'
DO $$
DECLARE
    source_count BIGINT;
    compact_count BIGINT;
BEGIN
    SELECT COUNT(*) INTO source_count FROM raw_pancake_orders;
    SELECT COUNT(*) INTO compact_count FROM raw_pancake_orders_compacting;
    IF source_count <> compact_count THEN
        RAISE EXCEPTION 'Row count mismatch: source=%, compact=%',
            source_count, compact_count;
    END IF;
    RAISE NOTICE 'Verified % fingerprint rows.', compact_count;
END
$$;

BEGIN;
LOCK TABLE raw_pancake_orders IN ACCESS EXCLUSIVE MODE;
ALTER TABLE raw_pancake_orders RENAME TO raw_pancake_orders_pre_compaction;
ALTER TABLE raw_pancake_orders_compacting RENAME TO raw_pancake_orders;
DROP TABLE raw_pancake_orders_pre_compaction;
COMMIT;

ANALYZE raw_pancake_orders;

\echo '4) Final compacted table size'
SELECT
    COUNT(*) AS fingerprint_rows,
    COUNT(payload) AS retained_payloads,
    PG_SIZE_PRETTY(PG_TOTAL_RELATION_SIZE('raw_pancake_orders')) AS total_size
FROM raw_pancake_orders;

SELECT pg_advisory_unlock(1735531090);
\echo 'Raw payload compaction completed.'
