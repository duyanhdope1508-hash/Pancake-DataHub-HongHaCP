import argparse
import asyncio
import sys

from app.config import get_settings
from app.telegram_alerts import send_telegram_alert


def backup_alert_message(
    *,
    status: str,
    detail: str,
    backup_size: str | None = None,
    disk_free: str | None = None,
    retained_count: int | None = None,
) -> str:
    if status == "success":
        lines = ["✅ HỒNG HÀ DATAHUB", "Backup PostgreSQL đã hoàn thành."]
    else:
        lines = ["🚨 HỒNG HÀ DATAHUB", "Backup PostgreSQL thất bại."]
    if detail:
        lines.append(f"Chi tiết: {detail[:500]}")
    if backup_size:
        lines.append(f"Dung lượng backup: {backup_size}")
    if disk_free:
        lines.append(f"Ổ đĩa còn trống: {disk_free}")
    if retained_count is not None:
        lines.append(f"Số bản local đang giữ: {retained_count}")
    return "\n".join(lines)


async def _notify(args: argparse.Namespace) -> int:
    message = backup_alert_message(
        status=args.status,
        detail=args.detail,
        backup_size=args.backup_size,
        disk_free=args.disk_free,
        retained_count=args.retained_count,
    )
    sent = await send_telegram_alert(get_settings().telegram_alerts_file, message)
    if sent is True:
        print("Backup alert sent to Telegram.")
        return 0
    if sent is None:
        print("Telegram alert configuration is not present; alert skipped.")
        return 0
    print("Could not send the backup alert to Telegram.", file=sys.stderr)
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Gửi trạng thái backup qua Telegram")
    parser.add_argument("--status", choices=("success", "failure"), required=True)
    parser.add_argument("--detail", default="")
    parser.add_argument("--backup-size")
    parser.add_argument("--disk-free")
    parser.add_argument("--retained-count", type=int)
    raise SystemExit(asyncio.run(_notify(parser.parse_args())))


if __name__ == "__main__":
    main()
