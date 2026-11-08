from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models import Shop, User, UserSession, UserShopAccess
from app.security import hash_password, normalize_username

AccountRole = Literal["admin", "staff"]


class DuplicateUsernameError(ValueError):
    pass


class StaffNotFoundError(LookupError):
    pass


class AccountPermissionError(PermissionError):
    pass


class UnknownShopError(ValueError):
    def __init__(self, shop_ids: list[str]):
        self.shop_ids = shop_ids
        super().__init__("Unknown shop IDs: " + ", ".join(shop_ids))


def normalize_shop_ids(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value.strip() for value in values if value.strip()))


def _validated_shop_ids(session: Session, values: list[str]) -> tuple[str, ...]:
    requested = normalize_shop_ids(values)
    if not requested:
        return ()
    existing = set(
        session.scalars(select(Shop.id).where(Shop.id.in_(requested))).all()
    )
    missing = [shop_id for shop_id in requested if shop_id not in existing]
    if missing:
        raise UnknownShopError(missing)
    return requested


def _validated_identity(username: str, display_name: str) -> tuple[str, str]:
    normalized_username = normalize_username(username)
    clean_display_name = display_name.strip()
    if not clean_display_name:
        raise ValueError("Tên hiển thị không được để trống.")
    if len(clean_display_name) > 255:
        raise ValueError("Tên hiển thị không được dài quá 255 ký tự.")
    return normalized_username, clean_display_name


def _create_user(
    session: Session,
    *,
    username: str,
    display_name: str,
    password: str,
    role: AccountRole,
    shop_ids: list[str],
) -> User:
    normalized_username, clean_display_name = _validated_identity(
        username, display_name
    )
    if session.scalar(select(User.id).where(User.username == normalized_username)):
        raise DuplicateUsernameError("Tên đăng nhập đã tồn tại.")

    validated_shop_ids = _validated_shop_ids(session, shop_ids) if role == "staff" else ()
    user = User(
        id=str(uuid4()),
        username=normalized_username,
        display_name=clean_display_name,
        password_hash=hash_password(password),
        must_change_password=True,
        role=role,
        is_root_admin=False,
        is_active=True,
    )
    session.add(user)
    session.add_all(
        UserShopAccess(user_id=user.id, shop_id=shop_id)
        for shop_id in validated_shop_ids
    )
    session.flush()
    return user


def create_staff(
    session: Session,
    *,
    username: str,
    display_name: str,
    password: str,
    shop_ids: list[str],
) -> User:
    return _create_user(
        session,
        username=username,
        display_name=display_name,
        password=password,
        role="staff",
        shop_ids=shop_ids,
    )


def create_managed_user(
    session: Session,
    *,
    actor: User,
    username: str,
    display_name: str,
    password: str,
    role: AccountRole,
    shop_ids: list[str],
) -> User:
    if actor.role != "admin":
        raise AccountPermissionError("Chỉ quản trị viên mới được tạo tài khoản.")
    if role == "admin" and not actor.is_root_admin:
        raise AccountPermissionError(
            "Chỉ quản trị gốc mới được tạo tài khoản quản trị viên."
        )
    return _create_user(
        session,
        username=username,
        display_name=display_name,
        password=password,
        role=role,
        shop_ids=shop_ids,
    )


def can_manage_account(actor: User, target: User) -> bool:
    if target.deleted_at is not None or target.id == actor.id or target.is_root_admin:
        return False
    if actor.role != "admin":
        return False
    if actor.is_root_admin:
        return target.role in {"admin", "staff"}
    return target.role == "staff"


