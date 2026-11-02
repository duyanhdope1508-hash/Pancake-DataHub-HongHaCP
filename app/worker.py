import asyncio
import json
import logging
from typing import Any

from app.config import Settings, get_settings
from app.db import init_db
from app.sync import sync_all
from app.transform import transform_raw_orders

logger = logging.getLogger(__name__)


async def run_cycle(settings: Settings) -> dict[str, Any]:
    sync_result = await sync_all(settings)
    transform_result = transform_raw_orders()
    return {"sync": sync_result, "transform": transform_result}


async def run_forever(settings: Settings) -> None:
    init_db()
    logger.info(
        "Pancake sync worker started with interval=%s seconds",
        settings.pancake_sync_interval_seconds,
    )
    while True:
        try:
            result = await run_cycle(settings)
            logger.info("Sync cycle completed: %s", json.dumps(result, default=str))
        except Exception:
            logger.exception("Sync cycle failed")
        await asyncio.sleep(settings.pancake_sync_interval_seconds)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # Pancake authenticates through a query parameter. httpx's INFO request log
    # includes the complete URL, so keep it disabled to prevent credential leaks.
    logging.getLogger("httpx").setLevel(logging.WARNING)


def main() -> None:
    configure_logging()
    asyncio.run(run_forever(get_settings()))


if __name__ == "__main__":
    main()
