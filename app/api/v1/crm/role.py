"""Role endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import Page
from app.schemas.crm.role import (
    RoleIn,
    RoleOut,
    RolePatch,
)
from app.services.crm._common import build_page
from app.services.crm.role import RoleService

router = APIRouter(prefix="/roles", tags=["crm-roles"])


def _get_service(session: DbSession) -> RoleService:
    return RoleService(session=session)


ServiceDep = Annotated[RoleService, Depends(_get_service)]


@router.get("", response_model=Page[RoleOut], summary="List roles")
async def list_roles(
    service: ServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> Page[RoleOut]:
    items, total = await service.list(page=page, size=size)
    return build_page([RoleOut.model_validate(r) for r in items], total, page, size)


@router.post("", response_model=RoleOut, status_code=status.HTTP_201_CREATED, summary="Create role")
async def create_role(
    payload: RoleIn,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> RoleOut:
    role = await service.create(payload, actor=_current_user)
    return RoleOut.model_validate(role)


@router.get("/{role_id}", response_model=RoleOut, summary="Get role by id")
async def get_role(role_id: uuid.UUID, service: ServiceDep) -> RoleOut:
    role = await service.get_by_id(role_id)
    return RoleOut.model_validate(role)


@router.patch("/{role_id}", response_model=RoleOut, summary="Update role")
async def update_role(
    role_id: uuid.UUID,
    payload: RolePatch,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> RoleOut:
    role = await service.update(role_id, payload, actor=_current_user)
    return RoleOut.model_validate(role)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete role")
async def delete_role(
    role_id: uuid.UUID,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> None:
    await service.delete(role_id, actor=_current_user)
