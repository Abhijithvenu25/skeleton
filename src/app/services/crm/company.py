"""Company service."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.company import Company
from app.models.user import User
from app.schemas.crm.company import CompanyIn, CompanyPatch
from app.services.crm._common import (
    apply_audit_create,
    apply_audit_soft_delete,
    apply_audit_update,
    commit,
    flush_and_refresh,
    paginate,
)


class CompanyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self, *, page: int = 1, size: int = 20
    ) -> tuple[list[Company], int]:
        return await paginate(
            self.session,
            Company,
            page=page,
            size=size,
            order_by=Company.name,
            where=[Company.deleted_at.is_(None)],
        )

    async def get_by_id(self, company_id: uuid.UUID) -> Company:
        company = await Company.get_by_id(self.session, company_id)
        if company is None or company.deleted_at is not None:
            raise NotFoundError(f"Company {company_id} not found")
        return company

    async def create(self, payload: CompanyIn, *, actor: User) -> Company:
        company = Company(**payload.model_dump())
        apply_audit_create(company, actor=actor)
        self.session.add(company)
        await flush_and_refresh(self.session, company)
        return company

    async def update(
        self, company_id: uuid.UUID, payload: CompanyPatch, *, actor: User
    ) -> Company:
        company = await self.get_by_id(company_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(company, field, value)
        apply_audit_update(company, actor=actor)
        await commit(self.session)
        return company

    async def soft_delete(self, company_id: uuid.UUID, *, actor: User) -> None:
        company = await self.get_by_id(company_id)
        apply_audit_soft_delete(company, actor=actor)
        await commit(self.session)
