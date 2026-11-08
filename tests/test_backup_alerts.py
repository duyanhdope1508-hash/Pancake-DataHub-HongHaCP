from app.notify_backup import backup_alert_message


def test_successful_backup_alert_contains_capacity_context() -> None:
    message = backup_alert_message(
        status="success",
        detail="pancake-data-hub-20261108T023000Z.dump",
        backup_size="2.7G",
        disk_free="21G",
        retained_count=3,
    )

    assert "Backup PostgreSQL đã hoàn thành" in message
    assert "2.7G" in message
    assert "21G" in message
    assert "3" in message


def test_failed_backup_alert_bounds_untrusted_detail() -> None:
    message = backup_alert_message(
        status="failure",
        detail="x" * 700,
    )

    assert "Backup PostgreSQL thất bại" in message
    assert len(message) < 700
