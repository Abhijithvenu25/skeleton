"""Pytest fixtures.

Integration tests run against the real PostgreSQL + Redis services declared
in docker-compose.yml. The fixtures below expect services to be reachable
via the standard env vars (POSTGRES_*, REDIS_URL) — `make up` brings them up.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import TYPE_CHECKING

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import create_access_token
from app.db.redis import close_redis
from app.main import app
from app.repositories.user import UserRepository

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from app.models.user import User

# Per-test DB index. Falls back to 1 if unset.
os.environ.setdefault("REDIS_TEST_DB", "1")


@pytest_asyncio.fixture
async def engine():
    # Per-test engine with NullPool: each session gets a fresh connection so we
    # don't bind asyncpg connections across event-loop boundaries between tests.
    eng = create_async_engine(settings.database_url, future=True, poolclass=NullPool)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncIterator[AsyncSession]:
    # Create a new connection per test to avoid asyncpg concurrent operation errors
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    async with session_factory() as session:
        # Truncate tables in a transaction
        async with session.begin():
            await session.execute(text("TRUNCATE TABLE customers, users RESTART IDENTITY CASCADE"))
        yield session


@pytest_asyncio.fixture
async def redis_client():
    from redis.asyncio import from_url

    client = from_url(str(settings.redis_url), decode_responses=True)
    await client.flushdb()
    try:
        yield client
    finally:
        await client.flushdb()
        await client.aclose()


@pytest_asyncio.fixture
async def client(redis_client, db_session) -> AsyncIterator[AsyncClient]:
    from app.api.deps import db_session as db_session_dep
    from app.db.session import get_session

    # Override DB session to use the test session
    async def _get_session_override() -> AsyncIterator[AsyncSession]:
        yield db_session

    # Override Redis dependency
    async def _redis_override() -> AsyncIterator:
        yield redis_client

    app.dependency_overrides[get_session] = _get_session_override
    app.dependency_overrides[db_session_dep] = _get_session_override
    from app.api.deps import redis_dep
    app.dependency_overrides[redis_dep] = _redis_override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def user_factory(db_session: AsyncSession):
    async def _make(
        *,
        email: str | None = None,
        password: str = "supersecret123",
        is_active: bool = True,
        is_superuser: bool = False,
    ) -> User:
        from app.core.security import hash_password

        repo = UserRepository(db_session)
        user = await repo.create(
            email=email or f"user-{uuid.uuid4().hex[:8]}@example.com",
            hashed_password=hash_password(password),
            full_name="Test User",
            is_active=is_active,
            is_superuser=is_superuser,
        )
        await db_session.commit()
        return user

    return _make


@pytest_asyncio.fixture
async def auth_user(user_factory) -> User:
    return await user_factory(email="alice@example.com")


@pytest_asyncio.fixture
async def auth_headers(auth_user: User) -> dict[str, str]:
    token = create_access_token(str(auth_user.id))
    return {"Authorization": f"Bearer {token}"}


# Final cleanup of the global Redis client used by the app
@pytest_asyncio.fixture(scope="session", autouse=True)
async def _close_global_redis():
    yield
    await close_redis()
    # give asyncio a moment to finalize
    await asyncio.sleep(0)
