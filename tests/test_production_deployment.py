from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_production_deployment_files_exist() -> None:
    for relative_path in (
        ".dockerignore",
        ".env.production.example",
        "compose.production.yaml",
        "scripts/backup-postgres.sh",
        "scripts/restore-postgres.sh",
        "scripts/deploy-production.sh",
    ):
        assert (ROOT / relative_path).is_file()


def test_production_compose_uses_outbound_only_cloudflare_tunnel() -> None:
    compose = (ROOT / "compose.production.yaml").read_text(encoding="utf-8")
    db_section, api_section = compose.split("  api:", 1)
    api_section, worker_section = api_section.split("  worker:", 1)
    worker_section, tunnel_section = worker_section.split("  cloudflared:", 1)

    assert "ports:" not in db_section
    assert "ports:" not in api_section
    assert "ports:" not in worker_section
    assert "ports:" not in tunnel_section
    assert 'AUTH_COOKIE_SECURE: "true"' in api_section
    assert "--proxy-headers" in api_section
    assert "--no-access-log" in api_section
    assert "cloudflare/cloudflared:2026.10.7" in tunnel_section
    assert "--token-file" in tunnel_section
    assert "/run/secrets/cloudflare_tunnel_token" in tunnel_section


def test_production_secrets_are_not_sent_to_docker_or_git() -> None:
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "secrets" in dockerignore
    assert ".env.production" in gitignore
    assert "backups/" in gitignore
    assert "secrets/cloudflare_tunnel_token" in gitignore


def test_restore_requires_explicit_confirmation() -> None:
    restore_script = (ROOT / "scripts/restore-postgres.sh").read_text(encoding="utf-8")

    assert 'RESTORE_CONFIRM:-' in restore_script
    assert '!= "RESTORE"' in restore_script
    assert "--single-transaction" in restore_script

