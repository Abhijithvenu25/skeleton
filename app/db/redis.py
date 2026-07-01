"""Async Redis client factory."""

from __future__ import annotations

from redis.asyncio import Redis, from_url

from app.core.config import settings
from app.core.logging import get_logger

_client: Redis | None = None
logger = get_logger(__name__)


def get_redis() -> Redis:
    global _client
    if _client is None:
        _client = from_url(
            str(settings.redis_url),
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
        )
    return _client


async def ping_redis() -> None:
    """Fail-fast startup ping: refuse to boot if Redis is unreachable.

    With REDIS_URL now required in non-local envs (see
    `Settings.validate_production`), an unreachable Redis at startup
    means the operator pasted a wrong URL — better to fail loud at
    boot than to 503 on the first /auth/register call.

    Soft-fail behaviour (warn instead of raise) was kept temporarily
    while Upstash was being provisioned; that's no longer the case
    since REDIS_URL is now mandatory and validated by the time we
    reach this function.
    """
    client = get_redis()
    try:
        await client.ping()
        logger.info("redis_ok", url=str(settings.redis_url))
    except Exception as exc:
        logger.error(
            "redis_unreachable",
            url=str(settings.redis_url),
            error=str(exc),
            hint=(
                "REDIS_URL is set but the host is unreachable. "
                "Check the URL, network, and provider status. "
                "If you intentionally need a soft-fail (e.g. during a "
                "managed-Redis migration), see the comment block in this file."
            ),
        )
        raise


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
