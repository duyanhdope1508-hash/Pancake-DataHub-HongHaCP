from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_production_deployment_files_exist() -> None:
    for relative_path in (
        ".dockerignore",
        ".env.production.example",
        "compose.production.yaml",
        "scripts/backup-postgres.sh",
        "scripts/install-backup-timer.sh",
        "scripts/restore-postgres.sh",
        "scripts/deploy-production.sh",
    ):
        assert (ROOT / relative_path).is_file()


def test_image_normalizes_source_permissions_for_non_root_runtime() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "chmod -R a=rX /app/app /app/frontend" in dockerfile


def test_production_compose_uses_outbound_only_cloudflare_tunnel() -> None:
    compose = (ROOT / "compose.production.yaml").read_text(encoding="utf-8")
    db_section, api_section = compose.split("  api:", 1)
    api_section, worker_section = api_section.split("  worker:", 1)
    worker_section, tunnel_section = worker_section.split("  cloudflared:", 1)

    assert "ports:" not in db_section
    assert "ports:" not in api_section
    assert "ports:" not in worker_section
    assert "ports:" not in tunnel_section
    assert 'user: "${APP_UID:-1000}:${APP_GID:-1000}"' in api_section
    assert 'user: "${APP_UID:-1000}:${APP_GID:-1000}"' in worker_section
    assert 'AUTH_COOKIE_SECURE: "true"' in api_section
    assert "--proxy-headers" in api_section
    assert "--no-access-log" in api_section
    assert "cloudflare/cloudflared:2026.10.7" in tunnel_section
    assert 'user: "${CLOUDFLARED_UID:-1000}:${CLOUDFLARED_GID:-1000}"' in tunnel_section
    assert "--token-file" in tunnel_section
    assert "/run/secrets/cloudflare_tunnel_token" in tunnel_section


def test_production_secrets_are_not_sent_to_docker_or_git() -> None:
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "secrets" in dockerignore
    assert ".env.production" in gitignore
    assert "backups/" in gitignore
    assert "secrets/cloudflare_tunnel_token" in gitignore


def test_connector_admin_is_manual_and_has_only_required_secret_write_access() -> None:
    compose = (ROOT / "compose.production.yaml").read_text(encoding="utf-8")

    assert "connector-admin:" in compose
    assert 'profiles: ["tools"]' in compose
    assert "./secrets:/app/secrets:rw" in compose
    assert 'command: ["python", "-m", "app.add_connectors"]' in compose
    assert "PANCAKE_CONNECTORS_FILE: /app/secrets/pancake_connectors.json" in compose


def test_restore_requires_explicit_confirmation() -> None:
    restore_script = (ROOT / "scripts/restore-postgres.sh").read_text(encoding="utf-8")

    assert 'RESTORE_CONFIRM:-' in restore_script
    assert '!= "RESTORE"' in restore_script
    assert "--single-transaction" in restore_script


def test_backup_timer_is_daily_persistent_and_runs_as_deploy_user() -> None:
    installer = (ROOT / "scripts/install-backup-timer.sh").read_text(
        encoding="utf-8"
    )

    assert "OnCalendar=*-*-* 02:30:00" in installer
    assert "Persistent=true" in installer
    assert "BACKUP_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}" in installer
    assert "User=$BACKUP_USER" in installer
    assert "ExecStart=$PROJECT_DIR/scripts/backup-postgres.sh" in installer

