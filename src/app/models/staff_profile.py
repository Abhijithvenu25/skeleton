"""StaffProfile ORM model — role-specific extension of `users`."""

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
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
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
