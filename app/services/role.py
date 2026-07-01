"""Role service: CRUD + grant/revoke + reverse lookups.

Mirrors the AuthService pattern: pre-check -> write -> IntegrityError ->
ConflictError. Pre-checks exist for fast-path 409s on duplicate role
names; the IntegrityError handler in app.core.exceptions is the
authoritative safety net for races and for code paths that forget
the pre-check.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.core.exceptions import ConflictError, NotFoundError
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


class RoleService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- Internals ----------------------------------------------------------

    @staticmethod
    def _now() -> datetime:
        return datetime.now(tz=UTC)

    @staticmethod
    def _normalize(name: str) -> str:
        """Lower-case + strip. DB unique index is case-sensitive as-stored,
        so without normalization 'Admin' and 'admin' coexist."""
        return name.strip().lower()

    async def _get_or_404(self, role_id: uuid.UUID) -> Role:
        role = await Role.get_by_id(self.session, role_id)
        if role is None:
            raise NotFoundError(f"Role {role_id} not found")
        return role

    # ---- CRUD ---------------------------------------------------------------

    async def create(
        self,
        name: str,
        permissions: dict[str, Any] | None,
        description: str | None = None,
    ) -> Role:
        normalized = self._normalize(name)
        if await Role.exists_by_name(self.session, normalized):
            raise ConflictError(f"Role '{normalized}' already exists")
        # Compute the next business code as `R-<max_suffix + 1>`. Two
        # concurrent inserts can both compute the same code; the UNIQUE
        # index `uq_roles_role_code` is the authoritative safety net —
        # the IntegrityError catch below translates the collision into a
        # clean 409 (matching the pre-check + IntegrityError pattern
        # already used for `name`).
        next_n = (await Role.max_role_code_suffix(self.session)) + 1
        role_code = f"R-{next_n}"
        role = Role(
            name=normalized,
            permissions=permissions or {},
            role_code=role_code,
            description=description,
        )
        self.session.add(role)
        try:
            await self.session.commit()
            await self.session.refresh(role)
        except IntegrityError as exc:
            # Race: another insert won the code-generation race OR
            # collided on `name`. Roll back either way and let the global
            # handler map `uq_roles_role_code` -> 409 if it's that.
            await self.session.rollback()
            raise ConflictError(f"Role '{normalized}' already exists") from exc
        return role

    async def get(self, role_id: uuid.UUID) -> Role:
        return await self._get_or_404(role_id)

    async def paginate(
        self, skip: int, limit: int, search: str | None = None
    ) -> tuple[list[Role], int]:
        """Return (items, total). search is a case-insensitive substring
        match on `name`."""
        where = Role.name.ilike(f"%{search.strip()}%") if search else None
        count_stmt = select(func.count()).select_from(Role)
        list_stmt = select(Role).order_by(Role.name)
        if where is not None:
            count_stmt = count_stmt.where(where)
            list_stmt = list_stmt.where(where)
        total = int(await self.session.scalar(count_stmt) or 0)
        result = await self.session.scalars(list_stmt.offset(skip).limit(limit))
        rows: list[Role] = list(result.all())
        return rows, total

    async def update(
        self,
        role_id: uuid.UUID,
        name: str | None = None,
        permissions: dict[str, Any] | None = None,
        description: str | None = None,
    ) -> Role:
        role = await self._get_or_404(role_id)
        normalized: str | None = None
        if name is not None:
            normalized = self._normalize(name)
            if await Role.exists_by_name(self.session, normalized, exclude_id=role_id):
                raise ConflictError(f"Role '{normalized}' already exists")
            role.name = normalized
        if permissions is not None:
            role.permissions = permissions
        # `description` is patchable separately. Clients can clear it by
        # passing null; passing the field unset leaves it as-is.
        if description is not None:
            role.description = description
        try:
            await self.session.commit()
            await self.session.refresh(role)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(f"Role '{normalized}' already exists") from exc
        return role

    async def delete(self, role_id: uuid.UUID) -> None:
        role = await self._get_or_404(role_id)
        try:
            await self.session.delete(role)
            await self.session.commit()
        except IntegrityError as exc:
            # UserRole.role_id is ON DELETE RESTRICT -> deleting a role
            # that is still granted raises here. Tailor the message instead
            # of the generic 409 the global handler would emit.
            await self.session.rollback()
            raise ConflictError("Role is granted to one or more users; revoke first") from exc

    # ---- Grant / revoke -----------------------------------------------------

    async def assign_to_user(
        self,
        role_id: uuid.UUID,
        user_id: uuid.UUID,
        granted_by_id: uuid.UUID | None,
    ) -> UserRole:
        # Validate both sides explicitly so a missing user_id returns 404
        # rather than an IntegrityError -> 409 (which is the wrong code
        # for "this user doesn't exist" from the client's perspective).
        await self._get_or_404(role_id)
        user = await User.get_by_id(self.session, user_id)
        if user is None:
            raise NotFoundError(f"User {user_id} not found")

        grant = UserRole(
            user_id=user_id,
            role_id=role_id,
            granted_at=self._now(),
            granted_by_id=granted_by_id,
        )
        self.session.add(grant)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            # Composite PK (user_id, role_id) violation -> already granted.
            await self.session.rollback()
            raise ConflictError(f"User {user_id} already has role {role_id}") from exc
        return grant

    async def revoke_from_user(self, role_id: uuid.UUID, user_id: uuid.UUID) -> None:
        # Distinguish 'role missing' / 'user missing' / 'grant missing' so
        # the client knows which thing is wrong. We SELECT the grant first
        # rather than relying on cursor.rowcount (which mypy can't see on
        # async Result) — this also avoids a second round-trip on the
        # happy path because the DELETE just follows the SELECT.
        existing = await self.session.scalar(
            select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        )
        if existing is None:
            if await Role.get_by_id(self.session, role_id) is None:
                raise NotFoundError(f"Role {role_id} not found")
            if await User.get_by_id(self.session, user_id) is None:
                raise NotFoundError(f"User {user_id} not found")
            raise NotFoundError(f"User {user_id} does not have role {role_id}")
        await self.session.delete(existing)
        await self.session.commit()

    # ---- Reverse lookups ----------------------------------------------------

    async def users_with_role(self, role_id: uuid.UUID) -> list[User]:
        # Confirm role exists so empty list = "no grants", not "no such role".
        await self._get_or_404(role_id)
        stmt = (
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .where(UserRole.role_id == role_id)
            .order_by(UserRole.granted_at)
        )
        result = await self.session.scalars(stmt)
        users: list[User] = list(result.all())
        return users

    async def roles_for_user(self, user_id: uuid.UUID) -> list[Role]:
        user = await User.get_by_id(self.session, user_id)
        if user is None:
            raise NotFoundError(f"User {user_id} not found")
        # User.roles is selectin-loaded by the relationship — no extra query.
        roles: list[Role] = list(user.roles)
        return roles
