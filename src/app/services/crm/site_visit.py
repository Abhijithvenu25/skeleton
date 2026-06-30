"""SiteVisit service."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.site_visit import SiteVisit
from app.models.user import User
from app.schemas.crm.site_visit import (
    SiteVisitIn,
    SiteVisitPatch,
)
from app.services.crm._common import (
    apply_audit_create,
    apply_audit_update,
    commit,
    flush_and_refresh,
    paginate,
)


class SiteVisitService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self,
        *,
        page: int = 1,
        size: int = 20,
        enquiry_id: uuid.UUID | None = None,
    ) -> tuple[list[SiteVisit], int]:
        where = [SiteVisit.deleted_at.is_(None)]
        if enquiry_id is not None:
            where.append(SiteVisit.enquiry_id == enquiry_id)
        return await paginate(
            self.session,
            SiteVisit,
            page=page,
            size=size,
            order_by=SiteVisit.scheduled_at.desc(),
            where=where,
        )

    async def get_by_id(self, visit_id: uuid.UUID) -> SiteVisit:
        visit = await SiteVisit.get_by_id(self.session, visit_id)
        if visit is None or visit.deleted_at is not None:
            raise NotFoundError(f"SiteVisit {visit_id} not found")
        return visit

    async def create(self, payload: SiteVisitIn, *, actor: User) -> SiteVisit:
        visit = SiteVisit(
            enquiry_id=payload.enquiry_id,
            scheduled_at=payload.scheduled_at,
            completed_at=payload.completed_at,
            engineer_id=payload.engineer_id,
            sales_executive_id=payload.sales_executive_id,
            status=payload.status.value,
            notes=payload.notes,
        )
        apply_audit_create(visit, actor=actor)
        self.session.add(visit)
        await flush_and_refresh(self.session, visit)
        return visit

    async def update(
        self, visit_id: uuid.UUID, payload: SiteVisitPatch, *, actor: User
    ) -> SiteVisit:
        visit = await self.get_by_id(visit_id)
        if payload.scheduled_at is not None:
            visit.scheduled_at = payload.scheduled_at
        if payload.completed_at is not None:
            visit.completed_at = payload.completed_at
        if payload.engineer_id is not None:
            visit.engineer_id = payload.engineer_id
        if payload.status is not None:
            visit.status = payload.status.value
        if payload.notes is not None:
            visit.notes = payload.notes
        apply_audit_update(visit, actor=actor)
        await commit(self.session)
        return visit

    async def delete(self, visit_id: uuid.UUID, *, actor: User) -> None:
        """Hard-delete (site visits cascade from enquiry — no soft-delete)."""
        visit = await self.get_by_id(visit_id)
        await self.session.delete(visit)
        await commit(self.session)
