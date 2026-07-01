"""StaffProfile schemas.

Roles are N:M and live on `User.roles`, surfaced via `roles: list[RoleOut]`.
Per-user HR-style fields stay on `StaffProfile` itself.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.crm.role import RoleOut


class StaffProfileIn(BaseModel):
    employee_code: str | None = Field(None, max_length=64)
    department: str | None = Field(None, max_length=128)
    phone: str | None = Field(None, max_length=32)
    joined_on: date | None = None


class StaffProfileOut(BaseModel):
    user_id: uuid.UUID
    employee_code: str | None
    department: str | None
    phone: str | None
    joined_on: date | None
    roles: list[RoleOut] = []
    created_at: datetime
    created_by_id: uuid.UUID
    updated_at: datetime
    updated_by_id: uuid.UUID | None = None
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class StaffProfilePatch(BaseModel):
    employee_code: str | None = Field(None, max_length=64)
    department: str | None = Field(None, max_length=128)
    phone: str | None = Field(None, max_length=32)
    joined_on: date | None = None


class StaffProfileUpdate(StaffProfilePatch):
    pass


# --- Role assignment (replaces the old singular role_id on the profile) ----


class UserRolesIn(BaseModel):
    """Replace the user's roles with this exact set (any missing grants
    are removed, any new grants are added). At least one role required."""

    role_ids: list[uuid.UUID] = Field(min_length=1)


class UserRolesOut(BaseModel):
    roles: list[RoleOut]
