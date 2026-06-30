"""QuotationVersion schemas (with inline line items)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.crm.enums import LineItemType


class QuotationLineItemIn(BaseModel):
    line_type: LineItemType
    description: str = Field(..., min_length=1, max_length=255)
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    sort_order: int = 0


class QuotationVersionIn(BaseModel):
    terms: str | None = None
    file_url: str | None = Field(None, max_length=512)
    line_items: list[QuotationLineItemIn] = Field(default_factory=list)


class QuotationVersionOut(BaseModel):
    id: uuid.UUID
    quotation_id: uuid.UUID
    version_no: int
    amount: Decimal
    terms: str | None = None
    file_url: str | None = None
    created_by_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuotationLineItemOut(BaseModel):
    id: uuid.UUID
    quotation_version_id: uuid.UUID
    line_type: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    sort_order: int
    created_at: datetime
    created_by_id: uuid.UUID
    updated_at: datetime
    updated_by_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)
