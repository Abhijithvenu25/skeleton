from datetime import datetime
import uuid
from typing import TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
from app.models.base import UUIDPKMixin, ImmutableMixin
from app.models.enums import EnquiryAuditAction

if TYPE_CHECKING:
    from app.models.enquiry import Enquiry

class EnquiryAuditLog(Base, UUIDPKMixin, ImmutableMixin):
    __tablename__ = "enquiry_audit_log"

    enquiry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enquiry.id", ondelete="CASCADE"),
        nullable=False,
    )
    action: Mapped[EnquiryAuditAction] = mapped_column(
        SQLAlchemyEnum(EnquiryAuditAction),
        nullable=False,
    )
    action_date: Mapped[datetime] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    enquiry: Mapped["Enquiry"] = relationship("Enquiry", back_populates="audit_logs")
