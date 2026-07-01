"""Contact schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ContactIn(BaseModel):
    company_id: uuid.UUID
    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr | None = None
    mobile: str | None = Field(None, max_length=32)
    designation: str | None = Field(None, max_length=128)
    is_primary: bool = False


class ContactOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    full_name: str
    email: str | None = None
    mobile: str | None = None
    designation: str | None = None
    is_primary: bool
    created_at: datetime
    created_by_id: uuid.UUID
    updated_at: datetime
    updated_by_id: uuid.UUID | None = None
    deleted_at: datetime | None = None
    deleted_by_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class ContactPatch(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)
    email: EmailStr | None = None
    mobile: str | None = Field(None, max_length=32)
    designation: str | None = Field(None, max_length=128)
    is_primary: bool | None = None
