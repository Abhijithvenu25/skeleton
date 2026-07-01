"""Shared helpers for CRM services."""

from __future__ import annotations

import math
from typing import Any, TypeVar

from app.models.base import _utcnow  # re-use the mixin's clock
from app.models.user import User
from app.schemas.common import Page
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Audit helpers — call these from each service's create / update / soft_delete
# instead of writing the same `model.created_by_id = actor.id` everywhere.
# ---------------------------------------------------------------------------


def apply_audit_create(model: Any, *, actor: User) -> None:
    """Set created_by_id and updated_by_id on a freshly-created row."""
    model.created_by_id = actor.id
    model.updated_by_id = actor.id


def apply_audit_update(model: Any, *, actor: User) -> None:
    """Set updated_by_id on an updated row."""
    model.updated_by_id = actor.id


def apply_audit_soft_delete(model: Any, *, actor: User) -> None:
    """Set deleted_at + deleted_by_id on a soft-delete row."""
    model.deleted_at = _utcnow()
    model.deleted_by_id = actor.id


# ---------------------------------------------------------------------------
# Pagination helpers
# ---------------------------------------------------------------------------


def build_page(items: list[Any], total: int, page: int, size: int) -> Page[Any]:
    """Wrap (items, total, page, size) in a Page[...], computing pages."""
    pages = max(1, math.ceil(total / size)) if size else 1
    return Page(items=items, total=total, page=page, size=size, pages=pages)


async def paginate(
    session: AsyncSession,
    model: type[T],
    *,
    page: int,
    size: int,
    order_by: Any,
    where: Any | None = None,
) -> tuple[list[T], int]:
    """Standard offset-pagination: returns (items, total) for the given model.

    `where` is an optional list of SQLAlchemy expressions to AND together
    (e.g. `Model.deleted_at.is_(None)`).
    """
    offset = (page - 1) * size
    stmt_items = select(model).order_by(order_by)
    stmt_count = select(func.count(model.id))
    if where is not None:
        stmt_items = stmt_items.where(*where) if isinstance(where, list) else stmt_items.where(where)
        stmt_count = stmt_count.where(*where) if isinstance(where, list) else stmt_count.where(where)
    items = list((await session.execute(stmt_items.offset(offset).limit(size))).scalars())
    total = (await session.scalar(stmt_count)) or 0
    return items, int(total)
