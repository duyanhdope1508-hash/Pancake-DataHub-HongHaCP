from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

from app.auth import (
    authenticate_user_session,
    create_user_session,
    is_public_path,
    revoke_user_session,
)
from app.models import User, UserSession


def test_create_session_stores_only_token_hash() -> None:
    db = Mock()

    user_session, raw_token = create_user_session(db, user_id="user-1", session_hours=12)

    assert raw_token.startswith(f"{user_session.id}.")
    assert raw_token != user_session.token_hash
    assert len(user_session.token_hash) == 64
    assert user_session.expires_at > user_session.created_at
    db.add.assert_called_once_with(user_session)
    db.flush.assert_called_once_with()


def test_authenticate_session_accepts_valid_token_and_rejects_tampering() -> None:
    creating_db = Mock()
    user_session, raw_token = create_user_session(
        creating_db,
        user_id="user-1",
        session_hours=12,
    )
    user = User(
        id="user-1",
        username="admin",
        display_name="Admin",
        password_hash="hash",
        role="admin",
        is_active=True,
    )
    db = Mock()
    db.execute.return_value.one_or_none.return_value = (user_session, user)

    authenticated = authenticate_user_session(db, raw_token)
    tampered = authenticate_user_session(db, f"{user_session.id}.tampered")

    assert authenticated is not None
    assert authenticated.user is user
    assert tampered is None


def test_authenticate_session_rejects_expired_access() -> None:
    now = datetime.now(UTC)
    user_session = UserSession(
        id="session-1",
        token_hash="0" * 64,
        user_id="user-1",
        created_at=now - timedelta(days=1),
        last_seen_at=now - timedelta(days=1),
        expires_at=now - timedelta(seconds=1),
    )
    user = User(
        id="user-1",
        username="staff",
        display_name="Staff",
        password_hash="hash",
        role="staff",
        is_active=True,
    )
    db = Mock()
    db.execute.return_value.one_or_none.return_value = (user_session, user)

    assert authenticate_user_session(db, "session-1.secret") is None


def test_revoke_session_only_accepts_matching_token() -> None:
    creating_db = Mock()
    user_session, raw_token = create_user_session(
        creating_db,
        user_id="user-1",
        session_hours=12,
    )
    db = Mock()
    db.get.return_value = user_session

    revoke_user_session(db, f"{user_session.id}.tampered")
    assert user_session.revoked_at is None
    db.commit.assert_not_called()

    revoke_user_session(db, raw_token)
    assert user_session.revoked_at is not None
    db.commit.assert_called_once_with()


def test_only_login_health_root_and_assets_are_public() -> None:
    assert is_public_path("/") is True
    assert is_public_path("/health") is True
    assert is_public_path("/api/auth/login") is True
    assert is_public_path("/assets/app.js") is True
    assert is_public_path("/api/auth/me") is False
    assert is_public_path("/api/orders") is False
