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
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.storage.service import StorageService

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")


async def db_session() -> AsyncIterator[AsyncSession]:
    async for session in get_session():
        yield session


async def redis_dep() -> Redis:
    return get_redis()


def get_storage_service() -> StorageService:
    """Factory for the StorageService — used by routes that need upload/delete.

    The service is stateless; constructing per-request is cheap (aioboto3
    clients are created on demand inside service methods, not on init).
    """
    return StorageService()


DbSession = Annotated[AsyncSession, Depends(db_session)]
RedisDep = Annotated[Redis, Depends(redis_dep)]
StorageServiceDep = Annotated[StorageService, Depends(get_storage_service)]


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


async def get_current_user_with_role(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: DbSession,
) -> tuple[User, list[str]]:
    """Like `get_current_user`, but also returns the user's role names.

    Returns an empty list for the roles if the user has no role grants
    (e.g. the seed `system` user, or newly-registered visitors who haven't
    been assigned any roles yet).

    NOT yet wired to enforce permissions on any endpoint �� this is scaffolding
    for the RBAC follow-up. Endpoint authors can opt in by replacing
    `current_user: CurrentUser` with `current_user_role: CurrentUserWithRole`
    and writing `if "admin" in current_user_role[1]: ...`.

    Returns (User, list[str]) rather than (User, set[str]) so the order is
    deterministic — callers that display roles will get a stable presentation.
    """
    user = await get_current_user(credentials, session)
    result = await session.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
        .order_by(Role.name)
    )
    return user, [row[0] for row in result.all()]


CurrentUserWithRole = Annotated[
    tuple[User, list[str]], Depends(get_current_user_with_role)
]


def rate_limit(*, key_prefix: str, limit: int) -> Callable[..., Awaitable[None]]:
    """Build a per-IP rate-limit dependency for the given key/limit."""

    async def _check(request: Request, redis: RedisDep) -> None:
        limiter = SlidingWindowLimiter(redis)
        client_ip = request.client.host if request.client else "unknown"
        await limiter.hit(key=f"rl:{key_prefix}:{client_ip}", limit=limit)

    return _check
