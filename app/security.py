import re
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_PASSWORD_HASHER = PasswordHasher()
_DUMMY_PASSWORD_HASH = _PASSWORD_HASHER.hash("datahub-dummy-password-not-used-by-any-user")
_USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")


def normalize_username(value: str) -> str:
    username = value.strip().lower()
    if not _USERNAME_PATTERN.fullmatch(username):
        raise ValueError(
            "Tên đăng nhập phải dài 3-64 ký tự và chỉ gồm chữ thường, số, dấu chấm, "
            "gạch dưới hoặc gạch ngang."
        )
    return username


def validate_password(password: str) -> None:
    if len(password) < 12:
        raise ValueError("Mật khẩu phải có ít nhất 12 ký tự.")
    if len(password) > 256:
        raise ValueError("Mật khẩu không được dài quá 256 ký tự.")


def hash_password(password: str) -> str:
    validate_password(password)
    return _PASSWORD_HASHER.hash(password)


def generate_temporary_password() -> str:
    """Generate a copy-friendly password that is shown to an admin only once."""
    return secrets.token_urlsafe(18)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _PASSWORD_HASHER.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def verify_password_or_dummy(password_hash: str | None, password: str) -> bool:
    candidate_hash = password_hash or _DUMMY_PASSWORD_HASH
    verified = verify_password(candidate_hash, password)
    return password_hash is not None and verified


def password_needs_rehash(password_hash: str) -> bool:
    try:
        return _PASSWORD_HASHER.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True
