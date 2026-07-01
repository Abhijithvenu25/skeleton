"""Quotation ORM model — audit + cascade-delete from enquiry."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import AuditMixin, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class Quotation(Base, UUIDPKMixin, TimestampMixin, AuditMixin):
    __tablename__ = "quotations"

    # Trigger-assigned (QT-001 etc.). `server_default=""` keeps NOT NULL satisfied
    # during the brief window before the trigger fires.
    quote_no: Mapped[str] = mapped_column(String(32), nullable=False, server_default="")

    enquiry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enquiries.id", ondelete="CASCADE"),
        nullable=False,
    )
    current_version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    sent_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="draft", server_default="draft"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"Quotation(id={self.id!r}, quote_no={self.quote_no!r})"

    @classmethod
    async def get_by_id(cls, session: AsyncSession, quotation_id: uuid.UUID) -> Quotation | None:
        from sqlalchemy import select

        return await session.scalar(select(cls).where(cls.id == quotation_id))
