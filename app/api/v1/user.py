"""User CRUD endpoints. Public — no auth required.

Superadmin-only concern in the frontend (UI hidden from non-superadmins);
the API mirrors that trade-off, same as /roles.

All success responses use the common ApiResponse envelope — see
app/schemas/common.py and app/api/v1/_response.py.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DbSession
from app.api.v1._response import created_single, ok_list, ok_single
from app.api.v1._user_response import build_user_out
from app.schemas.common import ApiResponse
from app.schemas.user import UserCreate, UserOut, UserPatch
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _get_user_service(db: DbSession) -> UserService:
    return UserService(session=db)


UserServiceDep = Annotated[UserService, Depends(_get_user_service)]


# ---- CRUD ------------------------------------------------------------------


@router.post(
    "",
    response_model=ApiResponse[UserOut],
    status_code=status.HTTP_201_CREATED,
    summary="Admin-style create a user (optionally with multiple roles and an S3 user_image URL)",
)
async def create_user(
    payload: UserCreate,
    service: UserServiceDep,
) -> ApiResponse[UserOut]:
    user = await service.create(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        user_image=payload.user_image,
        is_active=payload.is_active,
        is_superuser=payload.is_superuser,
        role_ids=payload.role_ids,
    )
    return created_single(
        build_user_out(user),
        "user created successfully.",
    )


@router.get(
    "",
    response_model=ApiResponse[UserOut],
    summary="List users (paginated, optional search by email or full_name)",
)
async def list_users(
    service: UserServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=64),
) -> ApiResponse[UserOut]:
    skip = (page - 1) * size
    items, total = await service.list(skip=skip, limit=size, search=search)
    return ok_list(
        [build_user_out(u) for u in items],
        page=page,
        size=size,
        total=total,
        message="users fetched successfully.",
    )


@router.get(
    "/{user_id}",
    response_model=ApiResponse[UserOut],
    summary="Get a user by id",
)
async def get_user(
    user_id: uuid.UUID,
    service: UserServiceDep,
) -> ApiResponse[UserOut]:
    user = await service.get(user_id)
    return ok_single(
        build_user_out(user),
        "user fetched successfully.",
    )


@router.patch(
    "/{user_id}",
    response_model=ApiResponse[UserOut],
    summary="Patch full_name / user_image / is_active / is_superuser (role changes use /roles/{id}/users)",
)
async def update_user(
    user_id: uuid.UUID,
    payload: UserPatch,
    service: UserServiceDep,
) -> ApiResponse[UserOut]:
    user = await service.update(
        user_id=user_id,
        full_name=payload.full_name,
        user_image=payload.user_image,
        is_active=payload.is_active,
        is_superuser=payload.is_superuser,
    )
    return ok_single(
        build_user_out(user),
        "user updated successfully.",
    )
