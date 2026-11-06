#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
ENV_FILE=${ENV_FILE:-$PROJECT_DIR/.env.production}
COMPOSE_FILE=${COMPOSE_FILE:-$PROJECT_DIR/compose.production.yaml}

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing production environment file: $ENV_FILE" >&2
  echo "Copy .env.production.example to .env.production and fill every required value." >&2
  exit 2
fi

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

cd "$PROJECT_DIR"
compose config --quiet

if compose ps --status running --services 2>/dev/null | grep -qx db; then
  if [ "${SKIP_BACKUP:-0}" != "1" ]; then
    ENV_FILE="$ENV_FILE" COMPOSE_FILE="$COMPOSE_FILE" \
      "$SCRIPT_DIR/backup-postgres.sh"
  fi
fi

compose pull db cloudflared
compose build --pull api
compose up -d --remove-orphans

attempt=0
until compose exec -T api python -c \
  "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()" \
  >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    compose ps
    echo "Deployment started, but the API health check did not pass in time." >&2
    exit 1
  fi
  sleep 2
done

compose ps
echo "Production deployment is healthy."

