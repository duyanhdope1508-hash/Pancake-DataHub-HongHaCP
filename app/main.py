from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from time import monotonic
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from starlette.background import BackgroundTask

from app.audit import list_audit_logs
from app.auth import (
    SESSION_COOKIE_NAME,
    InvalidCurrentPasswordError,
    ReusedPasswordError,
    authenticate_user_session,
    change_user_password,
    create_user_session,
    is_public_path,
    revoke_user_session,
)
from app.authorization import (
    authorized_shop_ids,
    can_view_revenue,
    require_admin,
    scoped_shop_filter,
)
from app.config import get_settings
from app.db import SessionLocal, init_db
from app.models import AuditLog, User
from app.order_detail import AmbiguousOrderError, OrderNotFoundError, get_order_detail
from app.order_export import ExportLimitExceeded, export_orders_xlsx
from app.order_filters import order_filters
from app.search import search_orders, summarize_orders
from app.status import database_status
from app.user_management import (
    DuplicateUsernameError,
    StaffNotFoundError,
    UnknownShopError,
    create_staff,
    management_snapshot,
    update_staff,
)
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


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


class CreateStaffRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=12, max_length=256)
    shop_ids: list[str] = Field(default_factory=list, max_length=100)


class UpdateStaffRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    is_active: bool
    shop_ids: list[str] = Field(default_factory=list, max_length=100)
    password: str | None = Field(default=None, min_length=12, max_length=256)


def _safe_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "must_change_password": user.must_change_password,
        "can_sync": user.role == "admin",
        "can_view_revenue": can_view_revenue(user),
    }


def _add_security_headers(response: Response) -> Response:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
    )
    return response


def _record_audit(
    *,
    actor_user_id: str,
    action: str,
    resource_type: str,
    result: str,
    metadata: dict,
) -> None:
    with SessionLocal() as session:
        session.add(
            AuditLog(
                actor_user_id=actor_user_id,
                action=action,
                resource_type=resource_type,
                result=result,
                metadata_json=metadata,
            )
        )
        session.commit()


@lru_cache(maxsize=128)
def _cached_order_filters(
    time_bucket: int,
    shop_ids: tuple[str, ...] | None,
) -> dict:
    del time_bucket
    with SessionLocal() as session:
        return order_filters(session, shop_ids)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    if request.url.path.startswith("/api/") and not is_public_path(request.url.path):
        raw_token = request.cookies.get(SESSION_COOKIE_NAME)
        with SessionLocal() as session:
            authenticated = authenticate_user_session(session, raw_token)
        if authenticated is None:
            response = JSONResponse(
                status_code=401,
                content={"detail": "Bạn cần đăng nhập để sử dụng DataHub."},
            )
            response.delete_cookie(SESSION_COOKIE_NAME, path="/")
            return _add_security_headers(response)
        request.state.current_user = authenticated.user
        request.state.auth_session_id = authenticated.session.id
        if authenticated.user.must_change_password and request.url.path not in {
            "/api/auth/me",
            "/api/auth/logout",
            "/api/auth/change-password",
        }:
            return _add_security_headers(
                JSONResponse(
                    status_code=403,
                    content={
                        "detail": "Bạn phải đổi mật khẩu tạm thời trước khi tiếp tục.",
                        "code": "password_change_required",
                    },
                )
            )

    response = await call_next(request)
    return _add_security_headers(response)


@app.get("/", include_in_schema=False)
def portal() -> FileResponse:
    return FileResponse(frontend_dir / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    with SessionLocal() as session:
        session.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(payload: LoginRequest, response: Response) -> dict:
    from app.security import (
        normalize_username,
        password_needs_rehash,
        verify_password_or_dummy,
    )

    settings = get_settings()
    try:
        username = normalize_username(payload.username)
    except ValueError:
        username = ""

    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.username == username)) if username else None
        valid_password = verify_password_or_dummy(
            user.password_hash if user is not None else None,
            payload.password,
        )
        if user is None or not user.is_active or not valid_password:
            session.add(
                AuditLog(
                    actor_user_id=user.id if user is not None else None,
                    action="auth.login",
                    result="denied",
                    metadata_json={"username": username},
                )
            )
            session.commit()
            raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không đúng.")

        if password_needs_rehash(user.password_hash):
            from app.security import hash_password

            user.password_hash = hash_password(payload.password)
        user.last_login_at = datetime.now(UTC)
        user_session, raw_token = create_user_session(
            session,
            user_id=user.id,
            session_hours=settings.auth_session_hours,
        )
        session.add(
            AuditLog(
                actor_user_id=user.id,
                action="auth.login",
                resource_type="session",
                resource_id=user_session.id,
                result="success",
                metadata_json={},
            )
        )
        session.commit()

    response.set_cookie(
        SESSION_COOKIE_NAME,
        raw_token,
        max_age=settings.auth_session_hours * 3600,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="strict",
        path="/",
    )
    return {"user": _safe_user(user)}


