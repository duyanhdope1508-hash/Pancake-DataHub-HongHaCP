from app.notify_ops import operations_alert_message


def test_operations_alert_lists_known_issues_and_disk_capacity() -> None:
    message = operations_alert_message(
        status="unhealthy",
        issue_codes=["api_unhealthy", "disk_warning"],
        disk_usage="82%",
        disk_free="10G",
    )

    assert "API không phản hồi" in message
    assert "vượt ngưỡng cảnh báo" in message
    assert "82%" in message
    assert "10G" in message


def test_recovery_alert_is_short_and_does_not_repeat_old_issues() -> None:
    message = operations_alert_message(
        status="recovered",
        issue_codes=["api_unhealthy"],
    )

    assert "đã phục hồi bình thường" in message
    assert "API không phản hồi" not in message
