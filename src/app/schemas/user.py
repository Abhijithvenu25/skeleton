"""User schema (match AuthMeOut, but scoped for admin operations if added)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.common import MessageResponse

if TYPE_CHECKING:
    from datetime import datetime


class UserIn(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=255)
    full_name: str | None = Field(None, max_length=255)


class UserOut(BaseModel):
    id: str = Field(..., description="UUID string")
    email: EmailStr
    full_name: str | None = None
    is_active: bool
    is_superuser: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserPatch(BaseModel):
    full_name: str | None = Field(None, max_length=255)
    is_active: bool | None = None


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
