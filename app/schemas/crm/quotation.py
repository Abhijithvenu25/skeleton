"""Quotation schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.crm.enums import QuotationStatus


class QuotationIn(BaseModel):
    enquiry_id: uuid.UUID


class QuotationOut(BaseModel):
    id: uuid.UUID
    quote_no: str
    enquiry_id: uuid.UUID
    current_version_no: int
    sent_date: date | None = None
    status: str
    created_at: datetime
    created_by_id: uuid.UUID
    updated_at: datetime
    updated_by_id: uuid.UUID | None = None
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class QuotationPatch(BaseModel):
    sent_date: date | None = None
    status: QuotationStatus | None = None


class QuotationUpdate(QuotationPatch):
    pass
