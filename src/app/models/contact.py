"""Contact ORM model — soft-delete + audit."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import (
    AuditedSoftDeleteMixin,
    TimestampMixin,
    UUIDPKMixin,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class Contact(Base, UUIDPKMixin, TimestampMixin, AuditedSoftDeleteMixin):
    __tablename__ = "contacts"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(CITEXT(), nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(32), nullable=True)
    designation: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    def __repr__(self) -> str:
        return f"Contact(id={self.id!r}, full_name={self.full_name!r})"

    @classmethod
    async def get_by_id(cls, session: AsyncSession, contact_id: uuid.UUID) -> Contact | None:
        from sqlalchemy import select

        return await session.scalar(select(cls).where(cls.id == contact_id))
