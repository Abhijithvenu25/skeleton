import uuid
from datetime import date
from typing import TYPE_CHECKING
from sqlalchemy import String, Numeric, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.base import UUIDPKMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.project_type import ProjectType
    from app.models.enquiry import Enquiry

class Project(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "projects"

    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    project_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("project_type.id"), nullable=False)
    project_location: Mapped[str | None] = mapped_column(String(255))
    estimated_budget: Mapped[float | None] = mapped_column(Numeric(12, 3))
    expected_start_date: Mapped[date | None] = mapped_column(Date)

    project_type: Mapped["ProjectType"] = relationship("ProjectType", back_populates="projects")
    enquiry: Mapped["Enquiry"] = relationship("Enquiry", back_populates="project", uselist=False)