def _update_user(
    session: Session,
    *,
    user: User,
    display_name: str,
    is_active: bool,
    shop_ids: list[str],
    password: str | None = None,
) -> User:
    _unused_username, clean_display_name = _validated_identity(
        user.username, display_name
    )
    validated_shop_ids = (
        _validated_shop_ids(session, shop_ids) if user.role == "staff" else ()
    )

    password_changed = bool(password)
    if password_changed:
        user.password_hash = hash_password(password or "")
        user.must_change_password = True
    user.display_name = clean_display_name
    user.is_active = is_active
    session.execute(
        delete(UserShopAccess).where(UserShopAccess.user_id == user.id)
    )
    session.add_all(
        UserShopAccess(user_id=user.id, shop_id=shop_id)
        for shop_id in validated_shop_ids
    )
    if password_changed or not is_active:
        session.execute(
            update(UserSession)
            .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
    session.flush()
    return user


def update_staff(
    session: Session,
    *,
    user_id: str,
    display_name: str,
    is_active: bool,
    shop_ids: list[str],
    password: str | None = None,
) -> User:
    user = session.get(User, user_id)
    if user is None or user.role != "staff" or user.deleted_at is not None:
        raise StaffNotFoundError(user_id)
    return _update_user(
        session,
        user=user,
        display_name=display_name,
        is_active=is_active,
        shop_ids=shop_ids,
        password=password,
    )


def update_managed_user(
    session: Session,
    *,
    actor: User,
    user_id: str,
    display_name: str,
    is_active: bool,
    shop_ids: list[str],
    password: str | None = None,
) -> User:
    user = session.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise StaffNotFoundError(user_id)
    if not can_manage_account(actor, user):
        raise AccountPermissionError("Bạn không có quyền quản lý tài khoản này.")
    return _update_user(
        session,
        user=user,
        display_name=display_name,
        is_active=is_active,
        shop_ids=shop_ids,
        password=password,
    )


def _delete_user(session: Session, user: User) -> User:
    deleted_at = datetime.now(UTC)
    user.is_active = False
    user.deleted_at = deleted_at
    session.execute(
        delete(UserShopAccess).where(UserShopAccess.user_id == user.id)
    )
    session.execute(
        update(UserSession)
        .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .values(revoked_at=deleted_at)
    )
    session.flush()
    return user


def delete_staff(session: Session, *, user_id: str) -> User:
    user = session.get(User, user_id)
    if user is None or user.role != "staff" or user.deleted_at is not None:
        raise StaffNotFoundError(user_id)
    return _delete_user(session, user)


def delete_managed_user(session: Session, *, actor: User, user_id: str) -> User:
    user = session.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise StaffNotFoundError(user_id)
    if not can_manage_account(actor, user):
        raise AccountPermissionError("Bạn không có quyền xóa tài khoản này.")
    return _delete_user(session, user)


def management_snapshot(session: Session, actor: User | None = None) -> dict[str, Any]:
    shops = session.execute(select(Shop.id, Shop.name).order_by(Shop.name, Shop.id)).all()
    if actor is not None and actor.is_root_admin:
        user_filter = User.role.in_(("admin", "staff"))
    else:
        user_filter = User.role == "staff"
    users = list(
        session.scalars(
            select(User)
            .where(user_filter, User.deleted_at.is_(None))
            .order_by(User.role, User.display_name, User.username)
        ).all()
    )
    user_ids = [user.id for user in users]
    access_rows = (
        session.execute(
            select(UserShopAccess.user_id, UserShopAccess.shop_id).where(
                UserShopAccess.user_id.in_(user_ids)
            )
        ).all()
        if user_ids
        else []
    )
    access_by_user: dict[str, list[str]] = {user_id: [] for user_id in user_ids}
    for user_id, shop_id in access_rows:
        access_by_user[user_id].append(shop_id)

    return {
        "viewer_is_root_admin": bool(actor and actor.is_root_admin),
        "shops": [
            {"shop_id": shop_id, "shop_name": shop_name or shop_id}
            for shop_id, shop_name in shops
        ],
        "users": [
            {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "role": user.role,
                "is_root_admin": bool(user.is_root_admin),
                "can_manage": can_manage_account(actor, user) if actor else True,
                "is_active": user.is_active,
                "must_change_password": user.must_change_password,
                "shop_ids": access_by_user[user.id],
                "last_login_at": user.last_login_at,
                "created_at": user.created_at,
            }
            for user in users
        ],
    }
