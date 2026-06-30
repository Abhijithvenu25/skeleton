"""StaffProfile endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import Page
from app.schemas.crm.staff_profile import (
    StaffProfileIn,
    StaffProfileOut,
    StaffProfilePatch,
)
from app.services.crm._common import build_page
from app.services.crm.staff_profile import StaffProfileService

router = APIRouter(prefix="/staff-profiles", tags=["crm-staff-profiles"])


def _get_service(session: DbSession) -> StaffProfileService:
    return StaffProfileService(session=session)


ServiceDep = Annotated[StaffProfileService, Depends(_get_service)]


@router.get("", response_model=Page[StaffProfileOut], summary="List staff profiles")
async def list_staff_profiles(
    service: ServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> Page[StaffProfileOut]:
    items, total = await service.list(page=page, size=size)
    return build_page(
        [StaffProfileOut.model_validate(p) for p in items], total, page, size
    )


@router.post(
    "/{user_id}",
    response_model=StaffProfileOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a staff profile for a user",
)
async def create_staff_profile(
    user_id: uuid.UUID,
    payload: StaffProfileIn,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> StaffProfileOut:
    profile = await service.create(user_id, payload, actor=_current_user)
    return StaffProfileOut.model_validate(profile)


@router.get("/{user_id}", response_model=StaffProfileOut, summary="Get staff profile")
async def get_staff_profile(user_id: uuid.UUID, service: ServiceDep) -> StaffProfileOut:
    profile = await service.get_by_id(user_id)
    return StaffProfileOut.model_validate(profile)


@router.patch("/{user_id}", response_model=StaffProfileOut, summary="Update staff profile")
async def update_staff_profile(
    user_id: uuid.UUID,
    payload: StaffProfilePatch,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> StaffProfileOut:
    profile = await service.update(user_id, payload, actor=_current_user)
    return StaffProfileOut.model_validate(profile)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete staff profile",
)
async def delete_staff_profile(
    user_id: uuid.UUID,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> None:
    await service.soft_delete(user_id, actor=_current_user)
