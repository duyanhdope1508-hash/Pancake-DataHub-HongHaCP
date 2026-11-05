from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.authorization import (
    authorized_shop_ids,
    can_view_revenue,
    require_admin,
    scoped_shop_filter,
)
from app.models import User


def _user(role: str) -> User:
    return User(
        id=f"{role}-1",
        username=role,
        display_name=role.title(),
        password_hash="hash",
        role=role,
        is_active=True,
    )


def test_admin_has_unrestricted_shop_scope_and_revenue_access() -> None:
    admin = _user("admin")

    assert authorized_shop_ids(Mock(), admin) is None
    assert scoped_shop_filter(None, None) is None
    assert scoped_shop_filter(["shop-2"], None) == ["shop-2"]
    assert can_view_revenue(admin) is True
    require_admin(admin)


def test_staff_scope_intersects_requested_shops() -> None:
    staff = _user("staff")
    db = Mock()
    db.scalars.return_value.all.return_value = ["shop-1", "shop-2"]

    allowed = authorized_shop_ids(db, staff)

    assert allowed == ("shop-1", "shop-2")
    assert scoped_shop_filter(None, allowed) == ["shop-1", "shop-2"]
    assert scoped_shop_filter(["shop-2", "shop-secret"], allowed) == ["shop-2"]
    assert can_view_revenue(staff) is False


def test_staff_cannot_use_admin_action() -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_admin(_user("staff"))

    assert exc_info.value.status_code == 403


def test_staff_without_shop_assignments_gets_empty_scope() -> None:
    db = Mock()
    db.scalars.return_value.all.return_value = []

    allowed = authorized_shop_ids(db, _user("staff"))

    assert allowed == ()
    assert scoped_shop_filter(None, allowed) == []
