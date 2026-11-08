#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this installer with sudo." >&2
  exit 2
fi

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
BACKUP_USER=${BACKUP_USER:-${SUDO_USER:-deploy}}
BACKUP_GROUP=${BACKUP_GROUP:-$BACKUP_USER}
BACKUP_RETENTION_COUNT=${BACKUP_RETENTION_COUNT:-3}
BACKUP_MIN_FREE_GB=${BACKUP_MIN_FREE_GB:-8}
SERVICE_NAME=pancake-data-hub-backup
SERVICE_FILE=/etc/systemd/system/$SERVICE_NAME.service
TIMER_FILE=/etc/systemd/system/$SERVICE_NAME.timer

case "$BACKUP_USER" in
  ''|*[!A-Za-z0-9._-]*)
    echo "BACKUP_USER contains unsupported characters." >&2
    exit 2
    ;;
esac

case "$BACKUP_GROUP" in
  ''|*[!A-Za-z0-9._-]*)
    echo "BACKUP_GROUP contains unsupported characters." >&2
    exit 2
    ;;
esac

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

if ! id "$BACKUP_USER" >/dev/null 2>&1; then
  echo "Backup user does not exist: $BACKUP_USER" >&2
  exit 2
fi

if [ ! -f "$PROJECT_DIR/.env.production" ]; then
  echo "Missing production environment file: $PROJECT_DIR/.env.production" >&2
  exit 2
fi

install -d -m 0700 -o "$BACKUP_USER" -g "$BACKUP_GROUP" "$PROJECT_DIR/backups"

temporary_service=$(mktemp)
temporary_timer=$(mktemp)
cleanup() {
  rm -f -- "$temporary_service" "$temporary_timer"
}
trap cleanup EXIT INT TERM

cat > "$temporary_service" <<EOF
[Unit]
Description=Hồng Hà DataHub PostgreSQL daily backup
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
User=$BACKUP_USER
Group=$BACKUP_GROUP
WorkingDirectory=$PROJECT_DIR
Environment=BACKUP_RETENTION_COUNT=$BACKUP_RETENTION_COUNT
Environment=BACKUP_MIN_FREE_GB=$BACKUP_MIN_FREE_GB
ExecStart=$PROJECT_DIR/scripts/backup-postgres.sh
TimeoutStartSec=3h
Nice=10
IOSchedulingClass=best-effort
IOSchedulingPriority=7
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
EOF

cat > "$temporary_timer" <<EOF
[Unit]
Description=Run Hồng Hà DataHub PostgreSQL backup daily

[Timer]
OnCalendar=*-*-* 02:30:00
Persistent=true
RandomizedDelaySec=10m
Unit=$SERVICE_NAME.service

[Install]
WantedBy=timers.target
EOF

install -m 0644 "$temporary_service" "$SERVICE_FILE"
install -m 0644 "$temporary_timer" "$TIMER_FILE"
systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME.timer"

echo "Daily backup timer installed: $SERVICE_NAME.timer"
systemctl list-timers "$SERVICE_NAME.timer" --no-pager
