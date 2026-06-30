"""SiteVisit schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.crm.enums import SiteVisitStatus


class SiteVisitIn(BaseModel):
    enquiry_id: uuid.UUID
    scheduled_at: datetime
    completed_at: datetime | None = None
    engineer_id: uuid.UUID
    sales_executive_id: uuid.UUID
    status: SiteVisitStatus = SiteVisitStatus.SCHEDULED
    notes: str | None = None


class SiteVisitOut(BaseModel):
    id: uuid.UUID
    visit_no: str
    enquiry_id: uuid.UUID
    scheduled_at: datetime
    completed_at: datetime | None = None
    engineer_id: uuid.UUID
    sales_executive_id: uuid.UUID
    status: str
    notes: str | None = None
    created_at: datetime
    created_by_id: uuid.UUID
    updated_at: datetime
    updated_by_id: uuid.UUID | None = None
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SiteVisitPatch(BaseModel):
    scheduled_at: datetime | None = None
    completed_at: datetime | None = None
    engineer_id: uuid.UUID | None = None
    status: SiteVisitStatus | None = None
    notes: str | None = None


class SiteVisitUpdate(SiteVisitPatch):
    pass
