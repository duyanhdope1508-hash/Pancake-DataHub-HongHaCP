from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from sqlalchemy import text

from app.db import SessionLocal, init_db
from app.search import search_orders


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


@app.get("/health")
def health() -> dict[str, str]:
    with SessionLocal() as session:
        session.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/api/orders")
def orders(
    q: str | None = Query(default=None, max_length=100),
    page_id: str | None = Query(default=None, max_length=128),
    status: int | None = Query(default=None),
    page_number: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    with SessionLocal() as session:
        return search_orders(
            session,
            query=q,
            page_id=page_id,
            status=status,
            page_number=page_number,
            page_size=page_size,
        )

