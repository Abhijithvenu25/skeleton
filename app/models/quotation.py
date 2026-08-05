import uuid
from datetime import date
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, Date, Numeric, Integer, ForeignKey, Enum as SAEnum, Text, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.base import UUIDPKMixin, TimestampMixin, AuditMixin
from app.models.enums import QuotationStatus

if TYPE_CHECKING:
    from app.models.enquiry import Enquiry
    from app.models.company import Company
    from app.models.user import User
    from app.models.site_visit import SiteVisit
    from app.models.quotation_line_item import QuotationLineItem

quotation_signatures = Table(
    "quotation_signatures",
    Base.metadata,
    Column("quotation_id", ForeignKey("quotations.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)

class Quotation(Base, UUIDPKMixin, TimestampMixin, AuditMixin):
    __tablename__ = "quotations"

    quotation_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    subject: Mapped[str | None] = mapped_column(String(255))
    enquiry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("enquiries.id"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company.id"), nullable=False)
    executive_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    version_no: Mapped[str | None] = mapped_column(String(50))
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    is_draft: Mapped[bool] = mapped_column(Boolean, default=True)
    amount: Mapped[float | None] = mapped_column(Numeric(12, 3))
    currency: Mapped[str] = mapped_column(String(10), default="BHD")
    sent_date: Mapped[date | None] = mapped_column(Date)
    quotation_date: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    site_visit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("site_visits.id"))
    
    subtotal: Mapped[float | None] = mapped_column(Numeric(12, 3), default=0)
    global_discount: Mapped[float | None] = mapped_column(Numeric(12, 3), default=0)
    vat_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), default=0)
    expected_profit: Mapped[float | None] = mapped_column(Numeric(12, 3), default=0)
    total_estimated_cost: Mapped[float | None] = mapped_column(Numeric(12, 3), default=0)
    
    terms_and_conditions: Mapped[str | None] = mapped_column(Text)
    remarks: Mapped[str | None] = mapped_column(Text)
    
    status: Mapped[QuotationStatus] = mapped_column(SAEnum(QuotationStatus), default=QuotationStatus.draft)

    enquiry: Mapped["Enquiry"] = relationship("Enquiry", back_populates="quotations")
    company: Mapped["Company"] = relationship("Company", back_populates="quotations")
    executive: Mapped["User"] = relationship("User", back_populates="quotations", foreign_keys="Quotation.executive_id")
    site_visit: Mapped["SiteVisit | None"] = relationship("SiteVisit")
    line_items: Mapped[list["QuotationLineItem"]] = relationship("QuotationLineItem", back_populates="quotation", cascade="all, delete-orphan")
    signatures: Mapped[list["User"]] = relationship("User", secondary=quotation_signatures)
    
    created_by: Mapped["User"] = relationship("User", foreign_keys="Quotation.created_by_id")
    updated_by: Mapped["User | None"] = relationship("User", foreign_keys="Quotation.updated_by_id")

    @property
    def enquiry_no(self) -> str | None:
        return self.enquiry.enquiry_number if self.enquiry else None

    @property
    def company_name(self) -> str | None:
        return self.company.company_name if self.company else None

    @property
    def executive_name(self) -> str | None:
        return self.executive.full_name if self.executive else None

    @property
    def created_by_name(self) -> str | None:
        return self.created_by.full_name if self.created_by else None

    @property
    def updated_by_name(self) -> str | None:
        return self.updated_by.full_name if self.updated_by else None
