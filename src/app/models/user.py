"""User ORM model with query helpers."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from sqlalchemy import select as _select  # noqa: F401  (typing only)


class User(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, email={self.email!r})"

    # ---- Query helpers (classmethods) ---------------------------------------

    @classmethod
    async def get_by_id(cls, session: AsyncSession, user_id: uuid.UUID) -> User | None:
        """Fetch a user by primary key."""
        from sqlalchemy import select

        return await session.scalar(select(cls).where(cls.id == user_id))

    @classmethod
    async def get_by_email(cls, session: AsyncSession, email: str) -> User | None:
        """Fetch a user by email (case-insensitive)."""
        from sqlalchemy import select

        return await session.scalar(select(cls).where(cls.email == email.lower()))

    @classmethod
    async def email_exists(cls, session: AsyncSession, email: str) -> bool:
        """Return True if a user with the given email already exists."""
        from sqlalchemy import select

        result = await session.scalar(select(cls.id).where(cls.email == email.lower()))
        return result is not None
