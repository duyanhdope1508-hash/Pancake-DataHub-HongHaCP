import argparse
import getpass
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal, init_db
from app.models import User
from app.security import hash_password, normalize_username


def create_admin(
    session: Session,
    *,
    username: str,
    display_name: str,
    password: str,
) -> User:
    normalized_username = normalize_username(username)
    clean_display_name = display_name.strip()
    if not clean_display_name:
        raise ValueError("Tên hiển thị không được để trống.")

    existing = session.scalar(select(User).where(User.username == normalized_username))
    if existing is not None:
        raise ValueError("Tên đăng nhập đã tồn tại.")

    has_root_admin = bool(
        session.scalar(select(User.id).where(User.is_root_admin.is_(True)))
    )

    user = User(
        username=normalized_username,
        display_name=clean_display_name,
        password_hash=hash_password(password),
        role="admin",
        is_root_admin=not has_root_admin,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Tạo tài khoản quản trị DataHub")
    parser.add_argument("--username", required=True, help="Tên đăng nhập")
    parser.add_argument("--display-name", required=True, help="Tên hiển thị")
    args = parser.parse_args()

    password = getpass.getpass("Mật khẩu admin (ẩn): ")
    confirmation = getpass.getpass("Nhập lại mật khẩu (ẩn): ")
    if password != confirmation:
        raise SystemExit("Hai mật khẩu không khớp.")

    init_db()
    try:
        with SessionLocal() as session:
            user = create_admin(
                session,
                username=args.username,
                display_name=args.display_name,
                password=password,
            )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    account_type = "quản trị gốc" if user.is_root_admin else "quản trị viên"
    print(f"Đã tạo {account_type}: {user.username} ({user.display_name}).")


if __name__ == "__main__":
    main()
