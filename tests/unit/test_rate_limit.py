"""Unit tests for the Redis sliding-window rate limiter."""

from __future__ import annotations

import uuid

import pytest

from app.core.exceptions import RateLimitError
from app.core.rate_limit import SlidingWindowLimiter


@pytest.mark.asyncio
async def test_rate_limiter_allows_under_limit(redis_client):
    limiter = SlidingWindowLimiter(redis_client)
    for _ in range(3):
        await limiter.hit(key=f"rl:test:{uuid.uuid4().hex}", limit=3, window_seconds=60)


@pytest.mark.asyncio
async def test_rate_limiter_blocks_over_limit(redis_client):
    limiter = SlidingWindowLimiter(redis_client)
    key = f"rl:test:{uuid.uuid4().hex}"
    for _ in range(3):
        await limiter.hit(key=key, limit=3, window_seconds=60)
    with pytest.raises(RateLimitError):
        await limiter.hit(key=key, limit=3, window_seconds=60)


@pytest.mark.asyncio
async def test_rate_limiter_zero_limit_noops(redis_client):
    limiter = SlidingWindowLimiter(redis_client)
    for _ in range(5):
        await limiter.hit(key=f"rl:test:{uuid.uuid4().hex}", limit=0, window_seconds=60)
