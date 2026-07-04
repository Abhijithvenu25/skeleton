import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.base import UUIDPKMixin, TimestampMixin
from app.models.enums import SiteVisitStatus

if TYPE_CHECKING:
    from app.models.enquiry import Enquiry
    from app.models.company import Company
    from app.models.user import User
    from app.models.attachment import Attachment

class SiteVisit(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "site_visits"

    visit_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    enquiry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("enquiries.id"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company.id"), nullable=False)
    engineer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    sales_executive_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    visit_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[SiteVisitStatus] = mapped_column(SAEnum(SiteVisitStatus), default=SiteVisitStatus.scheduled)
    notes: Mapped[str | None] = mapped_column(Text)

    enquiry: Mapped["Enquiry"] = relationship("Enquiry", back_populates="site_visits")
    company: Mapped["Company"] = relationship("Company", back_populates="site_visits")
    engineer: Mapped["User"] = relationship("User", back_populates="engineered_visits", foreign_keys="SiteVisit.engineer_id")
    sales_executive: Mapped["User"] = relationship("User", back_populates="executive_visits", foreign_keys="SiteVisit.sales_executive_id")
    attachments: Mapped[list["Attachment"]] = relationship("Attachment", back_populates="site_visit")
