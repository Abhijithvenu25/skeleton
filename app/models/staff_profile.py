"""StaffProfile ORM model — per-user staff metadata, no longer carries role.

Roles are now N:M via the `user_roles` junction table; see `User.roles`.
This table holds per-user HR-style fields only.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import AuditMixin, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class StaffProfile(Base, AuditMixin, SoftDeleteMixin, TimestampMixin):
    """PK is `user_id` (1:1 with users), so we don't apply UUIDPKMixin here."""

    __tablename__ = "staff_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    employee_code: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    department: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    joined_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    def __repr__(self) -> str:
        return f"StaffProfile(user_id={self.user_id!r}, employee_code={self.employee_code!r})"

    @classmethod
    async def get_by_user_id(cls, session: AsyncSession, user_id: uuid.UUID) -> StaffProfile | None:
        from sqlalchemy import select

        return await session.scalar(select(cls).where(cls.user_id == user_id))

    @classmethod
    async def exists_by_employee_code(
        cls,
        session: AsyncSession,
        employee_code: str,
        *,
        exclude_user_id: uuid.UUID | None = None,
    ) -> bool:
        """Pre-check used by StaffProfileService.create/update. Excludes
        `exclude_user_id` so an UPDATE that re-uses the same employee_code
        doesn't false-positive."""
        from sqlalchemy import select

        stmt = select(cls.user_id).where(cls.employee_code == employee_code)
        if exclude_user_id is not None:
            stmt = stmt.where(cls.user_id != exclude_user_id)
        return (await session.scalar(stmt)) is not None
