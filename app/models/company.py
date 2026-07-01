"""Company ORM model — soft-delete + audit."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import (
    AuditedSoftDeleteMixin,
    TimestampMixin,
    UUIDPKMixin,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class Company(Base, UUIDPKMixin, TimestampMixin, AuditedSoftDeleteMixin):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(CITEXT(), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    street: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    landmark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    state: Mapped[str | None] = mapped_column(String(128), nullable=True)
    country: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pin: Mapped[str | None] = mapped_column(String(20), nullable=True)

    def __repr__(self) -> str:
        return f"Company(id={self.id!r}, name={self.name!r})"

    @classmethod
    async def get_by_id(cls, session: AsyncSession, company_id: uuid.UUID) -> Company | None:
        from sqlalchemy import select

        return await session.scalar(select(cls).where(cls.id == company_id))
