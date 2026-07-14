import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, Integer, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.base import Base
from app.models.base import UUIDPKMixin
from app.models.enums import AttachmentDocumentType

if TYPE_CHECKING:
    from app.models.enquiry import Enquiry
    from app.models.site_visit import SiteVisit

class Attachment(Base, UUIDPKMixin):
    __tablename__ = "attachments"
    
    file: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255))
    file_type: Mapped[str | None] = mapped_column(String(100))
    document_type: Mapped[AttachmentDocumentType | None] = mapped_column(SAEnum(AttachmentDocumentType))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), server_default=func.now())

    enquiry_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("enquiries.id"))
    site_visit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("site_visits.id"))

    enquiry: Mapped["Enquiry"] = relationship("Enquiry", back_populates="attachments")
    site_visit: Mapped["SiteVisit"] = relationship("SiteVisit", back_populates="attachments")
