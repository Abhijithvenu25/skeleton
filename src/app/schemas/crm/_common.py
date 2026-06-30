"""Shared CRM schema bits."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuditFields(BaseModel):
    """Audit columns exposed by every CRM resource's Out schema."""

    created_at: datetime
    updated_at: datetime
    created_by_id: uuid.UUID
    updated_by_id: uuid.UUID | None = None


class ORMBase(BaseModel):
    """Reusable config so all CRM Out schemas can do `from_attributes=True`."""

    model_config = ConfigDict(from_attributes=True)


class IdOut(ORMBase):
    """Minimal shape for endpoints that just return the new id."""

    id: uuid.UUID = Field(..., description="UUID of the created row")
