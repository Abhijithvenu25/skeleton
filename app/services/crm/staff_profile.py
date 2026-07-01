"""StaffProfile service.

Per-user HR-style fields live on `StaffProfile`. Roles are N:M and managed
through dedicated methods (`list_roles_for_user`, `replace_roles_for_user`,
`add_role`, `remove_role`) backed by the `user_roles` junction table.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

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
    apply_audit_update,
    commit,
    flush_and_refresh,
    paginate,
)
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


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
        profile = StaffProfile(
            user_id=user_id,
            employee_code=payload.employee_code,
            department=payload.department,
            phone=payload.phone,
            joined_on=payload.joined_on,
        )
        apply_audit_create(profile, actor=actor)
        self.session.add(profile)
        try:
            await flush_and_refresh(self.session, profile)
        except IntegrityError as exc:
            # Most likely: employee_code collision (uq_staff_profiles_employee_code).
            raise ConflictError(
                f"StaffProfile for user {user_id} already exists or employee_code in use"
            ) from exc
        return profile

    async def update(
        self, user_id: uuid.UUID, payload: StaffProfilePatch, *, actor: User
    ) -> StaffProfile:
        profile = await self.get_by_id(user_id)
        if payload.employee_code is not None:
            profile.employee_code = payload.employee_code
        if payload.department is not None:
            profile.department = payload.department
        if payload.phone is not None:
            profile.phone = payload.phone
        if payload.joined_on is not None:
            profile.joined_on = payload.joined_on
        apply_audit_update(profile, actor=actor)
        await commit(self.session)
        return profile

    async def soft_delete(self, user_id: uuid.UUID, *, actor: User) -> None:
        from app.services.crm._common import apply_audit_soft_delete

        profile = await self.get_by_id(user_id)
        apply_audit_soft_delete(profile, actor=actor)
        await commit(self.session)

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
        # Race protection: if a concurrent replace or grant inserts the
        # same (user_id, role_id) between our DELETE and our INSERT, the
        # composite-PK constraint fires. We retry the loop up to a couple
        # of times (each retry sees the now-inserted row, so the SELECT
        # in _validate_role_ids short-circuits via the dedup), then fall
        # back to 409 if the conflict is persistent.
        for attempt in range(3):
            try:
                for role in roles:
                    self.session.add(
                        UserRole(
                            user_id=user_id,
                            role_id=role.id,
                            granted_at=now,
                            granted_by_id=actor.id,
                        )
                    )
                await commit(self.session)
                break
            except IntegrityError as exc:
                await self.session.rollback()
                if attempt == 2:
                    # Persistent conflict — another caller is racing
                    # hard. Surface as 409 so the client can retry.
                    from app.core.exceptions import ConflictError
                    raise ConflictError(
                        "Concurrent role update conflict; please retry"
                    ) from exc
                # Else: loop and re-insert. The duplicate rows we tried
                # to insert on the previous attempt are now persisted by
                # the racing caller, so this attempt's inserts may also
                # collide, hence the bounded retry.
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
        # Fast path: pre-check so the common case doesn't pay for an
        # INSERT-and-rollback. Authoritative guard is the IntegrityError
        # catch below (handles the TOCTOU race).
        existing = await self.session.scalar(
            select(UserRole).where(
                UserRole.user_id == user_id, UserRole.role_id == role_id
            )
        )
        if existing is None:
            self.session.add(
                UserRole(
                    user_id=user_id,
                    role_id=role_id,
                    granted_at=datetime.now(tz=UTC),
                    granted_by_id=actor.id,
                )
            )
            try:
                await commit(self.session)
            except IntegrityError:
                # Race: another concurrent call inserted the same
                # (user_id, role_id) row between our SELECT and our INSERT.
                # Idempotent contract: re-adding the same role is a no-op,
                # not an error. So we just swallow the IntegrityError and
                # return the existing role.
                await self.session.rollback()
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
            await commit(self.session)
