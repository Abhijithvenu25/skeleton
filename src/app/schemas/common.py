"""Common API schemas."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class MessageResponse(BaseModel):
    message: str = Field(..., min_length=1, max_length=255)


class ErrorResponse(BaseModel):
    code: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1, max_length=255)
    details: dict[str, object] | None = None


class Page(BaseModel, Generic[T]):
    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    size: int = Field(..., ge=1, le=100)
    pages: int = Field(..., ge=1)
