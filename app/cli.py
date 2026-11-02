import argparse
import asyncio
import json
import sys

from app.config import get_settings
from app.db import init_db
from app.inspection import inspect_orders
from app.status import database_status
from app.sync import probe, sync_all
from app.transform import transform_raw_orders


async def _run(command: str) -> None:
    settings = get_settings()
    if command == "probe":
        print(json.dumps(await probe(settings), ensure_ascii=False, indent=2))
        return

    if command == "sync":
        init_db()
        print(json.dumps(await sync_all(settings), ensure_ascii=False, indent=2))
        return

    if command == "inspect-orders":
        result = await inspect_orders(settings)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if command == "status":
        init_db()
        print(json.dumps(database_status(), ensure_ascii=False, indent=2))
        return

    if command == "transform":
        init_db()
        print(json.dumps(transform_raw_orders(), ensure_ascii=False, indent=2))
        return

    raise ValueError(f"Unknown command: {command}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Pancake POS ingestion utility")
    parser.add_argument(
        "command", choices=["probe", "inspect-orders", "status", "sync", "transform"]
    )
    args = parser.parse_args()
    asyncio.run(_run(args.command))


if __name__ == "__main__":
    main()

