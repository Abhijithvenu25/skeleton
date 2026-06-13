"""Sliding-window rate limiter backed by Redis."""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

from redis.exceptions import RedisError

from app.core.exceptions import RateLimitError
from app.core.logging import get_logger

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = get_logger(__name__)


class SlidingWindowLimiter:
    """Atomic per-key sliding window using a Redis sorted set."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def hit(self, *, key: str, limit: int, window_seconds: int = 60) -> None:
        if limit <= 0:
            return
        now_ms = int(time.time() * 1000)
        window_start = now_ms - window_seconds * 1000
        member = f"{now_ms}-{uuid.uuid4().hex}"

        try:
            pipe = self._redis.pipeline(transaction=True)
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {member: now_ms})
            pipe.zcard(key)
            pipe.expire(key, window_seconds + 1)
            results = await pipe.execute()
            count = int(results[2])
        except RedisError as exc:
            # Fail-open: never block traffic on a rate-limiter outage.
            logger.warning("rate_limit_redis_error", error=str(exc))
            return

        if count > limit:
            retry_after = max(1, window_seconds)
            raise RateLimitError(
                "Too many requests",
                details={"retry_after_seconds": retry_after},
            )
