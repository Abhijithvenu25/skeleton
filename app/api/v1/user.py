"""User CRUD endpoints. Public — no auth required.

Superadmin-only concern in the frontend (UI hidden from non-superadmins);
the API mirrors that trade-off, same as /roles.

All success responses use the common ApiResponse envelope — see
app/schemas/common.py and app/api/v1/_response.py.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status, Form, File, UploadFile
from pydantic import EmailStr

from app.api.deps import DbSession, StorageServiceDep
from app.api.v1._response import created_single, ok_list, ok_single
from app.api.v1._user_response import build_user_out
from app.schemas.common import ApiResponse
from app.schemas.user import UserOut
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
    summary="Admin-style create a user (optionally with multiple roles and an S3 user_image upload)",
)
async def create_user(
    service: UserServiceDep,
    storage_service: StorageServiceDep,
    email: EmailStr = Form(...),
    password: str = Form(..., min_length=8, max_length=255),
    full_name: str | None = Form(None, max_length=255),
    phone: str | None = Form(None, max_length=50),
    is_active: bool = Form(True),
    is_superuser: bool = Form(False),
    is_signature: bool | None = Form(None),
    roles: list[uuid.UUID] = Form(default_factory=list),
    user_image: UploadFile | None = File(None),
    signature_file: UploadFile | None = File(None),
) -> ApiResponse[UserOut]:
    image_url = None
    if user_image:
        stored = await storage_service.upload_uploadfile(file=user_image, category="photos")
        image_url = stored.url

    signature_url = None
    if signature_file:
        stored = await storage_service.upload_uploadfile(file=signature_file, category="photos")
        signature_url = stored.url

    user = await service.create(
        email=email,
        password=password,
        full_name=full_name,
        phone=phone,
        user_image=image_url,
        is_signature=is_signature,
        signature=signature_url,
        is_active=is_active,
        is_superuser=is_superuser,
        role_ids=roles,
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
    summary="Patch email / phone / full_name / user_image / is_active / is_superuser / roles / password",
)
async def update_user(
    user_id: uuid.UUID,
    service: UserServiceDep,
    storage_service: StorageServiceDep,
    email: EmailStr | None = Form(None),
    phone: str | None = Form(None, max_length=50),
    full_name: str | None = Form(None, max_length=255),
    password: str | None = Form(None, min_length=8, max_length=255),
    is_active: bool | None = Form(None),
    is_superuser: bool | None = Form(None),
    is_signature: bool | None = Form(None),
    roles: list[uuid.UUID] | None = Form(None),
    user_image: UploadFile | None = File(None),
    signature: UploadFile | None = File(None),
) -> ApiResponse[UserOut]:
    image_url = None
    if user_image:
        stored = await storage_service.upload_uploadfile(file=user_image, category="photos")
        image_url = stored.url

    signature_url = None
    if signature:
        stored = await storage_service.upload_uploadfile(file=signature, category="photos")
        signature_url = stored.url

    user = await service.update(
        user_id=user_id,
        email=email,
        phone=phone,
        full_name=full_name,
        password=password,
        user_image=image_url,
        is_signature=is_signature,
        signature=signature_url,
        is_active=is_active,
        is_superuser=is_superuser,
        role_ids=roles,
    )
    return ok_single(
        build_user_out(user),
        "user updated successfully.",
    )
