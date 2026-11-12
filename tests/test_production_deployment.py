from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_production_deployment_files_exist() -> None:
    for relative_path in (
        ".dockerignore",
        ".env.production.example",
        "compose.production.yaml",
        "scripts/backup-postgres.sh",
        "scripts/install-backup-timer.sh",
        "scripts/monitor-operations.sh",
        "scripts/install-operations-monitor.sh",
        "scripts/analyze-storage.sh",
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


def test_production_database_connections_are_bounded() -> None:
    compose = (ROOT / "compose.production.yaml").read_text(encoding="utf-8")

    assert "DATABASE_POOL_SIZE: ${DATABASE_POOL_SIZE:-6}" in compose
    assert "DATABASE_MAX_OVERFLOW: ${DATABASE_MAX_OVERFLOW:-2}" in compose
    assert "DATABASE_POOL_TIMEOUT_SECONDS: ${DATABASE_POOL_TIMEOUT_SECONDS:-15}" in compose
    assert "DATABASE_POOL_RECYCLE_SECONDS: ${DATABASE_POOL_RECYCLE_SECONDS:-1800}" in compose
    assert "DATABASE_POOL_SIZE: ${WORKER_DATABASE_POOL_SIZE:-3}" in compose
    assert "DATABASE_MAX_OVERFLOW: ${WORKER_DATABASE_MAX_OVERFLOW:-1}" in compose


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


def test_telegram_admin_is_manual_and_writes_only_to_secret_mount() -> None:
    compose = (ROOT / "compose.production.yaml").read_text(encoding="utf-8")
    telegram_section, tunnel_section = compose.split("  telegram-admin:", 1)[1].split(
        "  cloudflared:", 1
    )

    assert 'profiles: ["tools"]' in telegram_section
    assert "./secrets:/app/secrets:rw" in telegram_section
    assert "TELEGRAM_ALERTS_FILE: /app/secrets/telegram_alerts.json" in telegram_section
    assert 'command: ["python", "-m", "app.setup_telegram_alerts"]' in telegram_section
    assert tunnel_section


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
    assert "BACKUP_RETENTION_COUNT=${BACKUP_RETENTION_COUNT:-3}" in installer
    assert "BACKUP_MIN_FREE_GB=${BACKUP_MIN_FREE_GB:-8}" in installer
    assert "User=$BACKUP_USER" in installer
    assert "ExecStart=$PROJECT_DIR/scripts/backup-postgres.sh" in installer
    assert "TimeoutStartSec=3h" in installer
    assert "IOSchedulingPriority=7" in installer


def test_backup_is_space_guarded_locked_and_count_retained() -> None:
    backup_script = (ROOT / "scripts/backup-postgres.sh").read_text(
        encoding="utf-8"
    )

    assert "BACKUP_RETENTION_COUNT=${BACKUP_RETENTION_COUNT:-3}" in backup_script
    assert "BACKUP_MIN_FREE_GB=${BACKUP_MIN_FREE_GB:-8}" in backup_script
    assert "flock -n 9" in backup_script
    assert "available_kb=$(df -Pk" in backup_script
    assert "app.notify_backup" in backup_script
    assert "pg_restore --list" in backup_script
    assert "sha256sum" in backup_script
    assert "NR > keep" in backup_script


def test_operations_monitor_checks_services_capacity_and_freshness() -> None:
    monitor = (ROOT / "scripts/monitor-operations.sh").read_text(encoding="utf-8")
    installer = (ROOT / "scripts/install-operations-monitor.sh").read_text(
        encoding="utf-8"
    )

    for issue in (
        "database_unhealthy",
        "api_unhealthy",
        "worker_stopped",
        "tunnel_stopped",
        "sync_stale",
        "backup_stale",
        "disk_warning",
        "disk_critical",
    ):
        assert issue in monitor
    assert "flock -n 9" in monitor
    assert ".ops-monitor-state" in monitor
    assert "app.notify_ops" in monitor
    assert "OnUnitInactiveSec=5m" in installer
    assert "Persistent=true" in installer
    assert "ExecStart=$PROJECT_DIR/scripts/monitor-operations.sh" in installer


def test_storage_audit_is_read_only_and_bounded() -> None:
    audit = (ROOT / "scripts/analyze-storage.sh").read_text(encoding="utf-8")

    assert "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY" in audit
    assert "statement_timeout = '180s'" in audit
    assert "lock_timeout = '3s'" in audit
    assert "pg_total_relation_size" in audit
    assert "pg_stat_user_tables AS stats" in audit
    assert "stats.relid = io.relid" in audit
    assert "r.ingested_at <= c.transformed_at" in audit
    for destructive_statement in (
        "DELETE FROM",
        "TRUNCATE ",
        "DROP TABLE",
        "VACUUM FULL",
    ):
        assert destructive_statement not in audit.upper()


def test_raw_compaction_is_guarded_and_uses_atomic_shadow_table() -> None:
    runner = (ROOT / "scripts/compact-raw-orders.sh").read_text(encoding="utf-8")
    sql = (ROOT / "scripts/compact-raw-orders.sql").read_text(encoding="utf-8")

    assert 'RAW_COMPACTION_CONFIRM:-' in runner
    assert '!= "COMPACT_RAW"' in runner
    assert "RAW_COMPACTION_MIN_FREE_GB" in runner
    assert 'exec 8>"$PROJECT_DIR/backups/.backup.lock"' in runner
    assert "compose stop --timeout 120 worker" in runner
    assert "trap restart_worker EXIT" in runner
    assert "pg_advisory_lock(1735531090)" in sql
    assert "missing_count <> 0 OR pending_count <> 0" in sql
    assert "raw_pancake_orders_compacting" in sql
    assert "source_count <> compact_count" in sql
    assert "LOCK TABLE raw_pancake_orders IN ACCESS EXCLUSIVE MODE" in sql
    assert "DROP TABLE raw_pancake_orders_pre_compaction" in sql


def test_manual_sync_is_queued_for_worker_instead_of_running_inside_api() -> None:
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    worker_source = (ROOT / "app/worker.py").read_text(encoding="utf-8")

    assert "SyncRequest(requested_by_user_id=actor.id" in main_source
    assert "from app.worker import run_cycle" not in main_source
    assert "asyncio.create_task(_run_manual_sync" not in main_source
    assert "MANUAL_SYNC_POLL_SECONDS = 5" in worker_source
    assert "claim_sync_request()" in worker_source
    assert "recover_interrupted_sync_requests()" in worker_source


def test_large_exports_use_disk_backed_private_storage() -> None:
    compose = (ROOT / "compose.production.yaml").read_text(encoding="utf-8")
    export_source = (ROOT / "app/order_export.py").read_text(encoding="utf-8")

    assert "EXPORT_TEMP_DIR: /app/export-tmp" in compose
    assert "./export-tmp:/app/export-tmp:rw" in compose
    assert '"tmpdir": str(export_dir)' in export_source
    assert "constant_memory" in export_source
    assert "cleanup_export_artifact" in export_source

