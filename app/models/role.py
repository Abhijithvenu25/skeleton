"""Role ORM model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class Role(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    permissions: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    # Business code in the form `R-1`, `R-2`, ... Assigned by the service
    # on insert (see RoleService.create). The UNIQUE constraint is what
    # actually guarantees no collisions under concurrent inserts.
    role_code: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Explicit unique index under the project's NAMING_CONVENTION so the
    # global IntegrityError handler can map `uq_roles_role_code` collisions
    # to a clean 409. (Declared here rather than via `unique=True` on the
    # column so the constraint name is deterministic across migrations.)
    __table_args__ = (Index("uq_roles_role_code", "role_code", unique=True),)

    def __repr__(self) -> str:
        return f"Role(id={self.id!r}, code={self.role_code!r}, name={self.name!r})"

    @classmethod
    async def get_by_id(cls, session: AsyncSession, role_id: uuid.UUID) -> Role | None:
        from sqlalchemy import select

        result = await session.scalar(select(cls).where(cls.id == role_id))
        return result

    @classmethod
    async def exists_by_name(
        cls, session: AsyncSession, name: str, *, exclude_id: uuid.UUID | None = None
    ) -> bool:
        """Pre-check used by RoleService.create/update to surface 409s without
        relying on IntegrityError catching. Excludes `exclude_id` so an UPDATE
        that re-uses the same name doesn't false-positive."""
        from sqlalchemy import select

        stmt = select(cls.id).where(cls.name == name)
        if exclude_id is not None:
            stmt = stmt.where(cls.id != exclude_id)
        return (await session.scalar(stmt)) is not None

    @classmethod
    async def max_role_code_suffix(cls, session: AsyncSession) -> int:
        """Return the largest numeric suffix in any existing `R-N` code.

        Used by RoleService.create to compute the next code (`max + 1`).
        Returns 0 when the table is empty, so the first role created gets
        `R-1`. Non-conforming codes (legacy rows, manual edits) are
        ignored — the suffix just advances from the highest valid one.
        """
        from sqlalchemy import func, select

        # Split each code on '-' and cast the second segment to int.
        # Non-numeric suffixes sort as NULLs and are excluded by the
        # WHERE filter; this keeps the function tolerant of legacy data.
        suffix = func.split_part(cls.role_code, "-", 2).cast(Integer)
        stmt = select(func.max(suffix)).where(suffix.is_not(None))
        result = await session.scalar(stmt)
        return int(result or 0)
