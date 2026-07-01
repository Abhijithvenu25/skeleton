"""StaffProfile service.

Per-user HR-style fields live on `StaffProfile`. Roles are N:M and managed
through dedicated methods (`list_roles_for_user`, `replace_roles_for_user`,
`add_role`, `remove_role`) backed by the `user_roles` junction table.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.role import Role
from app.models.staff_profile import StaffProfile
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.crm.staff_profile import (
    StaffProfileIn,
    StaffProfilePatch,
)
from app.services.crm._common import (
    apply_audit_create,
    apply_audit_soft_delete,
    apply_audit_update,
    paginate,
)


class StaffProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- Per-user HR-style fields (StaffProfile itself) --------------------

    async def list(
        self, *, page: int = 1, size: int = 20
    ) -> tuple[list[StaffProfile], int]:
        return await paginate(
            self.session,
            StaffProfile,
            page=page,
            size=size,
            order_by=StaffProfile.user_id,
            where=[StaffProfile.deleted_at.is_(None)],
        )

    async def get_by_id(self, user_id: uuid.UUID) -> StaffProfile:
        profile = await StaffProfile.get_by_user_id(self.session, user_id)
        if profile is None or profile.deleted_at is not None:
            raise NotFoundError(f"StaffProfile {user_id} not found")
        return profile

    async def create(self, user_id: uuid.UUID, payload: StaffProfileIn, *, actor: User) -> StaffProfile:
        if await StaffProfile.get_by_user_id(self.session, user_id) is not None:
            raise ConflictError(f"StaffProfile for user {user_id} already exists")
        if (
            payload.employee_code is not None
            and await StaffProfile.exists_by_employee_code(
                self.session, payload.employee_code
            )
        ):
            raise ConflictError(f"employee_code '{payload.employee_code}' is already in use")
        profile = StaffProfile(
            user_id=user_id,
            employee_code=payload.employee_code,
            department=payload.department,
            phone=payload.phone,
            joined_on=payload.joined_on,
        )
        apply_audit_create(profile, actor=actor)
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def update(
        self, user_id: uuid.UUID, payload: StaffProfilePatch, *, actor: User
    ) -> StaffProfile:
        profile = await self.get_by_id(user_id)
        if (
            payload.employee_code is not None
            and payload.employee_code != profile.employee_code
            and await StaffProfile.exists_by_employee_code(
                self.session, payload.employee_code, exclude_user_id=user_id
            )
        ):
            raise ConflictError(f"employee_code '{payload.employee_code}' is already in use")
        if payload.employee_code is not None:
            profile.employee_code = payload.employee_code
        if payload.department is not None:
            profile.department = payload.department
        if payload.phone is not None:
            profile.phone = payload.phone
        if payload.joined_on is not None:
            profile.joined_on = payload.joined_on
        apply_audit_update(profile, actor=actor)
        await self.session.commit()
        return profile

    async def soft_delete(self, user_id: uuid.UUID, *, actor: User) -> None:
        profile = await self.get_by_id(user_id)
        apply_audit_soft_delete(profile, actor=actor)
        await self.session.commit()

    # ---- Roles (N:M via user_roles) -----------------------------------------

    async def list_roles_for_user(self, user_id: uuid.UUID) -> list[Role]:
        """Return all roles currently granted to the user, ordered by name."""
        result = await self.session.execute(
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .order_by(Role.name)
        )
        return list(result.scalars())

    async def _validate_role_ids(self, role_ids: list[uuid.UUID]) -> list[Role]:
        """Resolve role_ids to Role rows; raise 404 on the first miss.

        De-duplicates the input so a caller passing [A, A, B] doesn't error
        on the duplicate A.
        """
        unique = list(dict.fromkeys(role_ids))  # preserve order, dedupe
        result = await self.session.execute(
            select(Role).where(Role.id.in_(unique))
        )
        found = {r.id: r for r in result.scalars()}
        missing = [str(rid) for rid in unique if rid not in found]
        if missing:
            raise NotFoundError(f"Roles not found: {', '.join(missing)}")
        return [found[rid] for rid in unique]

    async def _grant_exists(
        self, user_id: uuid.UUID, role_id: uuid.UUID
    ) -> bool:
        """Pre-check used by add_role for the (user_id, role_id) composite PK."""
        return (
            await self.session.scalar(
                select(UserRole.user_id).where(
                    UserRole.user_id == user_id, UserRole.role_id == role_id
                )
            )
        ) is not None

    async def replace_roles_for_user(
        self, user_id: uuid.UUID, role_ids: list[uuid.UUID], *, actor: User
    ) -> list[Role]:
        """Set the user's roles to exactly `role_ids` (replace, not merge).

        Validates every role_id exists (404 on first miss). Removes any
        current grants not in the new set, adds any new ones. Returns the
        final sorted role list.
        """
        roles = await self._validate_role_ids(role_ids)
        now = datetime.now(tz=UTC)

        # Wipe current grants for this user.
        await self.session.execute(
            delete(UserRole).where(UserRole.user_id == user_id)
        )
        # Insert the new set. De-duped by `_validate_role_ids`.
        for role in roles:
            self.session.add(
                UserRole(
                    user_id=user_id,
                    role_id=role.id,
                    granted_at=now,
                    granted_by_id=actor.id,
                )
            )
        await self.session.commit()
        return sorted(roles, key=lambda r: r.name)

    async def add_role(
        self, user_id: uuid.UUID, role_id: uuid.UUID, *, actor: User
    ) -> Role:
        """Grant a single role. Idempotent: re-adding the same role returns
        the existing role without error. Raises 404 if the role doesn't exist.
        """
        role = await Role.get_by_id(self.session, role_id)
        if role is None:
            raise NotFoundError(f"Role {role_id} not found")
        if not await self._grant_exists(user_id, role_id):
            self.session.add(
                UserRole(
                    user_id=user_id,
                    role_id=role_id,
                    granted_at=datetime.now(tz=UTC),
                    granted_by_id=actor.id,
                )
            )
            await self.session.commit()
        return role

    async def remove_role(self, user_id: uuid.UUID, role_id: uuid.UUID, *, actor: User) -> None:
        """Revoke a single role. Idempotent: removing a role the user
        doesn't have is a no-op (no 404). This matches the spec behaviour
        where a missing revoke is benign.
        """
        # actor is unused but kept in the signature for symmetry with the
        # other audit-aware endpoints and for future use (e.g. an audit log
        # of role revocations).
        del actor
        result = await self.session.execute(
            delete(UserRole).where(
                UserRole.user_id == user_id, UserRole.role_id == role_id
            )
        )
        if result.rowcount:
            await self.session.commit()