from collections.abc import Sequence

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserShopAccess


def require_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Chỉ quản trị viên mới được thực hiện thao tác này.",
        )


def authorized_shop_ids(session: Session, user: User) -> tuple[str, ...] | None:
    if user.role == "admin":
        return None
    return tuple(
        session.scalars(
            select(UserShopAccess.shop_id)
            .where(UserShopAccess.user_id == user.id)
            .order_by(UserShopAccess.shop_id)
        ).all()
    )


def scoped_shop_filter(
    requested_shop_ids: Sequence[str] | None,
    allowed_shop_ids: tuple[str, ...] | None,
) -> list[str] | None:
    requested = list(dict.fromkeys(requested_shop_ids or []))
    if allowed_shop_ids is None:
        return requested or None
    if not requested:
        return list(allowed_shop_ids)
    allowed = set(allowed_shop_ids)
    return [shop_id for shop_id in requested if shop_id in allowed]


def can_view_revenue(user: User) -> bool:
    return user.role == "admin"
