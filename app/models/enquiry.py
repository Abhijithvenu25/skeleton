import uuid
from datetime import date
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, Date, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.base import UUIDPKMixin, TimestampMixin, SoftDeleteMixin
from app.models.enums import EnquirySource, EnquiryPriority, EnquiryStatus

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.client import Client
    from app.models.project import Project
    from app.models.user import User
    from app.models.site_visit import SiteVisit
    from app.models.quotation import Quotation
    from app.models.audit_log import EnquiryAuditLog
    from app.models.attachment import Attachment

class Enquiry(Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "enquiries"

    enquiry_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    enquiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company.id"), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"))
    enquiry_source: Mapped[EnquirySource | None] = mapped_column(SAEnum(EnquirySource))
    priority: Mapped[EnquiryPriority] = mapped_column(SAEnum(EnquiryPriority), default=EnquiryPriority.medium)
    status: Mapped[EnquiryStatus] = mapped_column(SAEnum(EnquiryStatus), default=EnquiryStatus.enquiry)
    sales_executive_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    description: Mapped[str | None] = mapped_column(Text)
    remarks: Mapped[str | None] = mapped_column(Text)

    stage_lost: Mapped[str | None] = mapped_column(String(100))
    lost_reason: Mapped[str | None] = mapped_column(String(500))
    date_lost: Mapped[date | None] = mapped_column(Date)
    follow_up_date: Mapped[date | None] = mapped_column(Date)
    reinstated: Mapped[bool] = mapped_column(Boolean, default=False)

    company: Mapped["Company"] = relationship("Company", back_populates="enquiries")
    client: Mapped["Client"] = relationship("Client", back_populates="enquiries")
    project: Mapped["Project"] = relationship("Project", back_populates="enquiry")
    sales_executive: Mapped["User"] = relationship("User", back_populates="enquiries", foreign_keys="Enquiry.sales_executive_id")
    site_visits: Mapped[list["SiteVisit"]] = relationship("SiteVisit", back_populates="enquiry")
    quotations: Mapped[list["Quotation"]] = relationship("Quotation", back_populates="enquiry")
    audit_logs: Mapped[list["EnquiryAuditLog"]] = relationship(
        "EnquiryAuditLog", back_populates="enquiry", cascade="all, delete-orphan", order_by="desc(EnquiryAuditLog.created_at)"
    )
    attachments: Mapped[list["Attachment"]] = relationship("Attachment", back_populates="enquiry")
