"""Auth service: registration, login, refresh, logout."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import (
    LoginIn,
    RegisterIn,
    TokenPair,
    UserOut,
)

# Redis key shape for refresh-token store
_REFRESH_KEY = "refresh:{jti}"


def _refresh_key(jti: str) -> str:
    return _REFRESH_KEY.format(jti=jti)


def _now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(slots=True)
class AuthService:
    session: AsyncSession
    redis: Redis

    def _users(self) -> UserRepository:
        return UserRepository(self.session)

    # ------------------------------------------------------------------ register
    async def register(self, payload: RegisterIn) -> tuple[User, TokenPair]:
        users = self._users()
        existing = await users.get_by_email(payload.email)
        if existing is not None:
            raise ConflictError("Email already registered")

        user = await users.create(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
        )
        await self.session.commit()
        token = await self._issue_token_pair(str(user.id))
        return user, token

    # --------------------------------------------------------------------- login
    async def login(self, payload: LoginIn) -> tuple[User, TokenPair]:
        user = await self._users().get_by_email(payload.email)
        if user is None or not user.is_active:
            raise UnauthorizedError("Invalid credentials")
        if not verify_password(payload.password, user.hashed_password):
            raise UnauthorizedError("Invalid credentials")
        token = await self._issue_token_pair(str(user.id))
        return user, token

    # ------------------------------------------------------------------- refresh
    async def refresh(self, refresh_token: str) -> TokenPair:
        payload = decode_token(refresh_token, expected_type="refresh")
        jti = payload.get("jti")
        sub = payload.get("sub")
        if not jti or not sub:
            raise UnauthorizedError("Invalid token")

        stored = await self.redis.get(_refresh_key(jti))
        if stored is None or stored != sub:
            # Reuse of a revoked / rotated token → revoke all sessions for the user.
            await self._revoke_all_for_user(sub)
            raise UnauthorizedError("Refresh token revoked")

        user_id = uuid.UUID(sub)
        user = await self._users().get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("User not active")

        # Rotate: delete the old jti, then issue a new pair
        await self.redis.delete(_refresh_key(jti))
        return await self._issue_token_pair(sub)

    # -------------------------------------------------------------------- logout
    async def logout(self, access_token_payload: dict[str, Any]) -> None:
        sub = access_token_payload.get("sub")
        if not sub:
            return
        # Revoke all active refresh jtis for the user. For per-device logout,
        # pass the refresh token and delete only its jti.
        await self._revoke_all_for_user(sub)

    # -------------------------------------------------------------------- helpers
    async def _issue_token_pair(self, subject: str) -> TokenPair:
        access_token = create_access_token(subject)
        refresh_token, jti, expires_at = create_refresh_token(subject)
        ttl = max(1, int((expires_at.timestamp()) - _now().timestamp()))
        await self.redis.set(_refresh_key(jti), subject, ex=ttl)
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    async def _revoke_all_for_user(self, subject: str) -> None:
        # Scan for refresh:* keys belonging to this user.
        pattern = "refresh:*"
        async for raw_key in self.redis.scan_iter(match=pattern, count=200):
            value = await self.redis.get(raw_key)
            if value == subject:
                await self.redis.delete(raw_key)

    # -------------------------------------------------------------------- me
    async def get_user(self, user_id: uuid.UUID) -> UserOut:
        user = await self._users().get_by_id(user_id)
        if user is None:
            raise UnauthorizedError("User not found")
        return UserOut.model_validate(user)
