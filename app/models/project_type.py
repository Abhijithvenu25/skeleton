from typing import TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.base import UUIDPKMixin

if TYPE_CHECKING:
    from app.models.project import Project

class ProjectType(Base, UUIDPKMixin):
    __tablename__ = "project_type"

    type_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(500))

    projects: Mapped[list["Project"]] = relationship("Project", back_populates="project_type")
