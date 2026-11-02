import argparse
import getpass
import secrets
from pathlib import Path


def build_env(api_key: str, database_password: str) -> str:
    return "\n".join(
        [
            "POSTGRES_DB=pancake_data",
            "POSTGRES_USER=pancake_app",
            f"POSTGRES_PASSWORD={database_password}",
            (
                "DATABASE_URL=postgresql+psycopg://"
                f"pancake_app:{database_password}@127.0.0.1:15432/pancake_data"
            ),
            "PANCAKE_API_BASE_URL=https://pos.pages.fm/api/v1",
            f"PANCAKE_API_KEY={api_key}",
            "PANCAKE_SHOP_IDS=",
            "PANCAKE_CONNECTORS_FILE=secrets/pancake_connectors.json",
            "PANCAKE_PAGE_SIZE=100",
            "PANCAKE_MAX_PAGES=1",
            "",
        ]
    )


def write_env(project_root: Path, api_key: str, *, force: bool = False) -> Path:
    env_path = project_root / ".env"
    if env_path.exists() and not force:
        raise FileExistsError(
            ".env already exists. Use --force only if you intend to replace it."
        )

    clean_key = api_key.strip()
    if len(clean_key) < 10 or "\n" in clean_key or "\r" in clean_key:
        raise ValueError("The API key is empty, invalid, or unexpectedly short.")

    database_password = secrets.token_urlsafe(24)
    env_path.write_text(build_env(clean_key, database_password), encoding="utf-8")
    return env_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the local .env file securely")
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing .env file",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    print("Paste or type the Pancake POS API key, then press Enter.")
    print("For security, no characters or asterisks will appear while you enter it.")
    api_key = getpass.getpass("API key (hidden input): ")
    write_env(project_root, api_key, force=args.force)
    print(".env created locally. The file is excluded from Git.")


if __name__ == "__main__":
    main()

