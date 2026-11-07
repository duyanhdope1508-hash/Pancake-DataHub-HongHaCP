import asyncio
import logging
import secrets
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
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.abuse import QuotaDecision, consume_quota
from app.audit import add_audit_event, list_audit_logs
from app.auth import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    InvalidCurrentPasswordError,
    ReusedPasswordError,
    authenticate_user_session,
    change_user_password,
    clear_login_failures,
    create_user_session,
    enforce_active_session_limit,
    is_public_path,
    login_retry_after,
    record_login_failure,
    revoke_user_session,
    verify_csrf_token,
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
from app.order_export import ExportLimitExceeded, export_limit_for_role, export_orders_xlsx
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

logger = logging.getLogger(__name__)
_manual_sync_task: asyncio.Task[None] | None = None
_manual_sync_state: dict = {"status": "idle"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Pancake Data Platform",
    version="0.1.0",
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=get_settings().trusted_host_list,
)

frontend_dir = Path(__file__).resolve().parents[1] / "frontend"
app.mount("/assets", StaticFiles(directory=frontend_dir), name="assets")
ORDER_FILTER_CACHE_SECONDS = 300
SYSTEM_STATUS_CACHE_SECONDS = 15


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


class CreateStaffRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=255)
    shop_ids: list[str] = Field(default_factory=list, max_length=100)


class UpdateStaffRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    is_active: bool
    shop_ids: list[str] = Field(default_factory=list, max_length=100)
    reset_password: bool = False


class ExportOrderKey(BaseModel):
    shop_id: str = Field(min_length=1, max_length=64)
    order_id: str = Field(min_length=1, max_length=128)


class ExportOrdersRequest(BaseModel):
    selection_mode: Literal["selected", "filtered"]
    orders: list[ExportOrderKey] = Field(default_factory=list, max_length=100_000)
    q: str | None = Field(default=None, max_length=100)
    shop_id: list[str] | None = Field(default=None, max_length=100)
    page_id: list[str] | None = Field(default=None, max_length=100)
    status: list[int] | None = Field(default=None, max_length=100)
    business_status: list[str] | None = Field(default=None, max_length=100)
    carrier_name: list[str] | None = Field(default=None, max_length=100)
    delivery_status: list[str] | None = Field(default=None, max_length=100)
    date_from: datetime | None = None
    date_to: datetime | None = None
    min_total: Decimal | None = Field(default=None, ge=0)
    max_total: Decimal | None = Field(default=None, ge=0)
    has_tracking: bool | None = None
    sent_to_carrier: bool | None = None
    returned: bool | None = None
    product: str | None = Field(default=None, max_length=200)


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


def _add_security_headers(
    response: Response,
    *,
    no_store: bool = False,
    hsts: bool = False,
) -> Response:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "0"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    response.headers["X-Robots-Tag"] = (
        "noindex, nofollow, noarchive, nosnippet, noimageindex"
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    )
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
        "frame-src 'none'; worker-src 'none'; manifest-src 'none'; media-src 'none'; "
        "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    )
    if no_store:
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
    if hsts:
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response


def _record_audit(
    *,
    request: Request,
    actor_user_id: str,
    action: str,
    resource_type: str,
    result: str,
    metadata: dict,
    resource_id: str | None = None,
    deduplicate_seconds: int | None = None,
) -> bool:
    ip_address, user_agent = _audit_client(request)
    with SessionLocal() as session:
        event = add_audit_event(
            session,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent,
            deduplicate_seconds=deduplicate_seconds,
        )
        session.commit()
        return event is not None


def _audit_client(request: Request) -> tuple[str | None, str | None]:
    client = request.client
    ip_address = client.host[:64] if client and client.host else None
    raw_user_agent = request.headers.get("user-agent", "").strip()
    user_agent = raw_user_agent[:512] or None
    return ip_address, user_agent


