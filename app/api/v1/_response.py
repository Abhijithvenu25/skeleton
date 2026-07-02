"""Response-envelope factories.

Plain functions that turn handler results into the common
`ApiResponse[T]` shape. Generic over the inner model so FastAPI can
resolve `response_model=ApiResponse[RoleOut]` for OpenAPI docs.

Status-code mapping convention (mirrors HTTP semantics):
- `ok_single`        → 200 (single-resource GET by id, PATCH, etc.)
- `ok_list`          → 200 (paginated GET)
- `created_single`   → 201 (POST create)

DELETE endpoints keep status 204 with an empty body — no envelope.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import TypeVar

from pydantic import BaseModel

from app.schemas.common import ApiResponse, PaginationInfo

T = TypeVar("T", bound=BaseModel)


def _build_pagination(*, page: int, size: int, total: int) -> PaginationInfo:
    """Compute PaginationInfo from raw page/size/total.

    - `total_pages` is `ceil(total / size)` for non-zero totals, else 0
      ("empty list, no pages" semantics).
    - `has_next` is true only when more pages exist after the current one.
    - `has_previous` is true only when at least one page precedes the
      current one.
    """
    total_pages = math.ceil(total / size) if total else 0
    return PaginationInfo(
        current_page=page,
        total_pages=total_pages,
        total_records=total,
        has_next=page < total_pages,
        has_previous=page > 1,
    )


def ok_single[T: BaseModel](item: T, message: str) -> ApiResponse[T]:
    """Wrap a single resource as a one-element list.

    Caller passes the materialized `T` (e.g. `RoleOut.model_validate(role)`).
    """
    return ApiResponse[T](
        status=200,
        message=message,
        data=[item],
        pagination=None,
    )


def ok_list[T: BaseModel](
    items: Sequence[T],
    *,
    page: int,
    size: int,
    total: int,
    message: str,
) -> ApiResponse[T]:
    """Wrap a list resource with pagination metadata."""
    return ApiResponse[T](
        status=200,
        message=message,
        data=list(items),
        pagination=_build_pagination(page=page, size=size, total=total),
    )


def created_single[T: BaseModel](item: T, message: str) -> ApiResponse[T]:
    """Same shape as `ok_single` but with status 201 for POST creates."""
    return ApiResponse[T](
        status=201,
        message=message,
        data=[item],
        pagination=None,
    )
