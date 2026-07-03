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
    # Default is intentionally localhost (not the docker-compose service hostname
    # "redis") so a misconfigured prod deploy that forgets to set REDIS_URL
    # fails with a clear "connection refused" rather than silently trying the
    # docker-internal hostname that only resolves inside compose networks.
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")  # type: ignore[assignment]

    # S3 Object Storage (AWS S3)
    s3_endpoint_url: str | None = None
    s3_region: str
    s3_bucket: str
    s3_access_key_id: str
    s3_secret_access_key: str
    s3_public_base_url: str | None = None
    s3_presigned_ttl_seconds: int = 3600

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

    @property
    def s3_max_upload_bytes(self) -> int:
        """Hard cap on upload size enforced by the /uploads endpoint (50 MiB)."""
        return 50 * 1024 * 1024

    def validate_production(self) -> None:
        """Refuse to start with weak config outside `local`.

        Failure-mode policy:
        - JWT_SECRET / CORS_ALLOW_ORIGINS: hard fail (security-critical).
        - REDIS_URL *missing or empty*: hard fail (silent failure — every
          /auth/* would 503 forever, and the operator wouldn't see it
          because the app boots and healthz returns 200).
        - REDIS_URL *set to docker-internal hostname*: WARNING, not fail
          (intentional dev state — Upstash is being provisioned). The
          app will boot, /auth/* will 503, but the rest of the API
          works for non-auth smoke tests. Once the operator pastes a
          real URL (Upstash, Render, AWS, Oracle) the warning stops.
        - REDIS_URL *set to a real URL*: we don't validate the URL here;
          the startup `ping_redis()` confirms reachability.
        """
        if self.app_env == "local":
            return
        if self.jwt_secret == "change-me" or len(self.jwt_secret) < 32:  # noqa: S105
            raise RuntimeError(
                "JWT_SECRET must be set to a strong (>=32 char) value outside local env"
            )
        if "*" in self.cors_allow_origins:
            raise RuntimeError("CORS_ALLOW_ORIGINS must not include '*' outside local env")
        # REDIS_URL must be present in prod. Without it the app would boot
        # fine, healthz would return 200, but every /auth/* would 503
        # silently. Hard-fail here surfaces the misconfig at deploy time
        # instead of at the first user's login attempt.
        if not str(self.redis_url).strip():
            raise RuntimeError(
                "REDIS_URL is required in non-local envs. "
                "Set it in your hosting provider's environment "
                "(e.g. rediss://default:<password>@<host>.upstash.io:6379)."
            )
        # Dev-state: warn loudly if the URL is the docker-compose hostname
        # (this only resolves inside the local compose network). Once
        # REDIS_URL is replaced with a real provider URL, the warning
        # stops firing automatically.
        if "redis://redis:" in str(self.redis_url) or "rediss://redis:" in str(self.redis_url):
            import structlog
            structlog.get_logger(__name__).warning(
                "redis_url_looks_docker_internal",
                redis_url=str(self.redis_url),
                hint=(
                    "REDIS_URL points at the docker-compose 'redis' hostname. "
                    "On Render this won't resolve. Auth routes will return 503 "
                    "until this is replaced with a managed Redis URL. "
                    "Set REDIS_URL in Render's environment to fix."
                ),
            )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_production()
    return settings


settings = get_settings()
