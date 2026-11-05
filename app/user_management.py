from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models import Shop, User, UserSession, UserShopAccess
from app.security import hash_password, normalize_username


class DuplicateUsernameError(ValueError):
    pass


class StaffNotFoundError(LookupError):
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


def create_staff(
    session: Session,
    *,
    username: str,
    display_name: str,
    password: str,
    shop_ids: list[str],
) -> User:
    normalized_username = normalize_username(username)
    clean_display_name = display_name.strip()
    if not clean_display_name:
        raise ValueError("Tên hiển thị không được để trống.")
    if len(clean_display_name) > 255:
        raise ValueError("Tên hiển thị không được dài quá 255 ký tự.")
    if session.scalar(select(User.id).where(User.username == normalized_username)):
        raise DuplicateUsernameError("Tên đăng nhập đã tồn tại.")

    validated_shop_ids = _validated_shop_ids(session, shop_ids)
    user = User(
        id=str(uuid4()),
        username=normalized_username,
        display_name=clean_display_name,
        password_hash=hash_password(password),
        role="staff",
        is_active=True,
    )
    session.add(user)
    session.add_all(
        UserShopAccess(user_id=user.id, shop_id=shop_id)
        for shop_id in validated_shop_ids
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
    if user is None or user.role != "staff":
        raise StaffNotFoundError(user_id)

    clean_display_name = display_name.strip()
    if not clean_display_name:
        raise ValueError("Tên hiển thị không được để trống.")
    if len(clean_display_name) > 255:
        raise ValueError("Tên hiển thị không được dài quá 255 ký tự.")
    validated_shop_ids = _validated_shop_ids(session, shop_ids)

    password_changed = bool(password)
    if password_changed:
        user.password_hash = hash_password(password or "")
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


def management_snapshot(session: Session) -> dict[str, Any]:
    shops = session.execute(select(Shop.id, Shop.name).order_by(Shop.name, Shop.id)).all()
    users = list(
        session.scalars(
            select(User).where(User.role == "staff").order_by(User.display_name, User.username)
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
        "shops": [
            {"shop_id": shop_id, "shop_name": shop_name or shop_id}
            for shop_id, shop_name in shops
        ],
        "users": [
            {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "is_active": user.is_active,
                "shop_ids": access_by_user[user.id],
                "last_login_at": user.last_login_at,
                "created_at": user.created_at,
            }
            for user in users
        ],
    }
