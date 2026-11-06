from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy import CheckConstraint

from app.create_admin import create_admin
from app.models import AuditLog, LoginThrottle, User, UserSession, UserShopAccess
from app.security import (
    generate_temporary_password,
    hash_password,
    normalize_username,
    verify_password,
    verify_password_or_dummy,
)


def test_auth_models_have_required_security_fields() -> None:
    assert {
        "id",
        "username",
        "display_name",
        "password_hash",
        "must_change_password",
        "role",
        "is_active",
        "last_login_at",
    }.issubset(User.__table__.columns.keys())
    assert {"user_id", "shop_id"}.issubset(UserShopAccess.__table__.columns.keys())
    assert {
        "id",
        "token_hash",
        "csrf_token_hash",
        "user_id",
        "expires_at",
        "revoked_at",
    }.issubset(
        UserSession.__table__.columns.keys()
    )
    assert {
        "actor_user_id",
        "action",
        "result",
        "metadata_json",
        "ip_address",
        "user_agent",
    }.issubset(
        AuditLog.__table__.columns.keys()
    )
    assert {"key_hash", "failure_count", "blocked_until", "updated_at"}.issubset(
        LoginThrottle.__table__.columns.keys()
    )


def test_user_role_is_constrained() -> None:
    constraints = {
        constraint.name
        for constraint in User.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_auth_users_role" in constraints


def test_password_is_hashed_with_argon2id_and_verifies() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert password_hash.startswith("$argon2id$")
    assert "correct horse" not in password_hash
    assert verify_password(password_hash, "correct horse battery staple") is True
    assert verify_password(password_hash, "wrong password") is False
    assert verify_password("not-a-password-hash", "wrong password") is False
    assert verify_password_or_dummy(None, "wrong password") is False


def test_temporary_passwords_are_strong_and_unique() -> None:
    first = generate_temporary_password()
    second = generate_temporary_password()

    assert len(first) >= 20
    assert first != second
    assert " " not in first


def test_username_is_normalized_and_validated() -> None:
    assert normalize_username("  Daniel.NG  ") == "daniel.ng"
    with pytest.raises(ValueError):
        normalize_username("a")
    with pytest.raises(ValueError):
        normalize_username("admin @")


def test_create_admin_never_keeps_plaintext_password() -> None:
    session = Mock()
    session.scalar.return_value = None
    session.refresh.side_effect = lambda user: setattr(user, "id", "user-1")

    user = create_admin(
        session,
        username="Admin.Main",
        display_name="Daniel Ng",
        password="a secure admin password",
    )

    assert user.username == "admin.main"
    assert user.role == "admin"
    assert user.password_hash != "a secure admin password"
    assert "a secure admin password" not in repr(user)
    session.add.assert_called_once_with(user)
    session.commit.assert_called_once_with()


def test_create_admin_rejects_duplicate_username() -> None:
    session = Mock()
    session.scalar.return_value = User(
        username="admin",
        display_name="Existing",
        password_hash="hash",
        role="admin",
    )

    with pytest.raises(ValueError, match="đã tồn tại"):
        create_admin(
            session,
            username="ADMIN",
            display_name="Daniel Ng",
            password="a secure admin password",
        )

    session.add.assert_not_called()
    session.commit.assert_not_called()


def test_migration_adds_temporary_password_flag_safely() -> None:
    source = Path("app/migrations.py").read_text(encoding="utf-8")

    assert "20261106_015_require_temporary_password_change" in source
    assert "must_change_password BOOLEAN NOT NULL DEFAULT FALSE" in source
    assert "20261106_016_add_login_throttling" in source
    assert "20261106_017_add_session_csrf_token" in source
    assert "20261106_018_add_audit_user_agent" in source
