#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this installer with sudo." >&2
  exit 2
fi

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
MONITOR_USER=${MONITOR_USER:-${SUDO_USER:-deploy}}
MONITOR_GROUP=${MONITOR_GROUP:-$MONITOR_USER}
SERVICE_NAME=pancake-data-hub-monitor
SERVICE_FILE=/etc/systemd/system/$SERVICE_NAME.service
TIMER_FILE=/etc/systemd/system/$SERVICE_NAME.timer

case "$MONITOR_USER" in
  ''|*[!A-Za-z0-9._-]*)
    echo "MONITOR_USER contains unsupported characters." >&2
    exit 2
    ;;
esac

case "$MONITOR_GROUP" in
  ''|*[!A-Za-z0-9._-]*)
    echo "MONITOR_GROUP contains unsupported characters." >&2
    exit 2
    ;;
esac

if ! id "$MONITOR_USER" >/dev/null 2>&1; then
  echo "Monitor user does not exist: $MONITOR_USER" >&2
  exit 2
fi

if [ ! -f "$PROJECT_DIR/.env.production" ]; then
  echo "Missing production environment file: $PROJECT_DIR/.env.production" >&2
  exit 2
fi

temporary_service=$(mktemp)
temporary_timer=$(mktemp)
cleanup() {
  rm -f -- "$temporary_service" "$temporary_timer"
}
trap cleanup EXIT INT TERM

cat > "$temporary_service" <<EOF
[Unit]
Description=Hồng Hà DataHub operations monitor
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
User=$MONITOR_USER
Group=$MONITOR_GROUP
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/scripts/monitor-operations.sh
TimeoutStartSec=3m
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
EOF

cat > "$temporary_timer" <<EOF
[Unit]
Description=Check Hồng Hà DataHub operations every five minutes

[Timer]
OnBootSec=3m
OnUnitInactiveSec=5m
AccuracySec=30s
Persistent=true
Unit=$SERVICE_NAME.service

[Install]
WantedBy=timers.target
EOF

install -m 0644 "$temporary_service" "$SERVICE_FILE"
install -m 0644 "$temporary_timer" "$TIMER_FILE"
systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME.timer"

echo "Operations monitor installed: $SERVICE_NAME.timer"
systemctl list-timers "$SERVICE_NAME.timer" --no-pager
