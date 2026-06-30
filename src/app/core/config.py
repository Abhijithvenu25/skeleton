"""Centralised application settings (12-factor env-driven)."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# In local dev, .env.local is the source of truth for non-secret-leaning defaults
# and is read from disk. In any other env we deliberately read no file: production
# must come from real platform-injected environment variables, never from a file
# that might have been baked into the image by mistake.
_LOCAL_ENV_FILE = ".env.local"


def _env_file_for(env: str) -> str | None:
    return _LOCAL_ENV_FILE if env == "local" else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file_for(os.getenv("APP_ENV", "local")),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: Literal["local", "dev", "staging", "prod"] = "local"
    app_name: str = "kalisia-backend"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    cors_allow_origins_raw: str = Field(default="*", alias="cors_allow_origins")

    # PostgreSQL
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"  # noqa: S105
    postgres_db: str = "kalisia"
    postgres_ssl: str | None = None  # e.g. "require" for Neon/Render Postgres

    # Redis
    redis_url: RedisDsn = Field(default="redis://redis:6379/0")  # type: ignore[assignment]

    # JWT
    jwt_secret: str = "change-me"  # noqa: S105
    jwt_algorithm: str = "HS256"
    access_token_ttl_min: int = 15
    refresh_token_ttl_days: int = 7

    # Rate limits
    rate_limit_login_per_min: int = 10
    rate_limit_register_per_min: int = 5

    @field_validator("cors_allow_origins_raw", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return value
        return value

    @property
    def cors_allow_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins_raw.split(",") if o.strip()]

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_connect_args(self) -> dict[str, object]:
        # asyncpg takes SSL as a connect kwarg, not a URL query string.
        if self.postgres_ssl:
            return {"ssl": self.postgres_ssl}
        return {}

    @property
    def database_url_sync(self) -> str:
        # Used by Alembic when it needs a sync driver (we use asyncpg via async wrapper).
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def validate_production(self) -> None:
        """Refuse to start with weak config outside `local`."""
        if self.app_env == "local":
            return
        if self.jwt_secret == "change-me" or len(self.jwt_secret) < 32:  # noqa: S105
            raise RuntimeError(
                "JWT_SECRET must be set to a strong (>=32 char) value outside local env"
            )
        if "*" in self.cors_allow_origins:
            raise RuntimeError("CORS_ALLOW_ORIGINS must not include '*' outside local env")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_production()
    return settings


settings = get_settings()
