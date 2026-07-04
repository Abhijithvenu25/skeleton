from typing import TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.base import UUIDPKMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.enquiry import Enquiry

class Client(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "clients"

    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_contact: Mapped[str | None] = mapped_column(String(50))
    alternate_contact: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    client_designation: Mapped[str | None] = mapped_column(String(255))
    enquiries: Mapped[list["Enquiry"]] = relationship("Enquiry", back_populates="client")
