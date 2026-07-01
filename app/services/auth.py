"""Auth service: registration, login, token rotation, logout."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import TokenPair
from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


class AuthService:
    """Encapsulates the auth business logic."""

    def __init__(self, session: AsyncSession, redis: Redis):
        self.session = session
        self.redis = redis

    # ---- Internals ----------------------------------------------------------

    @staticmethod
    def _refresh_key(jti: str) -> str:
        return f"refresh:{jti}"

    @staticmethod
    def _now() -> datetime:
        return datetime.now(tz=UTC)

    async def _issue_token_pair(self, subject: str) -> TokenPair:
        access_token = create_access_token(subject)
        refresh_token, jti, expires_at = create_refresh_token(subject)
        ttl = max(1, int((expires_at.timestamp()) - self._now().timestamp()))
        await self.redis.set(self._refresh_key(jti), subject, ex=ttl)
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    async def _revoke_all_for_user(self, subject: str) -> None:
        pattern = "refresh:*"
        async for raw_key in self.redis.scan_iter(match=pattern, count=200):
            value = await self.redis.get(raw_key)
            if value == subject:
                await self.redis.delete(raw_key)

    # ---- Public API ---------------------------------------------------------

    async def register(self, email: str, password: str, full_name: str | None) -> tuple[User, TokenPair]:
        """Create a new user and issue a token pair."""
        # Fast path: pre-check so the common case (duplicate email) doesn't
        # pay the round-trip cost of an INSERT-and-rollback. This is
        # advisory — the authoritative guard is the IntegrityError catch
        # below, which handles the TOCTOU race.
        existing = await User.get_by_email(self.session, email)
        if existing is not None:
            raise ConflictError("Email already registered")

        user = User(
            email=email.lower(),
            hashed_password=hash_password(password),
            full_name=full_name,
        )
        self.session.add(user)
        try:
            await self.session.commit()
            await self.session.refresh(user)
        except IntegrityError as exc:
            # Race: another concurrent request registered the same email
            # between our SELECT and our INSERT. Translate to the same
            # error the pre-check would have raised.
            await self.session.rollback()
            raise ConflictError("Email already registered") from exc

        token = await self._issue_token_pair(str(user.id))
        return user, token

    async def login(self, email: str, password: str) -> tuple[User, TokenPair]:
        """Validate credentials and issue a token pair."""
        user = await User.get_by_email(self.session, email)
        if user is None or not user.is_active:
            raise UnauthorizedError("Invalid credentials")
        if not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid credentials")

        token = await self._issue_token_pair(str(user.id))
        return user, token

    async def refresh(self, refresh_token: str) -> TokenPair:
        """Rotate a refresh token, returning a new pair."""
        decoded = decode_token(refresh_token, expected_type="refresh")
        jti = decoded.get("jti")
        sub = decoded.get("sub")
        if not jti or not sub:
            raise UnauthorizedError("Invalid token")

        # Verify the jti is still valid (not revoked or rotated)
        stored = await self.redis.get(self._refresh_key(jti))
        if stored is None or stored != sub:
            # Reuse of a revoked/rotated token → revoke all sessions for the user
            await self._revoke_all_for_user(sub)
            raise UnauthorizedError("Refresh token revoked")

        # Verify the user still exists and is active
        user_id = uuid.UUID(sub)
        user = await User.get_by_id(self.session, user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("User not active")

        # Rotate: delete the old jti, then issue a new pair
        await self.redis.delete(self._refresh_key(jti))
        return await self._issue_token_pair(sub)

    async def logout(self, request: Request | None = None) -> None:
        """Revoke all refresh tokens for the current user.

        Decodes the access token from the Authorization header (best-effort)
        to determine the user subject.
        """
        if request is None:
            return

        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return

        token = auth_header.split(" ", 1)[1]
        decoded = decode_token(token, expected_type="access")
        sub = decoded.get("sub")
        if sub:
            await self._revoke_all_for_user(sub)
