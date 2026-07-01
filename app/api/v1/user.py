"""User CRUD endpoints. Public — no auth required.

Superadmin-only concern in the frontend (UI hidden from non-superadmins);
the API mirrors that trade-off, same as /roles.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DbSession
from app.api.v1._user_response import build_user_out
from app.schemas.user import UserCreate, UserList, UserOut, UserPatch
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _get_user_service(db: DbSession) -> UserService:
    return UserService(session=db)


UserServiceDep = Annotated[UserService, Depends(_get_user_service)]


# ---- CRUD ------------------------------------------------------------------


@router.post(
    "",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Admin-style create a user (optionally with an initial role)",
)
async def create_user(
    payload: UserCreate,
    service: UserServiceDep,
) -> UserOut:
    user = await service.create(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        is_active=payload.is_active,
        is_superuser=payload.is_superuser,
        role_id=payload.role_id,
    )
    return await build_user_out(service.session, user)


@router.get(
    "",
    response_model=UserList,
    summary="List users (paginated, optional search by email or full_name)",
)
async def list_users(
    service: UserServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, min_length=1, max_length=64),
) -> UserList:
    skip = (page - 1) * size
    items, total = await service.list(skip=skip, limit=size, search=search)
    pages = (total + size - 1) // size if total else 1
    return UserList(
        items=[await build_user_out(service.session, u) for u in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get(
    "/{user_id}",
    response_model=UserOut,
    summary="Get a user by id",
)
async def get_user(
    user_id: uuid.UUID,
    service: UserServiceDep,
) -> UserOut:
    user = await service.get(user_id)
    return await build_user_out(service.session, user)


@router.patch(
    "/{user_id}",
    response_model=UserOut,
    summary="Patch full_name / is_active / is_superuser (role changes use /roles/{id}/users)",
)
async def update_user(
    user_id: uuid.UUID,
    payload: UserPatch,
    service: UserServiceDep,
) -> UserOut:
    user = await service.update(
        user_id=user_id,
        full_name=payload.full_name,
        is_active=payload.is_active,
        is_superuser=payload.is_superuser,
    )
    return await build_user_out(service.session, user)
