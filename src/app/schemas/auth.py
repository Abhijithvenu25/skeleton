"""Authentication API schemas."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

if TYPE_CHECKING:
    import uuid
    from datetime import datetime


class UserIn(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=255)
    full_name: str | None = Field(None, max_length=255)


class UserOut(BaseModel):
    id: uuid.UUID = Field(..., description="User UUID")
    email: EmailStr
    full_name: str | None = None
    is_active: bool
    is_superuser: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RegisterIn(UserIn):
    @field_validator("password")
    @classmethod
    def _valid_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class RegisterOut(UserOut):
    pass


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=255)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105


class RefreshIn(BaseModel):
    refresh_token: str


class RefreshOut(TokenPair):
    pass


class AuthOut(BaseModel):
    user: UserOut
    token: TokenPair


AuthMeOut = UserOut  # alias for OpenAPI / clarity
