"""User schemas — admin CRUD shape (public, superadmin-only in the UI).

`app.schemas.auth.UserOut` is the auth-flow shape used by /auth/me and
/auth/register responses. The two `UserOut`s differ on `id` typing
(str here, uuid.UUID there) and on whether they expose role info
(this one does, since it powers admin user-management views).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.common import MessageResponse, Page


class UserRoleBrief(BaseModel):
    """Embedded role representation in UserOut."""

    role_id: uuid.UUID
    role_name: str
    role_code: str

    model_config = ConfigDict(from_attributes=True)


class UserIn(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=255)
    full_name: str | None = Field(None, max_length=255)


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None
    phone: str | None = None
    user_image: str | None = None
    is_active: bool
    is_superuser: bool
    created_at: datetime

    # Role grants from the N:M junction. The frontend reads role_id /
    # role_name / role_code from each entry — there's no separate
    # "primary role" field at the top level.
    roles: list[UserRoleBrief] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    """Admin-style create payload. Distinct from auth.RegisterIn which
    is self-service and doesn't accept role/is_superuser."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=255)
    full_name: str | None = Field(None, max_length=255)
    user_image: str | None = Field(None, max_length=2048)
    is_active: bool = True
    is_superuser: bool = False
    # `role_ids` (plural) lets an admin grant multiple roles at create
    # time. Empty list / null means no grants. The service rejects
    # duplicate ids with 400; non-existent ids return 404.
    role_ids: list[uuid.UUID] = Field(default_factory=list, max_length=64)


class UserList(Page[UserOut]):
    """Alias for OpenAPI clarity."""


class UserPatch(BaseModel):
    full_name: str | None = Field(None, max_length=255)
    user_image: str | None = Field(None, max_length=2048)
    is_active: bool | None = None
    is_superuser: bool | None = None


class UserUpdate(UserPatch):
    email: EmailStr | None = None


class PasswordChange(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=255)
    new_password: str = Field(..., min_length=8, max_length=255)


class PasswordReset(BaseModel):
    token: str = Field(..., min_length=1, max_length=255)
    new_password: str = Field(..., min_length=8, max_length=255)


class DeleteUserOut(MessageResponse):
    pass
