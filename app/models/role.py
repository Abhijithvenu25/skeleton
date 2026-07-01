"""Role ORM model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from sqlalchemy import select as _select  # noqa: F401  (typing only)
    from sqlalchemy.ext.asyncio import AsyncSession


class Role(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    permissions: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    def __repr__(self) -> str:
        return f"Role(id={self.id!r}, name={self.name!r})"

    @classmethod
    async def get_by_id(cls, session: AsyncSession, role_id: uuid.UUID) -> Role | None:
        from sqlalchemy import select

        return await session.scalar(select(cls).where(cls.id == role_id))

    @classmethod
    async def get_by_name(cls, session: AsyncSession, name: str) -> Role | None:
        from sqlalchemy import select

        return await session.scalar(select(cls).where(cls.name == name))
