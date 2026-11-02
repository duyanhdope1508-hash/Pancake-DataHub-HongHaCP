import argparse
import asyncio
import json

from app.config import get_settings
from app.db import init_db
from app.inspection import inspect_orders
from app.sync import probe, sync_all


async def _run(command: str) -> None:
    settings = get_settings()
    if command == "probe":
        shops = await probe(settings)
        print(json.dumps({"success": True, "shops": shops}, ensure_ascii=False, indent=2))
        return

    if command == "sync":
        init_db()
        result = await sync_all(settings)
        print(json.dumps({"success": True, **result}, ensure_ascii=False, indent=2))
        return

    if command == "inspect-orders":
        result = await inspect_orders(settings)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    raise ValueError(f"Unknown command: {command}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pancake POS ingestion utility")
    parser.add_argument("command", choices=["probe", "inspect-orders", "sync"])
    args = parser.parse_args()
    asyncio.run(_run(args.command))


if __name__ == "__main__":
    main()

