"""LostEnquiry service."""

from __future__ import annotations

import uuid
from datetime import date

from app.core.exceptions import ConflictError, NotFoundError
from app.models.lost_enquiry import LostEnquiry
from app.models.user import User
from app.schemas.crm.lost_enquiry import (
    LostEnquiryIn,
    LostEnquiryPatch,
)
from app.services.crm._common import (
    apply_audit_create,
    apply_audit_update,
    commit,
    flush_and_refresh,
    paginate,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


class LostEnquiryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self,
        *,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[LostEnquiry], int]:
        return await paginate(
            self.session,
            LostEnquiry,
            page=page,
            size=size,
            order_by=LostEnquiry.date_lost.desc(),
        )

    async def get_by_id(self, lost_id: uuid.UUID) -> LostEnquiry:
        lost = await LostEnquiry.get_by_id(self.session, lost_id)
        if lost is None:
            raise NotFoundError(f"LostEnquiry {lost_id} not found")
        return lost

    async def create(self, payload: LostEnquiryIn, *, actor: User) -> LostEnquiry:
        existing = await LostEnquiry.get_by_enquiry_id(self.session, payload.enquiry_id)
        if existing is not None:
            raise ConflictError(
                f"Enquiry {payload.enquiry_id} is already marked lost "
                f"(stage={existing.stage_lost})"
            )
        lost = LostEnquiry(
            enquiry_id=payload.enquiry_id,
            stage_lost=payload.stage_lost.value,
            reason_lost=payload.reason_lost,
            follow_up_date=payload.follow_up_date,
            notes=payload.notes,
            date_lost=date.today(),
        )
        apply_audit_create(lost, actor=actor)
        self.session.add(lost)
        try:
            await flush_and_refresh(self.session, lost)
        except IntegrityError as exc:
            # Most likely: uq_lost_enquiries_enquiry_id (1:1 with enquiry).
            raise ConflictError(
                "Lost enquiry already exists for this enquiry"
            ) from exc
        return lost

    async def update(
        self, lost_id: uuid.UUID, payload: LostEnquiryPatch, *, actor: User
    ) -> LostEnquiry:
        lost = await self.get_by_id(lost_id)
        if payload.reason_lost is not None:
            lost.reason_lost = payload.reason_lost
        if payload.follow_up_date is not None:
            lost.follow_up_date = payload.follow_up_date
        if payload.notes is not None:
            lost.notes = payload.notes
        apply_audit_update(lost, actor=actor)
        await commit(self.session)
        return lost

    async def delete(self, lost_id: uuid.UUID, *, actor: User) -> None:
        lost = await self.get_by_id(lost_id)
        await self.session.delete(lost)
        await commit(self.session)
