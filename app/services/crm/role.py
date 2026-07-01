"""Role service."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.role import Role
from app.models.user import User
from app.schemas.crm.role import RoleIn, RolePatch
from app.services.crm._common import (
    apply_audit_create,
    apply_audit_update,
    paginate,
)


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
        if await Role.exists_by_name(self.session, payload.name):
            raise ConflictError(f"Role '{payload.name}' already exists")
        role = Role(name=payload.name, permissions=payload.permissions)
        apply_audit_create(role, actor=actor)
        self.session.add(role)
        await self.session.commit()
        await self.session.refresh(role)
        return role

    async def update(self, role_id: uuid.UUID, payload: RolePatch, *, actor: User) -> Role:
        role = await self.get_by_id(role_id)
        new_name = payload.name if payload.name is not None else role.name
        if payload.name is not None and await Role.exists_by_name(
            self.session, payload.name, exclude_id=role.id
        ):
            raise ConflictError(f"Role '{new_name}' already exists")
        if payload.name is not None:
            role.name = payload.name
        if payload.permissions is not None:
            role.permissions = payload.permissions
        apply_audit_update(role, actor=actor)
        await self.session.commit()
        return role

    async def delete(self, role_id: uuid.UUID, *, actor: User) -> None:
        role = await self.get_by_id(role_id)
        await self.session.delete(role)
        await self.session.commit()


__all__ = ["RoleService"]