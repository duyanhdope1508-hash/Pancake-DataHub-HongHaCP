#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
ENV_FILE=${ENV_FILE:-$PROJECT_DIR/.env.production}
COMPOSE_FILE=${COMPOSE_FILE:-$PROJECT_DIR/compose.production.yaml}

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing production environment file: $ENV_FILE" >&2
  exit 1
fi
if [ ! -f "$COMPOSE_FILE" ]; then
  echo "Missing production Compose file: $COMPOSE_FILE" >&2
  exit 1
fi

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

if ! compose ps --status running --services | grep -qx db; then
  echo "PostgreSQL container is not running." >&2
  exit 1
fi

echo "HONG HA DATAHUB - READ-ONLY STORAGE AUDIT"
echo "No rows or files will be changed. Large-table checks can take a few minutes."

compose exec -T db sh -c \
  'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
\pset pager off
\timing on

BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '180s';
SET LOCAL lock_timeout = '3s';

\echo
\echo '1) Database and largest tables'
SELECT
  current_database() AS database,
  pg_size_pretty(pg_database_size(current_database())) AS database_size;

SELECT
  io.relname AS table_name,
  pg_size_pretty(pg_total_relation_size(io.relid)) AS total_size,
  pg_size_pretty(pg_relation_size(io.relid)) AS table_size,
  pg_size_pretty(pg_indexes_size(io.relid)) AS index_size,
  stats.n_live_tup AS estimated_live_rows,
  stats.n_dead_tup AS estimated_dead_rows
FROM pg_catalog.pg_statio_user_tables AS io
JOIN pg_catalog.pg_stat_user_tables AS stats ON stats.relid = io.relid
ORDER BY pg_total_relation_size(io.relid) DESC
LIMIT 15;

\echo
\echo '2) Raw-to-core transformation coverage'
SELECT
  COUNT(*) AS raw_orders,
  COUNT(c.source_order_id) AS normalized_orders,
  COUNT(*) FILTER (WHERE c.source_order_id IS NULL) AS missing_core_orders,
  COUNT(*) FILTER (
    WHERE c.source_order_id IS NOT NULL
      AND r.ingested_at > c.transformed_at
  ) AS pending_retransform,
  COUNT(*) FILTER (
    WHERE c.source_order_id IS NOT NULL
      AND r.ingested_at <= c.transformed_at
  ) AS safely_transformed
FROM raw_pancake_orders AS r
LEFT JOIN core_orders AS c
  ON c.shop_id = r.shop_id
 AND c.source_order_id = r.source_order_id;

\echo
\echo '3) Raw rows by last-change age (retention candidates are only safely transformed rows)'
SELECT
  CASE
    WHEN r.ingested_at >= now() - interval '30 days' THEN '00-30 days'
    WHEN r.ingested_at >= now() - interval '90 days' THEN '31-90 days'
    WHEN r.ingested_at >= now() - interval '180 days' THEN '91-180 days'
    ELSE 'over 180 days'
  END AS age_bucket,
  COUNT(*) AS raw_orders,
  COUNT(*) FILTER (
    WHERE c.source_order_id IS NOT NULL
      AND r.ingested_at <= c.transformed_at
  ) AS safely_transformed,
  MIN(r.ingested_at) AS oldest_ingested_at,
  MAX(r.ingested_at) AS newest_ingested_at
FROM raw_pancake_orders AS r
LEFT JOIN core_orders AS c
  ON c.shop_id = r.shop_id
 AND c.source_order_id = r.source_order_id
GROUP BY 1
ORDER BY 1;

\echo
\echo '4) Shops with the most raw rows'
SELECT
  r.shop_id,
  COALESCE(s.name, r.shop_id) AS shop_name,
  COUNT(*) AS raw_orders,
  MIN(r.ingested_at) AS oldest_ingested_at,
  MAX(r.ingested_at) AS newest_ingested_at
FROM raw_pancake_orders AS r
LEFT JOIN pancake_shops AS s ON s.id = r.shop_id
GROUP BY r.shop_id, s.name
ORDER BY COUNT(*) DESC
LIMIT 15;

COMMIT;
SQL

echo "Storage audit completed without modifying the database."
