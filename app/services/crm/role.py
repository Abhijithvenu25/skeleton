"""Role service."""

from __future__ import annotations

import uuid

from app.core.exceptions import ConflictError, NotFoundError
from app.models.role import Role
from app.models.user import User
from app.schemas.crm.role import RoleIn, RolePatch
from app.services.crm._common import (
    apply_audit_create,
    apply_audit_update,
    commit,
    flush_and_refresh,
    paginate,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


class RoleService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self, *, page: int = 1, size: int = 20
    ) -> tuple[list[Role], int]:
        return await paginate(
            self.session, Role, page=page, size=size, order_by=Role.name
        )

    async def get_by_id(self, role_id: uuid.UUID) -> Role:
        role = await Role.get_by_id(self.session, role_id)
        if role is None:
            raise NotFoundError(f"Role {role_id} not found")
        return role

    async def create(self, payload: RoleIn, *, actor: User) -> Role:
        role = Role(name=payload.name, permissions=payload.permissions)
        apply_audit_create(role, actor=actor)
        self.session.add(role)
        try:
            await flush_and_refresh(self.session, role)
        except IntegrityError as exc:
            # Most likely: uq_roles_name. The flush_and_refresh helper also
            # catches IntegrityError and re-raises as ConflictError, but
            # with a generic message — we override here for a specific one.
            raise ConflictError(
                f"Role '{payload.name}' already exists"
            ) from exc
        return role

    async def update(self, role_id: uuid.UUID, payload: RolePatch, *, actor: User) -> Role:
        role = await self.get_by_id(role_id)
        if payload.name is not None:
            role.name = payload.name
        if payload.permissions is not None:
            role.permissions = payload.permissions
        apply_audit_update(role, actor=actor)
        try:
            await commit(self.session)
        except IntegrityError as exc:
            # Renaming to a name that's already taken.
            new_name = payload.name if payload.name is not None else "?"
            raise ConflictError(
                f"Role '{new_name}' already exists"
            ) from exc
        return role

    async def delete(self, role_id: uuid.UUID, *, actor: User) -> None:
        role = await self.get_by_id(role_id)
        await self.session.delete(role)
        await commit(self.session)


__all__ = ["RoleService"]
