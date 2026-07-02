"""User CRUD service. Public — no auth required (superadmin-only in the UI).

Mirrors AuthService / RoleService patterns: pre-check -> write ->
IntegrityError -> ConflictError. The global IntegrityError handler in
app.core.exceptions already maps `ix_users_email` -> "Email already
registered"; the explicit catches here produce the same message but
let us raise cleanly without going through the global handler.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- Internals ----------------------------------------------------------

    @staticmethod
    def _now() -> datetime:
        return datetime.now(tz=UTC)

    async def _get_or_404(self, user_id: uuid.UUID) -> User:
        user = await User.get_by_id(self.session, user_id)
        if user is None:
            raise NotFoundError(f"User {user_id} not found")
        return user

    # ---- CRUD ---------------------------------------------------------------

    async def list(
        self, skip: int, limit: int, search: str | None = None
    ) -> tuple[list[User], int]:
        """(items, total). search is a case-insensitive substring match
        on email OR full_name."""
        where = None
        if search:
            pattern = f"%{search.strip()}%"
            where = or_(User.email.ilike(pattern), User.full_name.ilike(pattern))

        count_stmt = select(func.count()).select_from(User)
        list_stmt = select(User).order_by(User.created_at.desc())
        if where is not None:
            count_stmt = count_stmt.where(where)
            list_stmt = list_stmt.where(where)

        total = int(await self.session.scalar(count_stmt) or 0)
        result = await self.session.scalars(list_stmt.offset(skip).limit(limit))
        rows: list[User] = list(result.all())
        return rows, total

    async def get(self, user_id: uuid.UUID) -> User:
        return await self._get_or_404(user_id)

    async def create(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None,
        is_active: bool,
        is_superuser: bool,
        role_id: uuid.UUID | None,
    ) -> User:
        normalized = email.lower()
        if await User.get_by_email(self.session, normalized) is not None:
            raise ConflictError("Email already registered")

        user = User(
            email=normalized,
            hashed_password=hash_password(password),
            full_name=full_name,
            is_active=is_active,
            is_superuser=is_superuser,
        )
        self.session.add(user)
        try:
            # flush() to assign user.id without committing, so we can
            # catch the email-unique race without rolling back a
            # half-built row.
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Email already registered") from exc

        # Optional initial role assignment. Validate the role exists so
        # the caller gets a clean 404 rather than a generic 500.
        if role_id is not None:
            role = await Role.get_by_id(self.session, role_id)
            if role is None:
                await self.session.rollback()
                raise NotFoundError(f"Role {role_id} not found")
            self.session.add(
                UserRole(
                    user_id=user.id,
                    role_id=role_id,
                    granted_at=self._now(),
                    granted_by_id=None,
                )
            )
            try:
                await self.session.commit()
            except IntegrityError as exc:
                await self.session.rollback()
                raise ConflictError(f"User already has role {role_id}") from exc
        else:
            await self.session.commit()

        await self.session.refresh(user)
        # Re-prime the selectin-loaded `roles` relationship so the response
        # reflects the just-inserted grant without a second round-trip.
        await self.session.refresh(user, attribute_names=["roles"])
        return user

    async def update(
        self,
        user_id: uuid.UUID,
        *,
        full_name: str | None = None,
        is_active: bool | None = None,
        is_superuser: bool | None = None,
    ) -> User:
        user = await self._get_or_404(user_id)
        if full_name is not None:
            user.full_name = full_name
        if is_active is not None:
            user.is_active = is_active
        if is_superuser is not None:
            user.is_superuser = is_superuser
        await self.session.commit()
        await self.session.refresh(user)
        return user
