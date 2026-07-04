"""User ORM model with query helpers."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from sqlalchemy import select as _select  # noqa: F401  (typing only)

    from app.models.role import Role
    from app.models.enquiry import Enquiry
    from app.models.site_visit import SiteVisit
    from app.models.quotation import Quotation

class User(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_image: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # N:M roles via user_roles junction. selectin loading so .roles is eager
    # when serialising a User, avoiding the N+1 trap when responses include
    # multiple users. primaryjoin + secondaryjoin are required because
    # `user_roles` has TWO FKs back to users (user_id and granted_by_id),
    # which gives SQLAlchemy two candidate join paths; we want the
    # user_id → role_id path (the role-grant recipient).
    roles: Mapped[list[Role]] = relationship(
        "Role",
        secondary="user_roles",
        primaryjoin="User.id == UserRole.user_id",
        secondaryjoin="Role.id == UserRole.role_id",
        lazy="selectin",
    )

    enquiries: Mapped[list["Enquiry"]] = relationship(
        "Enquiry", back_populates="sales_executive", foreign_keys="Enquiry.sales_executive_id"
    )
    engineered_visits: Mapped[list["SiteVisit"]] = relationship(
        "SiteVisit", back_populates="engineer", foreign_keys="SiteVisit.engineer_id"
    )
    executive_visits: Mapped[list["SiteVisit"]] = relationship(
        "SiteVisit", back_populates="sales_executive", foreign_keys="SiteVisit.sales_executive_id"
    )
    quotations: Mapped[list["Quotation"]] = relationship("Quotation", back_populates="executive")

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, email={self.email!r})"

    # ---- Query helpers (classmethods) ---------------------------------------

    @classmethod
    async def get_by_id(cls, session: AsyncSession, user_id: uuid.UUID) -> User | None:
        """Fetch a user by primary key."""
        from sqlalchemy import select

        result = await session.scalar(select(cls).where(cls.id == user_id))
        return result

    @classmethod
    async def get_by_email(cls, session: AsyncSession, email: str) -> User | None:
        """Fetch a user by email (case-insensitive)."""
        from sqlalchemy import select

        result = await session.scalar(select(cls).where(cls.email == email.lower()))
        return result
