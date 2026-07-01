"""StaffProfile endpoints (per-user HR fields) + role assignment sub-routes.

Roles are managed under /staff-profiles/{user_id}/roles.
Per-user fields (employee_code, department, etc.) live at the parent routes.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import Page
from app.schemas.crm.role import RoleOut
from app.schemas.crm.staff_profile import (
    StaffProfileIn,
    StaffProfileOut,
    StaffProfilePatch,
    UserRolesIn,
    UserRolesOut,
)
from app.services.crm._common import build_page
from app.services.crm.staff_profile import StaffProfileService

router = APIRouter(prefix="/staff-profiles", tags=["crm-staff-profiles"])


async def _to_out(service: StaffProfileService, profile) -> StaffProfileOut:
    """Build a StaffProfileOut from a profile, eagerly attaching roles.

    The `roles` field on StaffProfileOut is a computed list sourced from the
    user_roles junction (not an ORM column on StaffProfile), so we
    populate it explicitly after model_validate.
    """
    out = StaffProfileOut.model_validate(profile)
    roles = await service.list_roles_for_user(profile.user_id)
    out.roles = [RoleOut.model_validate(r) for r in roles]
    return out


def _get_service(session: DbSession) -> StaffProfileService:
    return StaffProfileService(session=session)


ServiceDep = Annotated[StaffProfileService, Depends(_get_service)]


# ---- Parent: per-user HR-style fields ---------------------------------------


@router.get("", response_model=Page[StaffProfileOut], summary="List staff profiles")
async def list_staff_profiles(
    service: ServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> Page[StaffProfileOut]:
    items, total = await service.list(page=page, size=size)
    # Eager-load roles per profile. `StaffProfileOut.model_validate(p)` builds
    # the row from attributes; we then attach roles explicitly since the
    # `roles` field is computed from the N:M user_roles junction.
    out: list[StaffProfileOut] = []
    for profile in items:
        out.append(await _to_out(service, profile))
    return build_page(out, total, page, size)


@router.post(
    "/{user_id}",
    response_model=StaffProfileOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a staff profile for a user (no role assignment; use /roles)",
)
async def create_staff_profile(
    user_id: uuid.UUID,
    payload: StaffProfileIn,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> StaffProfileOut:
    profile = await service.create(user_id, payload, actor=_current_user)
    return await _to_out(service, profile)


@router.get("/{user_id}", response_model=StaffProfileOut, summary="Get staff profile")
async def get_staff_profile(user_id: uuid.UUID, service: ServiceDep) -> StaffProfileOut:
    profile = await service.get_by_id(user_id)
    return await _to_out(service, profile)


@router.patch(
    "/{user_id}",
    response_model=StaffProfileOut,
    summary="Update per-user staff fields (does NOT change roles)",
)
async def update_staff_profile(
    user_id: uuid.UUID,
    payload: StaffProfilePatch,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> StaffProfileOut:
    profile = await service.update(user_id, payload, actor=_current_user)
    return await _to_out(service, profile)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete staff profile (does NOT revoke roles)",
)
async def delete_staff_profile(
    user_id: uuid.UUID,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> None:
    await service.soft_delete(user_id, actor=_current_user)


# ---- Sub-resource: role assignment -----------------------------------------
#
# NOTE: All write endpoints here should ideally be gated by an admin/owner
# role check via CurrentUserWithRole. We currently don't enforce that — see
# the security follow-up. Adding the dep now would break existing callers
# during the rollout. Logged as a known gap; revisit when we wire RBAC.


@router.get(
    "/{user_id}/roles",
    response_model=UserRolesOut,
    summary="List roles currently granted to a user",
)
async def list_user_roles(user_id: uuid.UUID, service: ServiceDep) -> UserRolesOut:
    roles = await service.list_roles_for_user(user_id)
    return UserRolesOut(roles=[RoleOut.model_validate(r) for r in roles])


@router.put(
    "/{user_id}/roles",
    response_model=UserRolesOut,
    summary="Replace the user's roles with the given set",
)
async def replace_user_roles(
    user_id: uuid.UUID,
    payload: UserRolesIn,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> UserRolesOut:
    roles = await service.replace_roles_for_user(
        user_id, payload.role_ids, actor=_current_user
    )
    return UserRolesOut(roles=[RoleOut.model_validate(r) for r in roles])


@router.post(
    "/{user_id}/roles/{role_id}",
    response_model=RoleOut,
    status_code=status.HTTP_201_CREATED,
    summary="Grant a single role to a user (idempotent)",
)
async def add_user_role(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> RoleOut:
    role = await service.add_role(user_id, role_id, actor=_current_user)
    return RoleOut.model_validate(role)


@router.delete(
    "/{user_id}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a single role from a user (idempotent)",
)
async def remove_user_role(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> None:
    # Errors raise NotFoundError / ConflictError; the global AppError handler
    # translates them to the right HTTP status.
    await service.remove_role(user_id, role_id, actor=_current_user)
