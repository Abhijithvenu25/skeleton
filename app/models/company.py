from typing import TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.base import UUIDPKMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.enquiry import Enquiry
    from app.models.site_visit import SiteVisit
    from app.models.quotation import Quotation

class Company(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "company"

    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_website: Mapped[str | None] = mapped_column(String(255))
    address_line1: Mapped[str | None] = mapped_column(String(255))
    address_line2: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100))
    pincode: Mapped[str | None] = mapped_column(String(20))

    enquiries: Mapped[list["Enquiry"]] = relationship("Enquiry", back_populates="company")
    site_visits: Mapped[list["SiteVisit"]] = relationship("SiteVisit", back_populates="company")
    quotations: Mapped[list["Quotation"]] = relationship("Quotation", back_populates="company")