@app.get("/api/auth/me")
def current_user(request: Request) -> dict:
    return {"user": _safe_user(request.state.current_user)}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response) -> dict[str, str]:
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    with SessionLocal() as session:
        revoke_user_session(session, raw_token)
        session.add(
            AuditLog(
                actor_user_id=request.state.current_user.id,
                action="auth.logout",
                resource_type="session",
                resource_id=request.state.auth_session_id,
                result="success",
                metadata_json={},
            )
        )
        session.commit()
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"status": "logged_out"}


@app.post("/api/auth/change-password")
def change_password(request: Request, payload: ChangePasswordRequest) -> dict[str, str]:
    actor = request.state.current_user
    with SessionLocal() as session:
        try:
            user = change_user_password(
                session,
                user_id=actor.id,
                current_session_id=request.state.auth_session_id,
                current_password=payload.current_password,
                new_password=payload.new_password,
            )
        except (InvalidCurrentPasswordError, ReusedPasswordError) as exc:
            session.rollback()
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        session.add(
            AuditLog(
                actor_user_id=user.id,
                action="auth.password_change",
                resource_type="user",
                resource_id=user.id,
                result="success",
                metadata_json={},
            )
        )
        session.commit()
    return {"status": "password_changed"}


def _staff_error_response(exc: Exception) -> HTTPException:
    if isinstance(exc, DuplicateUsernameError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, UnknownShopError):
        return HTTPException(status_code=422, detail="Có cửa hàng không tồn tại.")
    if isinstance(exc, StaffNotFoundError):
        return HTTPException(status_code=404, detail="Không tìm thấy nhân viên.")
    return HTTPException(status_code=422, detail=str(exc))


@app.get("/api/admin/users")
def admin_users(request: Request) -> dict:
    require_admin(request.state.current_user)
    with SessionLocal() as session:
        return management_snapshot(session)


@app.get("/api/admin/audit-logs")
def admin_audit_logs(
    request: Request,
    page_number: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    action: str | None = Query(default=None, max_length=128),
) -> dict:
    require_admin(request.state.current_user)
    with SessionLocal() as session:
        return list_audit_logs(
            session,
            page_number=page_number,
            page_size=page_size,
            action=action,
        )


@app.post("/api/admin/users", status_code=201)
def admin_create_staff(request: Request, payload: CreateStaffRequest) -> dict:
    actor = request.state.current_user
    require_admin(actor)
    with SessionLocal() as session:
        try:
            user = create_staff(
                session,
                username=payload.username,
                display_name=payload.display_name,
                password=payload.password,
                shop_ids=payload.shop_ids,
            )
        except (DuplicateUsernameError, UnknownShopError, ValueError) as exc:
            session.rollback()
            raise _staff_error_response(exc) from exc
        session.add(
            AuditLog(
                actor_user_id=actor.id,
                action="staff.create",
                resource_type="user",
                resource_id=user.id,
                result="success",
                metadata_json={"shop_count": len(payload.shop_ids)},
            )
        )
        session.commit()
        return {"status": "created", "user_id": user.id}


@app.put("/api/admin/users/{user_id}")
def admin_update_staff(
    request: Request,
    user_id: str,
    payload: UpdateStaffRequest,
) -> dict:
    actor = request.state.current_user
    require_admin(actor)
    with SessionLocal() as session:
        try:
            user = update_staff(
                session,
                user_id=user_id,
                display_name=payload.display_name,
                is_active=payload.is_active,
                shop_ids=payload.shop_ids,
                password=payload.password,
            )
        except (StaffNotFoundError, UnknownShopError, ValueError) as exc:
            session.rollback()
            raise _staff_error_response(exc) from exc
        session.add(
            AuditLog(
                actor_user_id=actor.id,
                action="staff.update",
                resource_type="user",
                resource_id=user.id,
                result="success",
                metadata_json={
                    "active": payload.is_active,
                    "password_changed": bool(payload.password),
                    "shop_count": len(payload.shop_ids),
                },
            )
        )
        session.commit()
        return {"status": "updated", "user_id": user.id}