def _read_quota_policies(
    request: Request,
    user: User,
) -> list[tuple[str, int, int, int]]:
    if request.method != "GET":
        return []
    settings = get_settings()
    path = request.url.path
    if path == "/api/orders":
        try:
            requested_rows = int(request.query_params.get("page_size", "20"))
        except ValueError:
            requested_rows = 20
        amount = min(max(requested_rows, 1), 100)
        limit = (
            settings.admin_order_rows_per_hour
            if user.role == "admin"
            else settings.staff_order_rows_per_hour
        )
        policies = [("orders.list.rows", amount, limit, 3_600)]
        if user.role == "staff":
            policies.insert(
                0,
                (
                    "orders.list.rows.burst",
                    amount,
                    settings.staff_order_rows_per_5_minutes,
                    300,
                ),
            )
        return policies
    if path.startswith("/api/orders/") and path not in {
        "/api/orders/export",
        "/api/orders/summary",
    }:
        limit = (
            settings.admin_order_details_per_hour
            if user.role == "admin"
            else settings.staff_order_details_per_hour
        )
        policies = [("orders.view_detail", 1, limit, 3_600)]
        if user.role == "staff":
            policies.insert(
                0,
                (
                    "orders.view_detail.burst",
                    1,
                    settings.staff_order_details_per_5_minutes,
                    300,
                ),
            )
        return policies
    return []


def _rate_limit_response(decision: QuotaDecision) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "detail": (
                "Bạn đã thao tác quá nhanh hoặc xem quá nhiều dữ liệu. "
                "Hãy thử lại sau."
            ),
            "code": "usage_limit_exceeded",
            "retry_after": decision.retry_after,
        },
        headers={"Retry-After": str(decision.retry_after)},
    )


def _record_quota_denial(
    request: Request,
    *,
    actor: User,
    quota: str,
    decision: QuotaDecision,
) -> None:
    if not decision.should_log_denial:
        return
    _record_audit(
        request=request,
        actor_user_id=actor.id,
        action="security.rate_limit",
        resource_type="api",
        result="denied",
        metadata={
            "quota": quota,
            "used": decision.used,
            "limit": decision.limit,
            "retry_after": decision.retry_after,
        },
    )


