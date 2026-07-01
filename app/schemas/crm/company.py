"""Company schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CompanyIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=32)
    street: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    landmark: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=128)
    state: str | None = Field(None, max_length=128)
    country: str | None = Field(None, max_length=128)
    pin: str | None = Field(None, max_length=20)


class CompanyOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str | None = None
    phone: str | None = None
    street: str | None = None
    address_line2: str | None = None
    landmark: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    pin: str | None = None
    created_at: datetime
    created_by_id: uuid.UUID
    updated_at: datetime
    updated_by_id: uuid.UUID | None = None
    deleted_at: datetime | None = None
    deleted_by_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class CompanyPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=32)
    street: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    landmark: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=128)
    state: str | None = Field(None, max_length=128)
    country: str | None = Field(None, max_length=128)
    pin: str | None = Field(None, max_length=20)
