"""StaffProfile service."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.staff_profile import StaffProfile
from app.models.user import User
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


class StaffProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

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
            role_id=payload.role_id,
            employee_code=payload.employee_code,
            department=payload.department,
            phone=payload.phone,
            joined_on=payload.joined_on,
        )
        apply_audit_create(profile, actor=actor)
        self.session.add(profile)
        await flush_and_refresh(self.session, profile)
        return profile

    async def update(
        self, user_id: uuid.UUID, payload: StaffProfilePatch, *, actor: User
    ) -> StaffProfile:
        profile = await self.get_by_id(user_id)
        if payload.role_id is not None:
            profile.role_id = payload.role_id
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
