"""Role CRUD + grant/revoke endpoints. Public — no auth required.

These endpoints are intentionally open because role management is a
superadmin-only concern in the frontend. The frontend hides the UI from
non-superadmins, so the API does not need to enforce it.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DbSession
from app.schemas.common import Page
from app.schemas.role import (
    RoleAssignIn,
    RoleIn,
    RoleOut,
    RolePatch,
    UserRoleOut,
)
from app.schemas.user import UserOut
from app.services.role import RoleService

router = APIRouter(prefix="/roles", tags=["roles"])


def _get_role_service(db: DbSession) -> RoleService:
    return RoleService(session=db)


RoleServiceDep = Annotated[RoleService, Depends(_get_role_service)]


# ---- CRUD ------------------------------------------------------------------


@router.post(
    "",
    response_model=RoleOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a role",
)
async def create_role(
    payload: RoleIn,
    service: RoleServiceDep,
) -> RoleOut:
    role = await service.create(name=payload.name, permissions=payload.permissions)
    return RoleOut.model_validate(role)


@router.get(
    "",
    response_model=Page[RoleOut],
    summary="List roles (paginated, optional search)",
)
async def list_roles(
    service: RoleServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, min_length=1, max_length=64),
) -> Page[RoleOut]:
    skip = (page - 1) * size
    items, total = await service.paginate(skip=skip, limit=size, search=search)
    pages = (total + size - 1) // size if total else 1
    return Page[RoleOut](
        items=[RoleOut.model_validate(r) for r in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get(
    "/{role_id}",
    response_model=RoleOut,
    summary="Get a role by id",
)
async def get_role(
    role_id: uuid.UUID,
    service: RoleServiceDep,
) -> RoleOut:
    return RoleOut.model_validate(await service.get(role_id))


@router.patch(
    "/{role_id}",
    response_model=RoleOut,
    summary="Partial update of a role",
)
async def update_role(
    role_id: uuid.UUID,
    payload: RolePatch,
    service: RoleServiceDep,
) -> RoleOut:
    role = await service.update(
        role_id=role_id,
        name=payload.name,
        permissions=payload.permissions,
    )
    return RoleOut.model_validate(role)


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a role (409 if still granted to users)",
)
async def delete_role(
    role_id: uuid.UUID,
    service: RoleServiceDep,
) -> None:
    await service.delete(role_id)


# ---- Grant / revoke --------------------------------------------------------


@router.post(
    "/{role_id}/users",
    response_model=UserRoleOut,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a role to a user (granted_by is optional; pass a user id to record who granted it)",
)
async def assign_role_to_user(
    role_id: uuid.UUID,
    payload: RoleAssignIn,
    service: RoleServiceDep,
) -> UserRoleOut:
    grant = await service.assign_to_user(
        role_id=role_id,
        user_id=payload.user_id,
        granted_by_id=payload.granted_by_id,
    )
    return UserRoleOut.model_validate(grant)


@router.get(
    "/{role_id}/users",
    response_model=list[UserOut],
    summary="List users that hold this role (ordered by grant time)",
)
async def list_users_with_role(
    role_id: uuid.UUID,
    service: RoleServiceDep,
) -> list[UserOut]:
    users = await service.users_with_role(role_id)
    return [UserOut.model_validate(u) for u in users]


@router.get(
    "/users/{user_id}/roles",
    response_model=list[RoleOut],
    summary="List roles granted to a user",
)
async def list_user_roles(
    user_id: uuid.UUID,
    service: RoleServiceDep,
) -> list[RoleOut]:
    roles = await service.roles_for_user(user_id)
    return [RoleOut.model_validate(r) for r in roles]


@router.delete(
    "/{role_id}/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a role from a user",
)
async def revoke_role_from_user(
    role_id: uuid.UUID,
    user_id: uuid.UUID,
    service: RoleServiceDep,
) -> None:
    await service.revoke_from_user(role_id, user_id)
