"""Customer ORM model (FK to User) with query helpers."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, func, or_
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.user import User
    from sqlalchemy import select as _select  # noqa: F401  (typing only)


class Customer(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "customers"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(CITEXT(), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped[User] = relationship("User", lazy="joined")

    __table_args__ = (
        Index(
            "ix_customers_active_name",
            "name",
            postgresql_where=(deleted_at.is_(None)),
        ),
    )

    def __repr__(self) -> str:
        return f"Customer(id={self.id!r}, name={self.name!r})"

    # ---- Query helpers (classmethods) ---------------------------------------

    @classmethod
    async def get_by_id(cls, session: AsyncSession, customer_id: uuid.UUID) -> Customer | None:
        """Fetch a customer by primary key, excluding soft-deleted ones."""
        from sqlalchemy import select

        return await session.scalar(
            select(cls).where(cls.id == customer_id, cls.deleted_at.is_(None))
        )

    @classmethod
    async def count_by_owner(
        cls,
        session: AsyncSession,
        owner_id: uuid.UUID,
        *,
        include_deleted: bool = False,
    ) -> int:
        """Count customers for a given owner."""
        from sqlalchemy import select, func

        stmt = select(func.count(cls.id)).where(cls.owner_id == owner_id)
        if not include_deleted:
            stmt = stmt.where(cls.deleted_at.is_(None))
        return (await session.scalar(stmt)) or 0

    @classmethod
    async def search_by_owner(
        cls,
        session: AsyncSession,
        owner_id: uuid.UUID,
        *,
        query: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Customer], int]:
        """Search customers by owner, with optional search query, pagination."""
        from sqlalchemy import select, func

        count_stmt = select(func.count(cls.id)).where(cls.owner_id == owner_id)
        stmt = select(cls).where(cls.owner_id == owner_id)

        # Exclude soft-deleted by default
        stmt = stmt.where(cls.deleted_at.is_(None))
        count_stmt = count_stmt.where(cls.deleted_at.is_(None))

        # Apply search filters if provided
        if query:
            pattern = f"%{query.lower()}%"
            search_filters = [
                func.lower(cls.name).like(pattern),
                func.lower(func.coalesce(cls.email, "")).like(pattern),
                func.lower(func.coalesce(cls.company, "")).like(pattern),
                func.coalesce(cls.phone, "").like(query),
            ]
            stmt = stmt.where(or_(*search_filters))
            count_stmt = count_stmt.where(or_(*search_filters))

        # Add pagination
        stmt = stmt.order_by(cls.created_at.desc()).offset(offset).limit(limit)

        # Execute both queries
        result = await session.execute(stmt)
        items = list(result.scalars().unique().all())
        total = await session.scalar(count_stmt) or 0

        return items, total

    @classmethod
    async def update_by_id(
        cls,
        session: AsyncSession,
        customer_id: uuid.UUID,
        **kwargs,
    ) -> Customer | None:
        """Update a customer by ID. Returns updated customer if found and updated."""
        customer = await cls.get_by_id(session, customer_id)
        if customer is None:
            return None

        for key, value in kwargs.items():
            if hasattr(customer, key):
                setattr(customer, key, value)
        await session.commit()
        return customer

    @classmethod
    async def soft_delete_by_id(cls, session: AsyncSession, customer_id: uuid.UUID) -> bool:
        """Soft-delete a customer by ID. Returns True if found and updated."""
        customer = await cls.get_by_id(session, customer_id)
        if customer is None:
            return False

        customer.deleted_at = datetime.now()
        await session.commit()
        return True

    @classmethod
    async def get_customers_by_owner(
        cls,
        session: AsyncSession,
        owner_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Customer], int]:
        """List paginated customers for an owner, not including deleted."""
        from sqlalchemy import select, func

        count_stmt = select(func.count(cls.id)).where(
            cls.owner_id == owner_id, cls.deleted_at.is_(None)
        )
        stmt = (
            select(cls)
            .where(cls.owner_id == owner_id, cls.deleted_at.is_(None))
            .order_by(cls.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await session.execute(stmt)
        items = list(result.scalars().unique().all())
        total = await session.scalar(count_stmt) or 0

        return items, total