#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
ENV_FILE=${ENV_FILE:-$PROJECT_DIR/.env.production}
COMPOSE_FILE=${COMPOSE_FILE:-$PROJECT_DIR/compose.production.yaml}
BACKUP_DIR=${BACKUP_DIR:-$PROJECT_DIR/backups}
BACKUP_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}

case "$BACKUP_RETENTION_DAYS" in
  ''|*[!0-9]*)
    echo "BACKUP_RETENTION_DAYS must be a non-negative integer." >&2
    exit 2
    ;;
esac

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing production environment file: $ENV_FILE" >&2
  exit 2
fi

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

umask 077
mkdir -p "$BACKUP_DIR"
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
backup_file="$BACKUP_DIR/pancake-data-hub-$timestamp.dump"
temporary_file="$backup_file.tmp"

cleanup() {
  rm -f -- "$temporary_file"
}
trap cleanup EXIT INT TERM

compose exec -T db sh -c \
  'pg_dump --format=custom --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  > "$temporary_file"

if [ ! -s "$temporary_file" ]; then
  echo "Backup failed: PostgreSQL returned an empty file." >&2
  exit 1
fi

mv -- "$temporary_file" "$backup_file"
find "$BACKUP_DIR" -type f \
  \( -name 'pancake-data-hub-*.dump' -o -name 'pancake-data-hub-*.dump.sha256' \) \
  -mtime "+$BACKUP_RETENTION_DAYS" -delete

sha256sum "$backup_file" > "$backup_file.sha256"
echo "Backup created: $backup_file"

