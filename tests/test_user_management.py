from unittest.mock import Mock

import pytest

from app.models import Shop, User, UserShopAccess
from app.security import verify_password
from app.user_management import (
    AccountPermissionError,
    DuplicateUsernameError,
    StaffNotFoundError,
    UnknownShopError,
    can_manage_account,
    create_managed_user,
    create_staff,
    delete_staff,
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


def _admin(*, root: bool = False, user_id: str = "admin-1") -> User:
    return User(
        id=user_id,
        username=user_id,
        display_name="Daniel Ng" if root else "Admin thường",
        password_hash="hash",
        must_change_password=False,
        role="admin",
        is_root_admin=root,
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


def test_only_root_admin_can_create_another_admin() -> None:
    session = Mock()

    with pytest.raises(AccountPermissionError):
        create_managed_user(
            session,
            actor=_admin(),
            username="hung.admin",
            display_name="Hùng Phạm",
            password="a secure temporary password",
            role="admin",
            shop_ids=[],
        )

    session.scalar.return_value = None
    created = create_managed_user(
        session,
        actor=_admin(root=True),
        username="hung.admin",
        display_name="Hùng Phạm",
        password="a secure temporary password",
        role="admin",
        shop_ids=["shop-ignored"],
    )

    assert created.role == "admin"
    assert created.is_root_admin is False
    assert list(session.add_all.call_args.args[0]) == []


def test_root_can_manage_regular_admin_but_cannot_manage_itself() -> None:
    root = _admin(root=True, user_id="root-1")
    regular_admin = _admin(user_id="admin-2")
    staff = _staff()

    assert can_manage_account(root, regular_admin) is True
    assert can_manage_account(root, staff) is True
    assert can_manage_account(root, root) is False
    assert can_manage_account(regular_admin, staff) is True
    assert can_manage_account(regular_admin, root) is False
    assert can_manage_account(regular_admin, regular_admin) is False


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


def test_delete_staff_revokes_access_and_sessions_without_losing_audit_identity() -> None:
    session = Mock()
    user = _staff()
    session.get.return_value = user

    result = delete_staff(session, user_id=user.id)

    assert result is user
    assert user.is_active is False
    assert user.deleted_at is not None
    assert session.execute.call_count == 2
    session.flush.assert_called_once()


def test_delete_staff_rejects_admin_accounts() -> None:
    session = Mock()
    admin = _staff()
    admin.role = "admin"
    session.get.return_value = admin

    with pytest.raises(StaffNotFoundError, match="staff-1"):
        delete_staff(session, user_id=admin.id)


def test_update_staff_rejects_deleted_accounts() -> None:
    session = Mock()
    user = _staff()
    user.deleted_at = object()
    session.get.return_value = user

    with pytest.raises(StaffNotFoundError, match="staff-1"):
        update_staff(
            session,
            user_id=user.id,
            display_name="Không được khôi phục",
            is_active=True,
            shop_ids=[],
        )