@app.get("/api/system-status")
def system_status(request: Request) -> dict:
    with SessionLocal() as session:
        shop_ids = authorized_shop_ids(session, request.state.current_user)
    return database_status(shop_ids)


@app.post("/api/sync")
async def sync_now(request: Request) -> dict:
    actor = request.state.current_user
    require_admin(actor)
    result = await run_cycle(get_settings())
    if result["status"] == "skipped":
        _record_audit(
            actor_user_id=actor.id,
            action="orders.sync",
            resource_type="sync",
            result="skipped",
            metadata={"reason": result.get("reason", "unknown")},
        )
        raise HTTPException(
            status_code=409,
            detail="Đang có một lượt đồng bộ khác chạy. Hãy chờ lượt đó hoàn tất.",
        )

    sync_result = result["sync"]
    transform_result = result["transform"]
    _cached_order_filters.cache_clear()
    _record_audit(
        actor_user_id=actor.id,
        action="orders.sync",
        resource_type="sync",
        result="success" if sync_result["success"] else "partial",
        metadata={
            "shops_processed": sync_result["shops_processed"],
            "connectors_failed": sync_result["connectors_failed"],
            "rows_written": sync_result["rows_written"],
            "orders_transformed": transform_result["orders_transformed"],
        },
    )
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
    request: Request,
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
    sort_by: Literal["recent", "customer", "value_desc", "oldest"] = Query(
        default="recent"
    ),
) -> dict:
    with SessionLocal() as session:
        user = request.state.current_user
        allowed_shop_ids = authorized_shop_ids(session, user)
        effective_shop_ids = scoped_shop_filter(shop_id, allowed_shop_ids)
        result = search_orders(
            session,
            query=q,
            shop_id=effective_shop_ids,
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
            sort_by=sort_by,
        )
        if not can_view_revenue(user) and result["summary"] is not None:
            result["summary"].pop("total_revenue", None)
        return result


@app.get("/api/order-filters")
def filters(request: Request) -> dict:
    with SessionLocal() as session:
        shop_ids = authorized_shop_ids(session, request.state.current_user)
    time_bucket = int(monotonic() // ORDER_FILTER_CACHE_SECONDS)
    return _cached_order_filters(time_bucket, shop_ids)


@app.get("/api/orders/summary")
def order_summary(
    request: Request,
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
        user = request.state.current_user
        allowed_shop_ids = authorized_shop_ids(session, user)
        effective_shop_ids = scoped_shop_filter(shop_id, allowed_shop_ids)
        result = summarize_orders(
            session,
            query=q,
            shop_id=effective_shop_ids,
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
        if not can_view_revenue(user):
            result.pop("total_revenue", None)
        return result


@app.get("/api/orders/export")
def export_orders(
    request: Request,
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
        allowed_shop_ids = authorized_shop_ids(session, request.state.current_user)
        effective_shop_ids = scoped_shop_filter(shop_id, allowed_shop_ids)
        try:
            output_path, exported_count = export_orders_xlsx(
                session,
                query=q,
                shop_id=effective_shop_ids,
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
    _record_audit(
        actor_user_id=request.state.current_user.id,
        action="orders.export",
        resource_type="orders",
        result="success",
        metadata={"order_count": exported_count},
    )

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
    request: Request,
    order_id: str,
    shop_id: str | None = Query(default=None, max_length=64),
) -> dict:
    with SessionLocal() as session:
        allowed_shop_ids = authorized_shop_ids(session, request.state.current_user)
        try:
            return get_order_detail(
                session,
                order_id=order_id,
                shop_id=shop_id,
                allowed_shop_ids=(
                    list(allowed_shop_ids) if allowed_shop_ids is not None else None
                ),
            )
        except OrderNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Order not found") from exc
        except AmbiguousOrderError as exc:
            raise HTTPException(
                status_code=409,
                detail="Order ID exists in multiple shops; provide shop_id",
            ) from exc

