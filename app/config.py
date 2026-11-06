from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(
        default="postgresql+psycopg://pancake_app:change_this_password@localhost:5432/pancake_data"
    )
    pancake_api_base_url: str = "https://pos.pages.fm/api/v1"
    pancake_api_key: str = ""
    pancake_shop_ids: str = ""
    pancake_connectors_file: Path = Path("secrets/pancake_connectors.json")
    pancake_pages_connectors_file: Path = Path("secrets/pancake_pages_connectors.json")
    pancake_page_size: int = Field(default=100, ge=1, le=100)
    pancake_start_page: int = Field(default=1, ge=1, le=100_000)
    pancake_max_pages: int = Field(default=1, ge=1, le=100_000)
    pancake_sync_concurrency: int = Field(default=4, ge=1, le=16)
    pancake_resume_backfill: bool = False
    pancake_sync_interval_seconds: int = Field(default=300, ge=30, le=86_400)
    auth_session_hours: int = Field(default=12, ge=1, le=168)
    auth_cookie_secure: bool = False
    auth_login_max_failures: int = Field(default=5, ge=3, le=20)
    auth_login_window_seconds: int = Field(default=900, ge=60, le=86_400)
    auth_login_lock_seconds: int = Field(default=900, ge=60, le=86_400)
    auth_staff_max_sessions: int = Field(default=2, ge=1, le=10)
    staff_order_rows_per_hour: int = Field(default=2_000, ge=100, le=100_000)
    staff_order_details_per_hour: int = Field(default=120, ge=10, le=10_000)
    admin_order_rows_per_hour: int = Field(default=20_000, ge=1_000, le=1_000_000)
    admin_order_details_per_hour: int = Field(default=1_200, ge=100, le=100_000)
    staff_exports_per_hour: int = Field(default=5, ge=1, le=100)
    staff_export_rows_per_day: int = Field(default=2_000, ge=500, le=100_000)
    audit_detail_dedup_seconds: int = Field(default=600, ge=60, le=86_400)
    audit_detail_retention_days: int = Field(default=90, ge=7, le=365)
    audit_general_retention_days: int = Field(default=365, ge=90, le=3_650)
    audit_cleanup_interval_seconds: int = Field(default=86_400, ge=3_600, le=604_800)

    @property
    def shop_allowlist(self) -> set[str]:
        return {part.strip() for part in self.pancake_shop_ids.split(",") if part.strip()}

    def require_pancake_key(self) -> str:
        key = self.pancake_api_key.strip()
        if not key or key == "replace_with_your_key":
            raise RuntimeError("PANCAKE_API_KEY is missing; set it in the local .env file")
        return key


@lru_cache
def get_settings() -> Settings:
    return Settings()

