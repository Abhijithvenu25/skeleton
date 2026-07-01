"""Role schemas.

Name normalization (lowercase + strip) is enforced by RoleService, not
here, so the rule lives at the persistence boundary and can't be
bypassed by a future code path that skips these schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RoleIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    permissions: dict[str, Any] | None = None  # None -> {} in service


class RolePatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    permissions: dict[str, Any] | None = None


class RoleOut(BaseModel):
    id: uuid.UUID
    name: str
    permissions: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleAssignIn(BaseModel):
    user_id: uuid.UUID
    # Optional audit-trail field. The endpoint is public (superadmin-only in
    # the frontend), so callers may pass the granting user's id here.
    # Leave null when the grant isn't attributable to any user.
    granted_by_id: uuid.UUID | None = None


class UserRoleOut(BaseModel):
    user_id: uuid.UUID
    role_id: uuid.UUID
    granted_at: datetime
    granted_by_id: uuid.UUID | None

    model_config = ConfigDict(from_attributes=True)
