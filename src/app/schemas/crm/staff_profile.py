"""StaffProfile schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class StaffProfileIn(BaseModel):
    role_id: uuid.UUID
    employee_code: str | None = Field(None, max_length=64)
    department: str | None = Field(None, max_length=128)
    phone: str | None = Field(None, max_length=32)
    joined_on: date | None = None


class StaffProfileOut(BaseModel):
    user_id: uuid.UUID
    role_id: uuid.UUID
    employee_code: str | None
    department: str | None
    phone: str | None
    joined_on: date | None
    created_at: datetime
    created_by_id: uuid.UUID
    updated_at: datetime
    updated_by_id: uuid.UUID | None = None
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class StaffProfilePatch(BaseModel):
    role_id: uuid.UUID | None = None
    employee_code: str | None = Field(None, max_length=64)
    department: str | None = Field(None, max_length=128)
    phone: str | None = Field(None, max_length=32)
    joined_on: date | None = None


class StaffProfileUpdate(StaffProfilePatch):
    pass
