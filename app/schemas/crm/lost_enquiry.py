"""LostEnquiry schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.crm.enums import LostStage


class LostEnquiryIn(BaseModel):
    enquiry_id: uuid.UUID
    stage_lost: LostStage
    reason_lost: str | None = None
    follow_up_date: date | None = None
    notes: str | None = None


class LostEnquiryOut(BaseModel):
    id: uuid.UUID
    enquiry_id: uuid.UUID
    stage_lost: str
    reason_lost: str | None = None
    date_lost: date
    follow_up_date: date | None = None
    notes: str | None = None
    created_at: datetime
    created_by_id: uuid.UUID
    updated_at: datetime
    updated_by_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class LostEnquiryPatch(BaseModel):
    reason_lost: str | None = None
    follow_up_date: date | None = None
    notes: str | None = None


class LostEnquiryUpdate(LostEnquiryPatch):
    pass
