import argparse
import asyncio
import json
import sys

from app.config import get_settings
from app.page_identity_sync import sync_page_identities


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Đồng bộ danh tính khách gần nhất từ Pancake Pages"
    )
    parser.add_argument("--max-conversations", type=int, default=60)
    args = parser.parse_args()
    if not 1 <= args.max_conversations <= 60:
        raise SystemExit("--max-conversations phải nằm trong khoảng 1-60.")

    result = asyncio.run(
        sync_page_identities(
            get_settings(), max_conversations=args.max_conversations
        )
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
