"""LostEnquiry ORM model — terminal state record for a lost enquiry.

Cascade-only: no `deleted_at` column. The row exists iff the related enquiry
exists (hard-delete cascade).
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import AuditMixin, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class LostEnquiry(Base, UUIDPKMixin, TimestampMixin, AuditMixin):
    __tablename__ = "lost_enquiries"

    enquiry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enquiries.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    stage_lost: Mapped[str] = mapped_column(String(16), nullable=False)
    reason_lost: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_lost: Mapped[date] = mapped_column(Date, nullable=False)
    follow_up_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"LostEnquiry(enquiry_id={self.enquiry_id!r}, stage_lost={self.stage_lost!r})"

    @classmethod
    async def get_by_enquiry_id(
        cls, session: AsyncSession, enquiry_id: uuid.UUID
    ) -> LostEnquiry | None:
        from sqlalchemy import select

        return await session.scalar(select(cls).where(cls.enquiry_id == enquiry_id))
