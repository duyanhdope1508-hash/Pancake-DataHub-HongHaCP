#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
ENV_FILE=${ENV_FILE:-$PROJECT_DIR/.env.production}
COMPOSE_FILE=${COMPOSE_FILE:-$PROJECT_DIR/compose.production.yaml}
BACKUP_DIR=${BACKUP_DIR:-$PROJECT_DIR/backups}
BACKUP_RETENTION_COUNT=${BACKUP_RETENTION_COUNT:-3}
BACKUP_MIN_FREE_GB=${BACKUP_MIN_FREE_GB:-8}

for value_name in BACKUP_RETENTION_COUNT BACKUP_MIN_FREE_GB; do
  eval "value=\${$value_name}"
  case "$value" in
    ''|*[!0-9]*)
      echo "$value_name must be a positive integer." >&2
      exit 2
      ;;
  esac
  if [ "$value" -lt 1 ]; then
    echo "$value_name must be at least 1." >&2
    exit 2
  fi
done

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing production environment file: $ENV_FILE" >&2
  exit 2
fi

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

send_alert() {
  compose run --rm --no-deps api \
    python -m app.notify_backup "$@" >/dev/null 2>&1 || true
}

umask 077
mkdir -p "$BACKUP_DIR"

exec 9>"$BACKUP_DIR/.backup.lock"
if ! flock -n 9; then
  echo "Another PostgreSQL backup is already running." >&2
  exit 1
fi

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
backup_file="$BACKUP_DIR/pancake-data-hub-$timestamp.dump"
temporary_file="$backup_file.tmp"
failure_reason="Backup stopped before pg_dump completed."
backup_ready=0

cleanup() {
  status=$?
  trap - EXIT
  rm -f -- "$temporary_file"
  if [ "$status" -ne 0 ] && [ "$backup_ready" -ne 1 ]; then
    rm -f -- "$backup_file" "$backup_file.sha256"
  fi
  if [ "$status" -ne 0 ]; then
    disk_free=$(df -hP "$BACKUP_DIR" | awk 'NR == 2 {print $4}')
    send_alert \
      --status failure \
      --detail "$failure_reason" \
      --disk-free "$disk_free"
  fi
  exit "$status"
}
trap cleanup EXIT
trap 'failure_reason="Backup was interrupted."; exit 130' INT TERM

find "$BACKUP_DIR" -maxdepth 1 -type f \
  -name 'pancake-data-hub-*.dump.tmp' -mmin +360 -delete

available_kb=$(df -Pk "$BACKUP_DIR" | awk 'NR == 2 {print $4}')
minimum_kb=$((BACKUP_MIN_FREE_GB * 1024 * 1024))
if [ "$available_kb" -lt "$minimum_kb" ]; then
  failure_reason="Not enough free disk space to start backup (minimum ${BACKUP_MIN_FREE_GB} GB)."
  echo "$failure_reason" >&2
  exit 1
fi

failure_reason="pg_dump failed."
compose exec -T db sh -c \
  'pg_dump --format=custom --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  > "$temporary_file"

if [ ! -s "$temporary_file" ]; then
  failure_reason="PostgreSQL returned an empty backup file."
  echo "Backup failed: PostgreSQL returned an empty file." >&2
  exit 1
fi

failure_reason="The backup archive did not pass pg_restore validation."
compose exec -T db pg_restore --list < "$temporary_file" >/dev/null

failure_reason="Could not finalize or checksum the backup file."
mv -- "$temporary_file" "$backup_file"
sha256sum "$backup_file" > "$backup_file.sha256"
backup_ready=1

find "$BACKUP_DIR" -maxdepth 1 -type f \
  -name 'pancake-data-hub-????????T??????Z.dump' \
  -printf '%T@ %p\n' \
  | sort -nr \
  | awk -v keep="$BACKUP_RETENTION_COUNT" 'NR > keep' \
  | while IFS= read -r obsolete_record; do
      obsolete_file=${obsolete_record#* }
      rm -f -- "$obsolete_file" "$obsolete_file.sha256"
    done

retained_count=$(find "$BACKUP_DIR" -maxdepth 1 -type f \
  -name 'pancake-data-hub-????????T??????Z.dump' | wc -l | tr -d ' ')
backup_size=$(du -h "$backup_file" | awk '{print $1}')
disk_free=$(df -hP "$BACKUP_DIR" | awk 'NR == 2 {print $4}')

send_alert \
  --status success \
  --detail "$(basename "$backup_file")" \
  --backup-size "$backup_size" \
  --disk-free "$disk_free" \
  --retained-count "$retained_count"

echo "Backup created: $backup_file"
echo "Local backups retained: $retained_count/$BACKUP_RETENTION_COUNT"
echo "Disk free after backup: $disk_free"
