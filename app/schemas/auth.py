"""Authentication API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserIn(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=255)
    full_name: str | None = Field(None, max_length=255)


class UserOut(BaseModel):
    id: uuid.UUID = Field(..., description="User UUID")
    email: EmailStr
    full_name: str | None = None
    phone: str | None = None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    roles: list[str] = Field(default_factory=list)

    @field_validator("roles", mode="before")
    @classmethod
    def extract_role_names(cls, v: Any) -> list[str]:
        if not isinstance(v, list):
            return []
        res = []
        for r in v:
            if hasattr(r, "name"):
                res.append(r.name)
            elif isinstance(r, str):
                res.append(r)
        return res

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
