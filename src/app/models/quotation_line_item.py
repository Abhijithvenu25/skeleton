"""QuotationLineItem ORM model — line breakdown of a quotation version."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import AuditMixin, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class QuotationLineItem(Base, UUIDPKMixin, TimestampMixin, AuditMixin):
    __tablename__ = "quotation_line_items"

    quotation_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quotation_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_type: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    line_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    def __repr__(self) -> str:
        return f"QuotationLineItem(id={self.id!r}, line_total={self.line_total!r})"

    @classmethod
    async def get_by_id(
        cls, session: AsyncSession, line_id: uuid.UUID
    ) -> QuotationLineItem | None:
        from sqlalchemy import select

        return await session.scalar(select(cls).where(cls.id == line_id))
