"""SiteVisit ORM model — audit + cascade-delete from enquiry."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import AuditMixin, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SiteVisit(Base, UUIDPKMixin, TimestampMixin, AuditMixin):
    __tablename__ = "site_visits"

    # Trigger-assigned (VIS-001 etc.). `server_default=""` keeps NOT NULL satisfied
    # during the brief window before the trigger fires.
    visit_no: Mapped[str] = mapped_column(String(32), nullable=False, server_default="")

    enquiry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enquiries.id", ondelete="CASCADE"),
        nullable=False,
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    engineer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sales_executive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="scheduled", server_default="scheduled"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"SiteVisit(id={self.id!r}, visit_no={self.visit_no!r})"

    @classmethod
    async def get_by_id(cls, session: AsyncSession, visit_id: uuid.UUID) -> SiteVisit | None:
        from sqlalchemy import select

        return await session.scalar(select(cls).where(cls.id == visit_id))
