"""Project ORM model — soft-delete + audit."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
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


class Project(Base, UUIDPKMixin, TimestampMixin, AuditedSoftDeleteMixin):
    __tablename__ = "projects"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    project_type: Mapped[str] = mapped_column(String(32), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"Project(id={self.id!r}, name={self.name!r})"

    @classmethod
    async def get_by_id(cls, session: AsyncSession, project_id: uuid.UUID) -> Project | None:
        from sqlalchemy import select

        return await session.scalar(select(cls).where(cls.id == project_id))
