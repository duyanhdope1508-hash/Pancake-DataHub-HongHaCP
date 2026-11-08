import argparse
import asyncio
import sys

from app.config import get_settings
from app.telegram_alerts import send_telegram_alert

ISSUE_LABELS = {
    "api_unhealthy": "API không phản hồi health check",
    "database_unhealthy": "PostgreSQL không sẵn sàng",
    "worker_stopped": "Worker đồng bộ không chạy",
    "tunnel_stopped": "Cloudflare Tunnel không chạy",
    "sync_stale": "Không có lần đồng bộ thành công gần đây",
    "backup_stale": "Không có backup hợp lệ gần đây",
    "disk_warning": "Dung lượng ổ đĩa đã vượt ngưỡng cảnh báo",
    "disk_critical": "Dung lượng ổ đĩa đã vượt ngưỡng nguy hiểm",
}


def operations_alert_message(
    *,
    status: str,
    issue_codes: list[str],
    disk_usage: str | None = None,
    disk_free: str | None = None,
) -> str:
    if status == "recovered":
        return "✅ HỒNG HÀ DATAHUB\nGiám sát VPS: hệ thống đã phục hồi bình thường."

    lines = ["🚨 HỒNG HÀ DATAHUB", "Giám sát VPS phát hiện sự cố:"]
    for code in issue_codes[:20]:
        lines.append(f"- {ISSUE_LABELS.get(code, code)[:200]}")
    if disk_usage:
        lines.append(f"Ổ đĩa đã dùng: {disk_usage}")
    if disk_free:
        lines.append(f"Ổ đĩa còn trống: {disk_free}")
    lines.append("Hệ thống sẽ tiếp tục kiểm tra tự động mỗi 5 phút.")
    return "\n".join(lines)


async def _notify(args: argparse.Namespace) -> int:
    message = operations_alert_message(
        status=args.status,
        issue_codes=args.issue,
        disk_usage=args.disk_usage,
        disk_free=args.disk_free,
    )
    sent = await send_telegram_alert(get_settings().telegram_alerts_file, message)
    if sent is True:
        print("Operations alert sent to Telegram.")
        return 0
    if sent is None:
        print("Telegram alert configuration is not present; alert skipped.")
        return 0
    print("Could not send the operations alert to Telegram.", file=sys.stderr)
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Gửi cảnh báo vận hành qua Telegram")
    parser.add_argument("--status", choices=("unhealthy", "recovered"), required=True)
    parser.add_argument("--issue", action="append", default=[])
    parser.add_argument("--disk-usage")
    parser.add_argument("--disk-free")
    raise SystemExit(asyncio.run(_notify(parser.parse_args())))


if __name__ == "__main__":
    main()
