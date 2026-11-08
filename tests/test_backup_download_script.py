from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_windows_backup_downloader_is_safe_and_verifies_checksum() -> None:
    script = (ROOT / "scripts/download-latest-backup.ps1").read_text(encoding="utf-8")

    assert 'BatchMode=yes' in script
    assert 'ConnectTimeout=15' in script
    assert "Get-FileHash" in script
    assert "SHA256" in script
    assert ".partial" in script
    assert "checksum không đúng" in script
    assert "Select-Object -Skip $Keep" in script
    assert "BitLocker" in script
    assert "password" not in script.lower()


def test_cmd_wrapper_bypasses_local_script_policy_only_for_this_run() -> None:
    wrapper = (ROOT / "scripts/download-latest-backup.cmd").read_text(encoding="utf-8")

    assert "-ExecutionPolicy Bypass" in wrapper
    assert "download-latest-backup.ps1" in wrapper
