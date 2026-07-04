from __future__ import annotations

import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.common import Page

class ProjectTypeCreate(BaseModel):
    type_name: str = Field(..., max_length=255)
    description: str | None = Field(None, max_length=500)

class ProjectTypePatch(BaseModel):
    type_name: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=500)

class ProjectTypeOut(BaseModel):
    id: uuid.UUID
    type_name: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)

class ProjectTypeList(Page[ProjectTypeOut]):
    pass
