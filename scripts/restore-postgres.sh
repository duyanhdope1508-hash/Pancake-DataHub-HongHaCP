#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: RESTORE_CONFIRM=RESTORE $0 /absolute/path/to/backup.dump" >&2
  exit 2
fi

if [ "${RESTORE_CONFIRM:-}" != "RESTORE" ]; then
  echo "Restore replaces the current database." >&2
  echo "Run again with RESTORE_CONFIRM=RESTORE after checking the backup path." >&2
  exit 2
fi

BACKUP_FILE=$1
if [ ! -f "$BACKUP_FILE" ] || [ ! -s "$BACKUP_FILE" ]; then
  echo "Backup file is missing or empty: $BACKUP_FILE" >&2
  exit 2
fi

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
ENV_FILE=${ENV_FILE:-$PROJECT_DIR/.env.production}
COMPOSE_FILE=${COMPOSE_FILE:-$PROJECT_DIR/compose.production.yaml}

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing production environment file: $ENV_FILE" >&2
  exit 2
fi

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

restart_application() {
  compose up -d api worker caddy >/dev/null
}

compose up -d db >/dev/null
attempt=0
until compose exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    echo "PostgreSQL did not become ready in time." >&2
    exit 1
  fi
  sleep 2
done

compose stop api worker >/dev/null 2>&1 || true
trap restart_application EXIT INT TERM

compose exec -T db sh -c \
  'pg_restore --clean --if-exists --no-owner --no-privileges --single-transaction --exit-on-error -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < "$BACKUP_FILE"

trap - EXIT INT TERM
restart_application
echo "Database restored from: $BACKUP_FILE"

