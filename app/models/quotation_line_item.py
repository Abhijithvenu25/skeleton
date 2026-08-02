import uuid
from typing import TYPE_CHECKING
from sqlalchemy import String, Numeric, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.base import UUIDPKMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.quotation import Quotation


class QuotationLineItem(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "quotation_line_items"

    quotation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), default=1)
    unit: Mapped[str | None] = mapped_column(String(50))
    rate: Mapped[float] = mapped_column(Numeric(12, 3), default=0)
    amount: Mapped[float] = mapped_column(Numeric(12, 3), default=0)
    estimated_cost: Mapped[float | None] = mapped_column(Numeric(12, 3), default=0)
    profit_estimator: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    quotation: Mapped["Quotation"] = relationship("Quotation", back_populates="line_items")
