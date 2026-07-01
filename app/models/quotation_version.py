"""QuotationVersion ORM model — append-only history.

Versions are immutable: only `created_at` (ImmutableMixin) and `created_by_id`
(AuditMixin) — no `updated_at` and no `updated_by_id`.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import ImmutableMixin, UUIDPKMixin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class QuotationVersion(Base, UUIDPKMixin, ImmutableMixin):
    __tablename__ = "quotation_versions"

    quotation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quotations.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"QuotationVersion(id={self.id!r}, version_no={self.version_no!r})"

    @classmethod
    async def exists_for_quotation(
        cls,
        session: AsyncSession,
        *,
        quotation_id: uuid.UUID,
        version_no: int,
    ) -> bool:
        """Pre-check used by QuotationService.add_version to surface a 409
        on the (quotation_id, version_no) unique constraint without relying
        on IntegrityError catching."""
        from sqlalchemy import select

        return (
            await session.scalar(
                select(cls.id).where(
                    cls.quotation_id == quotation_id,
                    cls.version_no == version_no,
                )
            )
        ) is not None
