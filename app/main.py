from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from time import monotonic
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.background import BackgroundTask

from app.config import get_settings
from app.db import SessionLocal, init_db
from app.order_detail import AmbiguousOrderError, OrderNotFoundError, get_order_detail
from app.order_export import ExportLimitExceeded, export_orders_xlsx
from app.order_filters import order_filters
from app.search import search_orders, summarize_orders
from app.status import database_status
from app.worker import run_cycle


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Pancake Data Platform",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

frontend_dir = Path(__file__).resolve().parents[1] / "frontend"
app.mount("/assets", StaticFiles(directory=frontend_dir), name="assets")
ORDER_FILTER_CACHE_SECONDS = 300


@lru_cache(maxsize=2)
def _cached_order_filters(time_bucket: int) -> dict:
    del time_bucket
    with SessionLocal() as session:
        return order_filters(session)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
    )
    return response


@app.get("/", include_in_schema=False)
def portal() -> FileResponse:
    return FileResponse(frontend_dir / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    with SessionLocal() as session:
        session.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/api/system-status")
def system_status() -> dict:
    return database_status()


@app.post("/api/sync")
async def sync_now() -> dict:
    result = await run_cycle(get_settings())
    if result["status"] == "skipped":
        raise HTTPException(
            status_code=409,
            detail="Đang có một lượt đồng bộ khác chạy. Hãy chờ lượt đó hoàn tất.",
        )

    sync_result = result["sync"]
    transform_result = result["transform"]
    _cached_order_filters.cache_clear()
    return {
        "status": "completed" if sync_result["success"] else "completed_with_errors",
        "success": sync_result["success"],
        "shops_processed": sync_result["shops_processed"],
        "connectors_failed": sync_result["connectors_failed"],
        "rows_seen": sync_result["rows_seen"],
        "rows_written": sync_result["rows_written"],
        "orders_transformed": transform_result["orders_transformed"],
    }


@app.get("/api/orders")
def orders(
    q: str | None = Query(default=None, max_length=100),
    shop_id: Annotated[list[str] | None, Query()] = None,
    page_id: Annotated[list[str] | None, Query()] = None,
    status: Annotated[list[int] | None, Query()] = None,
    business_status: Annotated[list[str] | None, Query()] = None,
    carrier_name: Annotated[list[str] | None, Query()] = None,
    delivery_status: Annotated[list[str] | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    min_total: Annotated[Decimal | None, Query(ge=0)] = None,
    max_total: Annotated[Decimal | None, Query(ge=0)] = None,
    has_tracking: Annotated[bool | None, Query()] = None,
    sent_to_carrier: Annotated[bool | None, Query()] = None,
    returned: Annotated[bool | None, Query()] = None,
    product: Annotated[str | None, Query(max_length=200)] = None,
    page_number: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    include_summary: bool = Query(default=True),
) -> dict:
    with SessionLocal() as session:
        return search_orders(
            session,
            query=q,
            shop_id=shop_id,
            page_id=page_id,
            status=status,
            business_status=business_status,
            carrier_name=carrier_name,
            delivery_status=delivery_status,
            date_from=date_from,
            date_to=date_to,
            min_total=min_total,
            max_total=max_total,
            has_tracking=has_tracking,
            sent_to_carrier=sent_to_carrier,
            returned=returned,
            product=product,
            page_number=page_number,
            page_size=page_size,
            include_summary=include_summary,
        )


@app.get("/api/order-filters")
def filters() -> dict:
    time_bucket = int(monotonic() // ORDER_FILTER_CACHE_SECONDS)
    return _cached_order_filters(time_bucket)


@app.get("/api/orders/summary")
def order_summary(
    q: str | None = Query(default=None, max_length=100),
    shop_id: Annotated[list[str] | None, Query()] = None,
    page_id: Annotated[list[str] | None, Query()] = None,
    status: Annotated[list[int] | None, Query()] = None,
    business_status: Annotated[list[str] | None, Query()] = None,
    carrier_name: Annotated[list[str] | None, Query()] = None,
    delivery_status: Annotated[list[str] | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    min_total: Annotated[Decimal | None, Query(ge=0)] = None,
    max_total: Annotated[Decimal | None, Query(ge=0)] = None,
    has_tracking: Annotated[bool | None, Query()] = None,
    sent_to_carrier: Annotated[bool | None, Query()] = None,
    returned: Annotated[bool | None, Query()] = None,
    product: Annotated[str | None, Query(max_length=200)] = None,
) -> dict:
    with SessionLocal() as session:
        return summarize_orders(
            session,
            query=q,
            shop_id=shop_id,
            page_id=page_id,
            status=status,
            business_status=business_status,
            carrier_name=carrier_name,
            delivery_status=delivery_status,
            date_from=date_from,
            date_to=date_to,
            min_total=min_total,
            max_total=max_total,
            has_tracking=has_tracking,
            sent_to_carrier=sent_to_carrier,
            returned=returned,
            product=product,
        )


@app.get("/api/orders/export")
def export_orders(
    q: str | None = Query(default=None, max_length=100),
    shop_id: Annotated[list[str] | None, Query()] = None,
    page_id: Annotated[list[str] | None, Query()] = None,
    status: Annotated[list[int] | None, Query()] = None,
    business_status: Annotated[list[str] | None, Query()] = None,
    carrier_name: Annotated[list[str] | None, Query()] = None,
    delivery_status: Annotated[list[str] | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    min_total: Annotated[Decimal | None, Query(ge=0)] = None,
    max_total: Annotated[Decimal | None, Query(ge=0)] = None,
    has_tracking: Annotated[bool | None, Query()] = None,
    sent_to_carrier: Annotated[bool | None, Query()] = None,
    returned: Annotated[bool | None, Query()] = None,
    product: Annotated[str | None, Query(max_length=200)] = None,
) -> FileResponse:
    with SessionLocal() as session:
        try:
            output_path, _ = export_orders_xlsx(
                session,
                query=q,
                shop_id=shop_id,
                page_id=page_id,
                status=status,
                business_status=business_status,
                carrier_name=carrier_name,
                delivery_status=delivery_status,
                date_from=date_from,
                date_to=date_to,
                min_total=min_total,
                max_total=max_total,
                has_tracking=has_tracking,
                sent_to_carrier=sent_to_carrier,
                returned=returned,
                product=product,
            )
        except ExportLimitExceeded as exc:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Có {exc.total_orders:,} đơn. Hãy thu hẹp bộ lọc còn tối đa "
                    f"{exc.max_orders:,} đơn trước khi xuất Excel."
                ),
            ) from exc

    filename = f"pancake-orders-{datetime.now().strftime('%Y%m%d-%H%M')}.xlsx"
    return FileResponse(
        output_path,
        filename=filename,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        background=BackgroundTask(output_path.unlink, missing_ok=True),
    )


@app.get("/api/orders/{order_id}")
def order_detail(
    order_id: str,
    shop_id: str | None = Query(default=None, max_length=64),
) -> dict:
    with SessionLocal() as session:
        try:
            return get_order_detail(session, order_id=order_id, shop_id=shop_id)
        except OrderNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Order not found") from exc
        except AmbiguousOrderError as exc:
            raise HTTPException(
                status_code=409,
                detail="Order ID exists in multiple shops; provide shop_id",
            ) from exc

