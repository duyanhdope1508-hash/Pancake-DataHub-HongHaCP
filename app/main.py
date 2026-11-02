from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.db import SessionLocal, init_db
from app.order_detail import AmbiguousOrderError, OrderNotFoundError, get_order_detail
from app.order_filters import order_filters
from app.search import search_orders
from app.status import database_status


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


@app.get("/api/orders")
def orders(
    q: str | None = Query(default=None, max_length=100),
    shop_id: str | None = Query(default=None, max_length=64),
    page_id: str | None = Query(default=None, max_length=128),
    status: int | None = Query(default=None),
    page_number: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    with SessionLocal() as session:
        return search_orders(
            session,
            query=q,
            shop_id=shop_id,
            page_id=page_id,
            status=status,
            page_number=page_number,
            page_size=page_size,
        )


@app.get("/api/order-filters")
def filters() -> dict:
    with SessionLocal() as session:
        return order_filters(session)


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

