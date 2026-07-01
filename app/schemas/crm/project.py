"""Project schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.crm.enums import ProjectType


class ProjectIn(BaseModel):
    company_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=255)
    project_type: ProjectType
    location: str | None = Field(None, max_length=255)
    description: str | None = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    project_type: str
    location: str | None = None
    description: str | None = None
    created_at: datetime
    created_by_id: uuid.UUID
    updated_at: datetime
    updated_by_id: uuid.UUID | None = None
    deleted_at: datetime | None = None
    deleted_by_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class ProjectPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    project_type: ProjectType | None = None
    location: str | None = Field(None, max_length=255)
    description: str | None = None


class ProjectUpdate(ProjectPatch):
    pass