def _add_high_usage_alert(
    session,
    request: Request,
    *,
    actor: User,
    quota: str,
    decision: QuotaDecision,
    window_seconds: int,
) -> None:
    ip_address, user_agent = _audit_client(request)
    session.add(
        AuditLog(
            actor_user_id=actor.id,
            action="security.high_usage",
            resource_type="api",
            resource_id=quota,
            result="warning",
            metadata_json={
                "quota": quota,
                "used": decision.used,
                "limit": decision.limit,
                "window_seconds": window_seconds,
                "percent": round(decision.used * 100 / decision.limit),
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
    )


@lru_cache(maxsize=128)
def _cached_order_filters(
    time_bucket: int,
    shop_ids: tuple[str, ...] | None,
) -> dict:
    del time_bucket
    with SessionLocal() as session:
        return order_filters(session, shop_ids)


@lru_cache(maxsize=128)
def _cached_database_status(
    time_bucket: int,
    shop_ids: tuple[str, ...] | None,
) -> dict:
    del time_bucket
    return database_status(shop_ids)


def _should_disable_browser_cache(path: str) -> bool:
    return path == "/" or path.startswith(("/api/", "/assets/"))


@app.middleware("http")
async def security_headers(request: Request, call_next):
    no_store = _should_disable_browser_cache(request.url.path)
    hsts = get_settings().auth_cookie_secure

    def secure(response: Response) -> Response:
        return _add_security_headers(response, no_store=no_store, hsts=hsts)

    if request.url.path.startswith("/api/") and not is_public_path(request.url.path):
        raw_token = request.cookies.get(SESSION_COOKIE_NAME)
        rate_limited_response: JSONResponse | None = None
        with SessionLocal() as session:
            authenticated = authenticate_user_session(session, raw_token)
            if authenticated is not None:
                policies = _read_quota_policies(request, authenticated.user)
                for policy in policies:
                    action, amount, limit, window_seconds = policy
                    decision = consume_quota(
                        session,
                        user_id=authenticated.user.id,
                        action=action,
                        amount=amount,
                        limit=limit,
                        window_seconds=window_seconds,
                    )
                    if decision.should_alert:
                        _add_high_usage_alert(
                            session,
                            request,
                            actor=authenticated.user,
                            quota=action,
                            decision=decision,
                            window_seconds=window_seconds,
                        )
                    if not decision.allowed:
                        if decision.should_log_denial:
                            ip_address, user_agent = _audit_client(request)
                            session.add(
                                AuditLog(
                                    actor_user_id=authenticated.user.id,
                                    action="security.rate_limit",
                                    resource_type="api",
                                    resource_id=request.url.path,
                                    result="denied",
                                    metadata_json={
                                        "quota": action,
                                        "used": decision.used,
                                        "limit": decision.limit,
                                        "retry_after": decision.retry_after,
                                    },
                                    ip_address=ip_address,
                                    user_agent=user_agent,
                                )
                            )
                        rate_limited_response = _rate_limit_response(decision)
                        break
                session.commit()
        if authenticated is None:
            response = JSONResponse(
                status_code=401,
                content={"detail": "Bạn cần đăng nhập để sử dụng DataHub."},
            )
            response.delete_cookie(SESSION_COOKIE_NAME, path="/")
            response.delete_cookie(CSRF_COOKIE_NAME, path="/")
            return secure(response)
        if rate_limited_response is not None:
            return secure(rate_limited_response)
        request.state.current_user = authenticated.user
        request.state.auth_session_id = authenticated.session.id
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not verify_csrf_token(
            authenticated.session,
            request.headers.get("X-CSRF-Token"),
        ):
            return secure(
                JSONResponse(
                    status_code=403,
                    content={
                        "detail": "Phiên bảo mật không hợp lệ. Hãy tải lại trang.",
                        "code": "csrf_failed",
                    },
                )
            )
        if authenticated.user.must_change_password and request.url.path not in {
            "/api/auth/me",
            "/api/auth/logout",
            "/api/auth/change-password",
        }:
            return secure(
                JSONResponse(
                    status_code=403,
                    content={
                        "detail": "Bạn phải đổi mật khẩu tạm thời trước khi tiếp tục.",
                        "code": "password_change_required",
                    },
                )
            )

    response = await call_next(request)
    return secure(response)


@app.get("/", include_in_schema=False)
def portal() -> FileResponse:
    return FileResponse(frontend_dir / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    with SessionLocal() as session:
        session.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(request: Request, payload: LoginRequest, response: Response) -> dict:
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
    throttle_username = username or payload.username.strip().lower()[:128]
    ip_address, user_agent = _audit_client(request)
    throttle_ip = ip_address or "unknown"

    with SessionLocal() as session:
        retry_after = login_retry_after(
            session,
            username=throttle_username,
            ip_address=throttle_ip,
        )
        if retry_after:
            raise HTTPException(
                status_code=429,
                detail="Đăng nhập sai quá nhiều lần. Hãy thử lại sau.",
                headers={"Retry-After": str(retry_after)},
            )
        user = session.scalar(select(User).where(User.username == username)) if username else None
        valid_password = verify_password_or_dummy(
            user.password_hash if user is not None else None,
            payload.password,
        )
        if user is None or not user.is_active or not valid_password:
            record_login_failure(
                session,
                username=throttle_username,
                ip_address=throttle_ip,
                max_failures=settings.auth_login_max_failures,
                window_seconds=settings.auth_login_window_seconds,
                lock_seconds=settings.auth_login_lock_seconds,
            )
            session.add(
                AuditLog(
                    actor_user_id=user.id if user is not None else None,
                    action="auth.login",
                    result="denied",
                    metadata_json={"username": username},
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            )
            session.commit()
            raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không đúng.")

        clear_login_failures(
            session,
            username=throttle_username,
            ip_address=throttle_ip,
        )
        if password_needs_rehash(user.password_hash):
            from app.security import hash_password

            user.password_hash = hash_password(payload.password)
        user.last_login_at = datetime.now(UTC)
        user_session, raw_token, csrf_token = create_user_session(
            session,
            user_id=user.id,
            session_hours=settings.auth_session_hours,
        )
        if user.role == "staff":
            enforce_active_session_limit(
                session,
                user_id=user.id,
                current_session_id=user_session.id,
                max_sessions=settings.auth_staff_max_sessions,
            )
        session.add(
            AuditLog(
                actor_user_id=user.id,
                action="auth.login",
                resource_type="session",
                resource_id=user_session.id,
                result="success",
                metadata_json={},
                ip_address=ip_address,
                user_agent=user_agent,
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
    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf_token,
        max_age=settings.auth_session_hours * 3600,
        httponly=False,
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
    ip_address, user_agent = _audit_client(request)
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
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )
        session.commit()
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")
    return {"status": "logged_out"}


@app.post("/api/auth/change-password")
def change_password(request: Request, payload: ChangePasswordRequest) -> dict[str, str]:
    actor = request.state.current_user
    ip_address, user_agent = _audit_client(request)
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
                ip_address=ip_address,
                user_agent=user_agent,
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
    actor_user_id: str | None = Query(default=None, max_length=36),
    result: str | None = Query(default=None, max_length=32),
    ip_address: str | None = Query(default=None, max_length=64),
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
) -> dict:
    require_admin(request.state.current_user)
    with SessionLocal() as session:
        return list_audit_logs(
            session,
            page_number=page_number,
            page_size=page_size,
            action=action,
            actor_user_id=actor_user_id,
            result=result,
            ip_address=ip_address,
            date_from=date_from,
            date_to=date_to,
        )


@app.post("/api/admin/users", status_code=201)
def admin_create_staff(request: Request, payload: CreateStaffRequest) -> dict:
    actor = request.state.current_user
    require_admin(actor)
    from app.security import generate_temporary_password

    temporary_password = generate_temporary_password()
    ip_address, user_agent = _audit_client(request)
    with SessionLocal() as session:
        try:
            user = create_staff(
                session,
                username=payload.username,
                display_name=payload.display_name,
                password=temporary_password,
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
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )
        session.commit()
        return {
            "status": "created",
            "user_id": user.id,
            "username": user.username,
            "temporary_password": temporary_password,
        }


@app.put("/api/admin/users/{user_id}")
def admin_update_staff(
    request: Request,
    user_id: str,
    payload: UpdateStaffRequest,
) -> dict:
    actor = request.state.current_user
    require_admin(actor)
    from app.security import generate_temporary_password

    temporary_password = generate_temporary_password() if payload.reset_password else None
    ip_address, user_agent = _audit_client(request)
    with SessionLocal() as session:
        try:
            user = update_staff(
                session,
                user_id=user_id,
                display_name=payload.display_name,
                is_active=payload.is_active,
                shop_ids=payload.shop_ids,
                password=temporary_password,
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
                    "password_changed": payload.reset_password,
                    "shop_count": len(payload.shop_ids),
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )
        session.commit()
        return {
            "status": "updated",
            "user_id": user.id,
            "username": user.username,
            "temporary_password": temporary_password,
        }


@app.get("/api/system-status")
def system_status(request: Request) -> dict:
    with SessionLocal() as session:
        shop_ids = authorized_shop_ids(session, request.state.current_user)
    time_bucket = int(monotonic() // SYSTEM_STATUS_CACHE_SECONDS)
    return _cached_database_status(time_bucket, shop_ids)


async def _run_manual_sync(request: Request, actor_user_id: str) -> None:
    global _manual_sync_state
    try:
        result = await run_cycle(get_settings())
        finished_at = datetime.now(UTC).isoformat()
        if result["status"] == "skipped":
            _manual_sync_state = {
                "status": "skipped",
                "reason": result.get("reason", "unknown"),
                "finished_at": finished_at,
            }
            _record_audit(
                request=request,
                actor_user_id=actor_user_id,
                action="orders.sync",
                resource_type="sync",
                result="skipped",
                metadata={"reason": result.get("reason", "unknown")},
            )
            return

        sync_result = result["sync"]
        transform_result = result["transform"]
        _cached_order_filters.cache_clear()
        _cached_database_status.cache_clear()
        _manual_sync_state = {
            "status": "completed",
            "success": sync_result["success"],
            "shops_processed": sync_result["shops_processed"],
            "connectors_failed": sync_result["connectors_failed"],
            "rows_seen": sync_result["rows_seen"],
            "rows_written": sync_result["rows_written"],
            "orders_transformed": transform_result["orders_transformed"],
            "finished_at": finished_at,
        }
        _record_audit(
            request=request,
            actor_user_id=actor_user_id,
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
    except Exception as exc:
        logger.exception("Manual sync failed")
        _manual_sync_state = {
            "status": "failed",
            "detail": "Đồng bộ nền gặp lỗi. Hãy kiểm tra nhật ký hệ thống.",
            "finished_at": datetime.now(UTC).isoformat(),
        }
        _record_audit(
            request=request,
            actor_user_id=actor_user_id,
            action="orders.sync",
            resource_type="sync",
            result="failed",
            metadata={"error_type": type(exc).__name__},
        )


@app.post("/api/sync", status_code=202)
async def sync_now(request: Request) -> dict:
    global _manual_sync_state, _manual_sync_task
    actor = request.state.current_user
    require_admin(actor)
    if _manual_sync_task is not None and not _manual_sync_task.done():
        raise HTTPException(
            status_code=409,
            detail="Đang có một lượt đồng bộ thủ công chạy. Hãy chờ lượt đó hoàn tất.",
        )

    started_at = datetime.now(UTC).isoformat()
    _manual_sync_state = {"status": "running", "started_at": started_at}
    _record_audit(
        request=request,
        actor_user_id=actor.id,
        action="orders.sync",
        resource_type="sync",
        result="started",
        metadata={},
    )
    _manual_sync_task = asyncio.create_task(_run_manual_sync(request, actor.id))
    return {"status": "started", "started_at": started_at}


@app.get("/api/sync/status")
def manual_sync_status(request: Request) -> dict:
    require_admin(request.state.current_user)
    return dict(_manual_sync_state)


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


def _export_orders_response(
    request: Request,
    *,
    filters: dict,
    order_keys: list[tuple[str, str]] | None = None,
    selection_mode: str = "filtered",
) -> FileResponse:
    actor = request.state.current_user
    settings = get_settings()
    export_limit = export_limit_for_role(actor.role)
    trace_id = secrets.token_hex(6).upper()
    ip_address, _user_agent = _audit_client(request)
    with SessionLocal() as session:
        allowed_shop_ids = authorized_shop_ids(session, actor)
        effective_shop_ids = scoped_shop_filter(filters.get("shop_id"), allowed_shop_ids)
        try:
            output_path, exported_count = export_orders_xlsx(
                session,
                query=filters.get("q"),
                shop_id=effective_shop_ids,
                page_id=filters.get("page_id"),
                status=filters.get("status"),
                business_status=filters.get("business_status"),
                carrier_name=filters.get("carrier_name"),
                delivery_status=filters.get("delivery_status"),
                date_from=filters.get("date_from"),
                date_to=filters.get("date_to"),
                min_total=filters.get("min_total"),
                max_total=filters.get("max_total"),
                has_tracking=filters.get("has_tracking"),
                sent_to_carrier=filters.get("sent_to_carrier"),
                returned=filters.get("returned"),
                product=filters.get("product"),
                order_keys=order_keys,
                max_orders=export_limit,
                trace_id=trace_id,
                exported_by=f"@{actor.username}",
                exported_ip=ip_address,
            )
        except ExportLimitExceeded as exc:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Có {exc.total_orders:,} đơn. Hãy thu hẹp bộ lọc còn tối đa "
                    f"{exc.max_orders:,} đơn trước khi xuất Excel."
                ),
            ) from exc
        if actor.role == "staff":
            hourly_decision = consume_quota(
                session,
                user_id=actor.id,
                action="orders.export.requests",
                amount=1,
                limit=settings.staff_exports_per_hour,
                window_seconds=3_600,
            )
            if hourly_decision.should_alert:
                _add_high_usage_alert(
                    session,
                    request,
                    actor=actor,
                    quota="orders.export.requests",
                    decision=hourly_decision,
                    window_seconds=3_600,
                )
            session.commit()
            if not hourly_decision.allowed:
                output_path.unlink(missing_ok=True)
                _record_quota_denial(
                    request,
                    actor=actor,
                    quota="orders.export.requests",
                    decision=hourly_decision,
                )
                raise HTTPException(
                    status_code=429,
                    detail=(
                        "Bạn đã xuất Excel quá nhiều lần trong một giờ. "
                        "Hãy thử lại sau."
                    ),
                    headers={"Retry-After": str(hourly_decision.retry_after)},
                )
            daily_decision = consume_quota(
                session,
                user_id=actor.id,
                action="orders.export.rows",
                amount=max(exported_count, 1),
                limit=settings.staff_export_rows_per_day,
                window_seconds=86_400,
            )
            if daily_decision.should_alert:
                _add_high_usage_alert(
                    session,
                    request,
                    actor=actor,
                    quota="orders.export.rows",
                    decision=daily_decision,
                    window_seconds=86_400,
                )
            session.commit()
            if not daily_decision.allowed:
                output_path.unlink(missing_ok=True)
                _record_quota_denial(
                    request,
                    actor=actor,
                    quota="orders.export.rows",
                    decision=daily_decision,
                )
                raise HTTPException(
                    status_code=429,
                    detail=(
                        "Bạn đã đạt hạn mức số đơn được xuất trong 24 giờ. "
                        "Hãy thử lại sau."
                    ),
                    headers={"Retry-After": str(daily_decision.retry_after)},
                )
    _record_audit(
        request=request,
        actor_user_id=actor.id,
        action="orders.export",
        resource_type="orders",
        result="success",
        metadata={
            "order_count": exported_count,
            "trace_id": trace_id,
            "selection_mode": selection_mode,
        },
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
    return _export_orders_response(
        request,
        filters={
            "q": q,
            "shop_id": shop_id,
            "page_id": page_id,
            "status": status,
            "business_status": business_status,
            "carrier_name": carrier_name,
            "delivery_status": delivery_status,
            "date_from": date_from,
            "date_to": date_to,
            "min_total": min_total,
            "max_total": max_total,
            "has_tracking": has_tracking,
            "sent_to_carrier": sent_to_carrier,
            "returned": returned,
            "product": product,
        },
    )


@app.post("/api/orders/export")
def export_selected_orders(request: Request, payload: ExportOrdersRequest) -> FileResponse:
    order_keys: list[tuple[str, str]] | None = None
    if payload.selection_mode == "selected":
        order_keys = list(dict.fromkeys((item.shop_id, item.order_id) for item in payload.orders))
        if not order_keys:
            raise HTTPException(status_code=422, detail="Hãy chọn ít nhất một đơn để xuất.")
    filters = (
        {}
        if order_keys is not None
        else payload.model_dump(exclude={"selection_mode", "orders"})
    )
    return _export_orders_response(
        request,
        filters=filters,
        order_keys=order_keys,
        selection_mode=payload.selection_mode,
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
            detail = get_order_detail(
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
    _record_audit(
        request=request,
        actor_user_id=request.state.current_user.id,
        action="orders.view_detail",
        resource_type="order",
        resource_id=f"{detail['shop_id']}:{detail['order_id']}",
        result="success",
        metadata={"shop_id": detail["shop_id"]},
        deduplicate_seconds=get_settings().audit_detail_dedup_seconds,
    )
    return detail

