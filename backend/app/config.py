from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Ӟечбур"
    app_env: str = "development"
    app_secret: str = Field(default="development-secret-change-me-32-chars", min_length=32)
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://udmurt:udmurt@localhost:5432/udmurt"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:8000,http://localhost:5173"
    dictionary_path: Path = Path("udmurt_dictionary_full.json")
    auto_migrate: bool = False
    auto_import_dictionary: bool = False
    access_token_days: int = 180

    telegram_bot_token: str = ""
    telegram_bot_secret: str = "development-bot-secret"  # noqa: S105
    telegram_webapp_url: str = "http://localhost:8000"
    api_internal_url: str = "http://localhost:8000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
