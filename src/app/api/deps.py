"""FastAPI dependencies: DB session, Redis, current user, rate limiting."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.core.rate_limit import SlidingWindowLimiter
from app.core.security import decode_token
from app.db.redis import get_redis
from app.db.session import get_session
from app.models.user import User

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")


async def db_session() -> AsyncIterator[AsyncSession]:
    async for session in get_session():
        yield session


async def redis_dep() -> Redis:
    return get_redis()


DbSession = Annotated[AsyncSession, Depends(db_session)]
RedisDep = Annotated[Redis, Depends(redis_dep)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: DbSession,
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Missing bearer credentials")

    payload = decode_token(credentials.credentials, expected_type="access")
    sub = payload.get("sub")
    if not sub:
        raise UnauthorizedError("Invalid token subject")

    try:
        user_id = uuid.UUID(sub)
    except ValueError as exc:
        raise UnauthorizedError("Invalid token subject") from exc

    user = await session.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active:
        raise UnauthorizedError("User not active")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def rate_limit(*, key_prefix: str, limit: int) -> Callable[..., Awaitable[None]]:
    """Build a per-IP rate-limit dependency for the given key/limit."""

    async def _check(request: Request, redis: RedisDep) -> None:
        limiter = SlidingWindowLimiter(redis)
        client_ip = request.client.host if request.client else "unknown"
        await limiter.hit(key=f"rl:{key_prefix}:{client_ip}", limit=limit)

    return _check
