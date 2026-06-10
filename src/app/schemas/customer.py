"""Customer API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.common import Page


class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=32)
    company: str | None = Field(None, max_length=255)
    notes: str | None = None


class CustomerIn(CustomerBase):
    pass


class CustomerPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=32)
    company: str | None = Field(None, max_length=255)
    notes: str | None = None


class CustomerUpdate(CustomerPatch):
    pass


class CustomerOut(CustomerBase):
    id: uuid.UUID = Field(..., description="Customer UUID")
    owner_id: uuid.UUID = Field(..., description="Owning user UUID")
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CustomerPage(Page[CustomerOut]):
    pass  # explicit OpenAPI schema for the paginated response


class CustomerPatchIn(CustomerPatch):
    pass


class CustomerUpdateIn(CustomerUpdate):
    pass
