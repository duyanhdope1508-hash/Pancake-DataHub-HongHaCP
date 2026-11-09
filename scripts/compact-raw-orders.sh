#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
ENV_FILE=${ENV_FILE:-$PROJECT_DIR/.env.production}
COMPOSE_FILE=${COMPOSE_FILE:-$PROJECT_DIR/compose.production.yaml}
MIN_FREE_GB=${RAW_COMPACTION_MIN_FREE_GB:-8}

if [ "${RAW_COMPACTION_CONFIRM:-}" != "COMPACT_RAW" ]; then
  echo "Refusing to compact without RAW_COMPACTION_CONFIRM=COMPACT_RAW." >&2
  exit 2
fi
if [ ! -f "$ENV_FILE" ]; then
  echo "Missing production environment file: $ENV_FILE" >&2
  exit 2
fi
case "$MIN_FREE_GB" in
  ''|*[!0-9]*) echo "RAW_COMPACTION_MIN_FREE_GB must be an integer." >&2; exit 2 ;;
esac

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

available_kb=$(df -Pk "$PROJECT_DIR" | awk 'NR == 2 {print $4}')
minimum_kb=$((MIN_FREE_GB * 1024 * 1024))
if [ "$available_kb" -lt "$minimum_kb" ]; then
  echo "Not enough free disk space; at least ${MIN_FREE_GB} GB is required." >&2
  exit 1
fi

mkdir -p "$PROJECT_DIR/backups"
exec 9>"$PROJECT_DIR/backups/.raw-compaction.lock"
if ! flock -n 9; then
  echo "Another raw compaction is already running." >&2
  exit 1
fi
exec 8>"$PROJECT_DIR/backups/.backup.lock"
if ! flock -n 8; then
  echo "A PostgreSQL backup is running; retry after it finishes." >&2
  exit 1
fi

worker_was_running=0
if compose ps --status running --services | grep -qx worker; then
  worker_was_running=1
fi

restart_worker() {
  status=$?
  trap - EXIT INT TERM
  if [ "$worker_was_running" -eq 1 ]; then
    compose up -d worker >/dev/null
  fi
  exit "$status"
}
trap restart_worker EXIT
trap 'exit 130' INT TERM

echo "Stopping the sync worker during raw compaction..."
compose stop --timeout 120 worker

echo "Applying the lightweight fingerprint schema migration..."
compose run --rm --no-deps api python -c 'from app.db import init_db; init_db()'

echo "Building and atomically swapping the compact raw table..."
compose exec -T db sh -c \
  'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < "$SCRIPT_DIR/compact-raw-orders.sql"

echo "Raw compaction finished; the worker will now be restarted."
