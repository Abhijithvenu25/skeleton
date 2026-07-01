"""Enquiry ORM model — soft-delete + audit, trigger-assigned `enquiry_no`."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import (
    AuditedSoftDeleteMixin,
    TimestampMixin,
    UUIDPKMixin,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class Enquiry(Base, UUIDPKMixin, TimestampMixin, AuditedSoftDeleteMixin):
    __tablename__ = "enquiries"

    # `enquiry_no` is populated by a Postgres BEFORE INSERT trigger (see
    # 0003_crm_module.py). `server_default=""` keeps NOT NULL satisfied during
    # the brief window before the trigger fires.
    enquiry_no: Mapped[str] = mapped_column(String(32), nullable=False, server_default="")

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    sales_executive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    engineer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    source: Mapped[str] = mapped_column(String(32), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    priority: Mapped[str] = mapped_column(
        String(16), nullable=False, default="medium", server_default="medium"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="enquiry", server_default="enquiry"
    )
    enquiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"Enquiry(id={self.id!r}, enquiry_no={self.enquiry_no!r})"

    @classmethod
    async def get_by_id(cls, session: AsyncSession, enquiry_id: uuid.UUID) -> Enquiry | None:
        from sqlalchemy import select

        return await session.scalar(select(cls).where(cls.id == enquiry_id))
