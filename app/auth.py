import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import User, UserSession
from app.security import hash_password, verify_password

SESSION_COOKIE_NAME = "hongha_session"


@dataclass(frozen=True)
class AuthenticatedSession:
    user: User
    session: UserSession


class InvalidCurrentPasswordError(ValueError):
    pass


class ReusedPasswordError(ValueError):
    pass


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_user_session(
    db: Session,
    *,
    user_id: str,
    session_hours: int,
) -> tuple[UserSession, str]:
    session_id = str(uuid4())
    raw_token = f"{session_id}.{secrets.token_urlsafe(32)}"
    now = datetime.now(UTC)
    user_session = UserSession(
        id=session_id,
        token_hash=_hash_token(raw_token),
        user_id=user_id,
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(hours=session_hours),
    )
    db.add(user_session)
    db.flush()
    return user_session, raw_token


def authenticate_user_session(
    db: Session,
    raw_token: str | None,
) -> AuthenticatedSession | None:
    if not raw_token or "." not in raw_token or len(raw_token) > 256:
        return None
    session_id, _ = raw_token.split(".", 1)
    result = db.execute(
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(UserSession.id == session_id)
    ).one_or_none()
    if result is None:
        return None

    user_session, user = result
    now = datetime.now(UTC)
    if (
        not user.is_active
        or user_session.revoked_at is not None
        or user_session.expires_at <= now
        or not hmac.compare_digest(user_session.token_hash, _hash_token(raw_token))
    ):
        return None

    if user_session.last_seen_at <= now - timedelta(minutes=5):
        user_session.last_seen_at = now
        db.commit()
    return AuthenticatedSession(user=user, session=user_session)


def revoke_user_session(db: Session, raw_token: str | None) -> None:
    if not raw_token or "." not in raw_token:
        return
    session_id, _ = raw_token.split(".", 1)
    user_session = db.get(UserSession, session_id)
    if user_session is None:
        return
    if hmac.compare_digest(user_session.token_hash, _hash_token(raw_token)):
        user_session.revoked_at = datetime.now(UTC)
        db.commit()


def change_user_password(
    db: Session,
    *,
    user_id: str,
    current_session_id: str,
    current_password: str,
    new_password: str,
) -> User:
    user = db.get(User, user_id)
    if user is None or not user.is_active or not verify_password(
        user.password_hash, current_password
    ):
        raise InvalidCurrentPasswordError("Mật khẩu hiện tại không đúng.")
    if current_password == new_password:
        raise ReusedPasswordError("Mật khẩu mới phải khác mật khẩu hiện tại.")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.execute(
        update(UserSession)
        .where(
            UserSession.user_id == user.id,
            UserSession.id != current_session_id,
            UserSession.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
    db.flush()
    return user


def is_public_path(path: str) -> bool:
    return (
        path == "/"
        or path == "/health"
        or path == "/api/auth/login"
        or path.startswith("/assets/")
    )
