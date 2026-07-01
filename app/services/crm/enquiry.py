"""Enquiry service."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.enquiry import Enquiry
from app.models.lost_enquiry import LostEnquiry
from app.models.user import User
from app.schemas.crm.enquiry import (
    EnquiryIn,
    EnquiryPatch,
    MarkLostIn,
)
from app.services.crm._common import (
    apply_audit_create,
    apply_audit_soft_delete,
    apply_audit_update,
    commit,
    flush_and_refresh,
    paginate,
)


class EnquiryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self,
        *,
        page: int = 1,
        size: int = 20,
        status: str | None = None,
        sales_executive_id: uuid.UUID | None = None,
    ) -> tuple[list[Enquiry], int]:
        where = [Enquiry.deleted_at.is_(None)]
        if status is not None:
            where.append(Enquiry.status == status)
        if sales_executive_id is not None:
            where.append(Enquiry.sales_executive_id == sales_executive_id)
        return await paginate(
            self.session,
            Enquiry,
            page=page,
            size=size,
            order_by=Enquiry.enquiry_date.desc(),
            where=where,
        )

    async def get_by_id(self, enquiry_id: uuid.UUID) -> Enquiry:
        enquiry = await Enquiry.get_by_id(self.session, enquiry_id)
        if enquiry is None or enquiry.deleted_at is not None:
            raise NotFoundError(f"Enquiry {enquiry_id} not found")
        return enquiry

    async def create(self, payload: EnquiryIn, *, actor: User) -> Enquiry:
        enquiry = Enquiry(
            company_id=payload.company_id,
            contact_id=payload.contact_id,
            project_id=payload.project_id,
            sales_executive_id=payload.sales_executive_id,
            engineer_id=payload.engineer_id,
            source=payload.source.value,
            location=payload.location,
            priority=payload.priority.value,
            status="enquiry",
            enquiry_date=payload.enquiry_date or date.today(),
            notes=payload.notes,
        )
        apply_audit_create(enquiry, actor=actor)
        self.session.add(enquiry)
        # Flush so the trigger-assigned enquiry_no is populated, then refresh
        # so created_at / created_by_id server defaults are visible.
        await flush_and_refresh(self.session, enquiry)
        return enquiry

    async def update(
        self, enquiry_id: uuid.UUID, payload: EnquiryPatch, *, actor: User
    ) -> Enquiry:
        enquiry = await self.get_by_id(enquiry_id)
        if payload.project_id is not None:
            enquiry.project_id = payload.project_id
        if payload.engineer_id is not None:
            enquiry.engineer_id = payload.engineer_id
        if payload.source is not None:
            enquiry.source = payload.source.value
        if payload.location is not None:
            enquiry.location = payload.location
        if payload.priority is not None:
            enquiry.priority = payload.priority.value
        if payload.status is not None:
            enquiry.status = payload.status.value
        if payload.notes is not None:
            enquiry.notes = payload.notes
        apply_audit_update(enquiry, actor=actor)
        await commit(self.session)
        return enquiry

    async def mark_lost(
        self, enquiry_id: uuid.UUID, payload: MarkLostIn, *, actor: User
    ) -> tuple[Enquiry, LostEnquiry]:
        """Atomic: create lost_enquiries row + flip enquiry.status='lost'."""
        enquiry = await self.get_by_id(enquiry_id)
        stage = payload.stage_lost.value
        if stage not in {"enquiry", "site_visit", "quotation"}:
            raise BadRequestError(
                f"stage_lost must be one of enquiry/site_visit/quotation, got {stage!r}"
            )

        existing = await LostEnquiry.get_by_enquiry_id(self.session, enquiry_id)
        if existing is not None:
            from app.core.exceptions import ConflictError

            raise ConflictError(
                f"Enquiry {enquiry_id} is already marked lost (stage={existing.stage_lost})"
            )

        lost = LostEnquiry(
            enquiry_id=enquiry_id,
            stage_lost=stage,
            reason_lost=payload.reason_lost,
            follow_up_date=payload.follow_up_date,
            notes=payload.notes,
            date_lost=date.today(),
        )
        apply_audit_create(lost, actor=actor)
        self.session.add(lost)

        enquiry.status = "lost"
        enquiry.updated_by_id = actor.id
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(enquiry)
        await self.session.refresh(lost)
        return enquiry, lost

    async def soft_delete(self, enquiry_id: uuid.UUID, *, actor: User) -> None:
        enquiry = await self.get_by_id(enquiry_id)
        apply_audit_soft_delete(enquiry, actor=actor)
        await commit(self.session)
