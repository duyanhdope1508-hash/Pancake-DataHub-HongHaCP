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
    pancake_page_size: int = Field(default=100, ge=1, le=100)
    pancake_max_pages: int = Field(default=1, ge=1, le=100_000)

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

