"""Role schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.crm.enums import RoleName


class RoleIn(BaseModel):
    name: str
    permissions: dict[str, Any] = Field(default_factory=dict)


class RoleOut(BaseModel):
    id: uuid.UUID
    name: str
    permissions: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RolePatch(BaseModel):
    name: str | None = None
    permissions: dict[str, Any] | None = None


class RoleUpdate(RolePatch):
    pass
