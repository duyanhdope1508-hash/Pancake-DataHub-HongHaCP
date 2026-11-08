#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
ENV_FILE=${ENV_FILE:-$PROJECT_DIR/.env.production}
COMPOSE_FILE=${COMPOSE_FILE:-$PROJECT_DIR/compose.production.yaml}
STATE_DIR=${STATE_DIR:-$PROJECT_DIR/backups}
DISK_WARNING_PERCENT=${DISK_WARNING_PERCENT:-75}
DISK_CRITICAL_PERCENT=${DISK_CRITICAL_PERCENT:-85}
MAX_SYNC_AGE_HOURS=${MAX_SYNC_AGE_HOURS:-15}
MAX_BACKUP_AGE_HOURS=${MAX_BACKUP_AGE_HOURS:-36}

for value_name in DISK_WARNING_PERCENT DISK_CRITICAL_PERCENT MAX_SYNC_AGE_HOURS MAX_BACKUP_AGE_HOURS; do
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

if [ "$DISK_WARNING_PERCENT" -ge "$DISK_CRITICAL_PERCENT" ]; then
  echo "DISK_WARNING_PERCENT must be lower than DISK_CRITICAL_PERCENT." >&2
  exit 2
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing production environment file: $ENV_FILE" >&2
  exit 2
fi

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

send_alert() {
  compose run --rm --no-deps api python -m app.notify_ops "$@" >/dev/null 2>&1
}

umask 077
mkdir -p "$STATE_DIR"
state_file="$STATE_DIR/.ops-monitor-state"
lock_file="$STATE_DIR/.ops-monitor.lock"
exec 9>"$lock_file"
if ! flock -n 9; then
  exit 0
fi

issues=""
add_issue() {
  if [ -z "$issues" ]; then
    issues=$1
  else
    issues="$issues,$1"
  fi
}

running_services=$(compose ps --status running --services 2>/dev/null || true)
has_running_service() {
  printf '%s\n' "$running_services" | grep -qx "$1"
}

if ! has_running_service db || ! compose exec -T db sh -c \
  'pg_isready -q -U "$POSTGRES_USER" -d "$POSTGRES_DB"'; then
  add_issue database_unhealthy
fi

if ! has_running_service api || ! compose exec -T api python -c \
  "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()" \
  >/dev/null 2>&1; then
  add_issue api_unhealthy
fi

if ! has_running_service worker; then
  add_issue worker_stopped
fi

if ! has_running_service cloudflared; then
  add_issue tunnel_stopped
fi

if has_running_service db; then
  sync_fresh=$(compose exec -T db sh -c \
    'psql -At -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
      SELECT CASE WHEN MAX(finished_at) >= NOW() - make_interval(hours => '"$MAX_SYNC_AGE_HOURS"')
                  THEN 1 ELSE 0 END
      FROM sync_runs
      WHERE status = '"'"'success'"'"';
    "' 2>/dev/null || printf '0')
  if [ "$sync_fresh" != "1" ]; then
    add_issue sync_stale
  fi
fi

latest_backup=$(find "$PROJECT_DIR/backups" -maxdepth 1 -type f \
  -name 'pancake-data-hub-????????T??????Z.dump' \
  -mmin "-$((MAX_BACKUP_AGE_HOURS * 60))" -print -quit 2>/dev/null || true)
if [ -z "$latest_backup" ]; then
  add_issue backup_stale
fi

disk_usage_number=$(df -P "$PROJECT_DIR" | awk 'NR == 2 {gsub(/%/, "", $5); print $5}')
disk_usage="${disk_usage_number}%"
disk_free=$(df -hP "$PROJECT_DIR" | awk 'NR == 2 {print $4}')
if [ "$disk_usage_number" -ge "$DISK_CRITICAL_PERCENT" ]; then
  add_issue disk_critical
elif [ "$disk_usage_number" -ge "$DISK_WARNING_PERCENT" ]; then
  add_issue disk_warning
fi

current_state=${issues:-healthy}
previous_state=$(cat "$state_file" 2>/dev/null || printf 'unknown')

if [ "$current_state" = "$previous_state" ]; then
  printf 'Operations monitor unchanged: %s\n' "$current_state"
  exit 0
fi

if [ "$current_state" = "healthy" ]; then
  if [ "$previous_state" != "unknown" ] && [ "$previous_state" != "healthy" ]; then
    if ! send_alert --status recovered; then
      echo "Could not send recovery alert; keeping previous state for retry." >&2
      exit 1
    fi
  fi
else
  set -- --status unhealthy --disk-usage "$disk_usage" --disk-free "$disk_free"
  old_ifs=$IFS
  IFS=,
  for issue in $issues; do
    set -- "$@" --issue "$issue"
  done
  IFS=$old_ifs
  if ! send_alert "$@"; then
    echo "Could not send operations alert; keeping previous state for retry." >&2
    exit 1
  fi
fi

temporary_state="$state_file.tmp"
printf '%s\n' "$current_state" > "$temporary_state"
mv -- "$temporary_state" "$state_file"
printf 'Operations monitor state changed: %s -> %s\n' "$previous_state" "$current_state"
