"""Enquiry schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.crm.enums import (
    EnquiryPriority,
    EnquirySource,
    EnquiryStatus,
)


class EnquiryIn(BaseModel):
    company_id: uuid.UUID
    contact_id: uuid.UUID
    project_id: uuid.UUID | None = None
    sales_executive_id: uuid.UUID
    engineer_id: uuid.UUID | None = None
    source: EnquirySource
    location: str | None = Field(None, max_length=255)
    priority: EnquiryPriority = EnquiryPriority.MEDIUM
    enquiry_date: date | None = None  # defaults to today in service if None
    notes: str | None = None


class EnquiryOut(BaseModel):
    id: uuid.UUID
    enquiry_no: str
    company_id: uuid.UUID
    contact_id: uuid.UUID
    project_id: uuid.UUID | None = None
    sales_executive_id: uuid.UUID
    engineer_id: uuid.UUID | None = None
    source: str
    location: str | None = None
    priority: str
    status: str
    enquiry_date: date
    notes: str | None = None
    created_at: datetime
    created_by_id: uuid.UUID
    updated_at: datetime
    updated_by_id: uuid.UUID | None = None
    deleted_at: datetime | None = None
    deleted_by_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class EnquiryPatch(BaseModel):
    project_id: uuid.UUID | None = None
    engineer_id: uuid.UUID | None = None
    source: EnquirySource | None = None
    location: str | None = Field(None, max_length=255)
    priority: EnquiryPriority | None = None
    status: EnquiryStatus | None = None
    notes: str | None = None


class EnquiryUpdate(EnquiryPatch):
    pass


class MarkLostIn(BaseModel):
    stage_lost: EnquiryStatus  # only enquiry/site_visit/quotation are valid stages
    reason_lost: str | None = None
    follow_up_date: date | None = None
    notes: str | None = None
