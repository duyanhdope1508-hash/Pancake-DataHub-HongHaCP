from unittest.mock import Mock

import pytest

from app.models import Shop, User, UserShopAccess
from app.security import verify_password
from app.user_management import (
    DuplicateUsernameError,
    UnknownShopError,
    create_staff,
    normalize_shop_ids,
    update_staff,
)


def _staff() -> User:
    return User(
        id="staff-1",
        username="nhan.vien",
        display_name="Nhân viên",
        password_hash="old-hash",
        must_change_password=False,
        role="staff",
        is_active=True,
    )


def test_shop_ids_are_trimmed_and_deduplicated() -> None:
    assert normalize_shop_ids([" shop-1 ", "shop-2", "shop-1", ""]) == (
        "shop-1",
        "shop-2",
    )


def test_create_staff_hashes_password_and_assigns_valid_shops() -> None:
    session = Mock()
    session.scalar.return_value = None
    session.scalars.return_value.all.return_value = ["shop-1", "shop-2"]

    user = create_staff(
        session,
        username="  Nhan.Vien  ",
        display_name="Nhân viên bán hàng",
        password="a secure temporary password",
        shop_ids=["shop-1", "shop-2"],
    )

    assert user.username == "nhan.vien"
    assert user.role == "staff"
    assert user.must_change_password is True
    assert verify_password(user.password_hash, "a secure temporary password") is True
    assignments = list(session.add_all.call_args.args[0])
    assert {(item.user_id, item.shop_id) for item in assignments} == {
        (user.id, "shop-1"),
        (user.id, "shop-2"),
    }


def test_create_staff_rejects_duplicate_username() -> None:
    session = Mock()
    session.scalar.return_value = "existing-user-id"

    with pytest.raises(DuplicateUsernameError):
        create_staff(
            session,
            username="nhan.vien",
            display_name="Nhân viên",
            password="a secure temporary password",
            shop_ids=[],
        )


def test_create_staff_rejects_unknown_shop() -> None:
    session = Mock()
    session.scalar.return_value = None
    session.scalars.return_value.all.return_value = ["shop-1"]

    with pytest.raises(UnknownShopError) as exc_info:
        create_staff(
            session,
            username="nhan.vien",
            display_name="Nhân viên",
            password="a secure temporary password",
            shop_ids=["shop-1", "missing-shop"],
        )

    assert exc_info.value.shop_ids == ["missing-shop"]


def test_update_staff_replaces_access_and_revokes_sessions_after_password_change() -> None:
    session = Mock()
    user = _staff()
    session.get.return_value = user
    session.scalars.return_value.all.return_value = ["shop-2"]

    result = update_staff(
        session,
        user_id=user.id,
        display_name="Nhân viên mới",
        is_active=True,
        shop_ids=["shop-2"],
        password="a new secure password",
    )

    assert result.display_name == "Nhân viên mới"
    assert result.must_change_password is True
    assert verify_password(result.password_hash, "a new secure password") is True
    assignment = next(iter(session.add_all.call_args.args[0]))
    assert isinstance(assignment, UserShopAccess)
    assert assignment.shop_id == "shop-2"
    assert session.execute.call_count == 2


def test_models_used_by_management_are_importable() -> None:
    assert Shop.__tablename__ == "pancake_shops"
    assert UserShopAccess.__tablename__ == "auth_user_shop_access"
