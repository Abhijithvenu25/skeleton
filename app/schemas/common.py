"""Common API schemas."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")
TResponse = TypeVar("TResponse")


class MessageResponse(BaseModel):
    message: str = Field(..., min_length=1, max_length=255)


class ErrorResponse(BaseModel):
    code: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1, max_length=255)
    details: dict[str, object] | None = None


class Page[T](BaseModel):
    """Legacy pagination wrapper — superseded by ApiResponse for role/user
    endpoints; retained as a base class for UserList."""

    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    size: int = Field(..., ge=1, le=100)
    pages: int = Field(..., ge=1)


class PaginationInfo(BaseModel):
    """Pagination metadata for paginated list endpoints."""

    current_page: int = Field(..., ge=1)
    total_pages: int = Field(..., ge=0)
    total_records: int = Field(..., ge=0)
    has_next: bool
    has_previous: bool


class ApiResponse[TResponse](BaseModel):
    """Common success-response envelope.

    Wraps every payload as a list (`data: list[TResponse]`) so client code
    can always iterate `data` regardless of whether the response is a
    single resource or a paginated list. `pagination` is omitted for
    single / non-paginated responses.

    Status mirrors the HTTP status code for client convenience.

    A dedicated `TResponse` TypeVar (rather than reusing the file-level
    `T` from `Page`) is used because Pydantic v2's BaseModel metaclass
    rejects multiple generic ancestors that share a TypeVar instance.
    """

    status: int = Field(..., ge=100, le=599)
    message: str = Field(..., min_length=1, max_length=255)
    data: list[TResponse]
    pagination: PaginationInfo | None = None
