"""Quotation service."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.quotation import Quotation
from app.models.quotation_line_item import QuotationLineItem
from app.models.quotation_version import QuotationVersion
from app.models.user import User
from app.schemas.crm.quotation import QuotationIn, QuotationPatch
from app.schemas.crm.quotation_version import QuotationVersionIn
from app.services.crm._common import (
    apply_audit_create,
    apply_audit_update,
    commit,
    flush_and_refresh,
    paginate,
)


class QuotationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self,
        *,
        page: int = 1,
        size: int = 20,
        enquiry_id: uuid.UUID | None = None,
    ) -> tuple[list[Quotation], int]:
        where = [Quotation.deleted_at.is_(None)]
        if enquiry_id is not None:
            where.append(Quotation.enquiry_id == enquiry_id)
        return await paginate(
            self.session,
            Quotation,
            page=page,
            size=size,
            order_by=Quotation.created_at.desc(),
            where=where,
        )

    async def get_by_id(self, quotation_id: uuid.UUID) -> Quotation:
        quotation = await Quotation.get_by_id(self.session, quotation_id)
        if quotation is None or quotation.deleted_at is not None:
            raise NotFoundError(f"Quotation {quotation_id} not found")
        return quotation

    async def create(self, payload: QuotationIn, *, actor: User) -> Quotation:
        quotation = Quotation(enquiry_id=payload.enquiry_id)
        apply_audit_create(quotation, actor=actor)
        self.session.add(quotation)
        await flush_and_refresh(self.session, quotation)
        return quotation

    async def update(
        self, quotation_id: uuid.UUID, payload: QuotationPatch, *, actor: User
    ) -> Quotation:
        quotation = await self.get_by_id(quotation_id)
        if payload.sent_date is not None:
            quotation.sent_date = payload.sent_date
        if payload.status is not None:
            quotation.status = payload.status.value
        apply_audit_update(quotation, actor=actor)
        await commit(self.session)
        return quotation

    async def add_version(
        self,
        quotation_id: uuid.UUID,
        payload: QuotationVersionIn,
        *,
        actor: User,
    ) -> QuotationVersion:
        """Create a new version + its line items atomically.

        Increments `quotations.current_version_no` and recomputes the new
        version's `amount` as `SUM(line_total)`. All in one transaction.
        """
        quotation = await self.get_by_id(quotation_id)
        # Source-of-truth: highest existing version_no on this quotation + 1.
        # (Falls back to 1 when no versions exist yet.)
        from sqlalchemy import func as sa_func

        max_existing = await self.session.scalar(
            select(sa_func.max(QuotationVersion.version_no)).where(
                QuotationVersion.quotation_id == quotation_id
            )
        )
        next_version_no = (max_existing or 0) + 1

        # Compute amount up front so we can persist it on the version row.
        amount = sum(
            (li.quantity * li.unit_price for li in payload.line_items),
            start=0,
        )

        version = QuotationVersion(
            quotation_id=quotation_id,
            version_no=next_version_no,
            amount=amount,
            terms=payload.terms,
            file_url=payload.file_url,
            created_by_id=actor.id,
        )
        self.session.add(version)
        await self.session.flush()  # populates version.id

        for li in payload.line_items:
            line_total = li.quantity * li.unit_price
            line_item = QuotationLineItem(
                quotation_version_id=version.id,
                line_type=li.line_type.value,
                description=li.description,
                quantity=li.quantity,
                unit_price=li.unit_price,
                line_total=line_total,
                sort_order=li.sort_order,
                created_by_id=actor.id,
                updated_by_id=actor.id,
            )
            self.session.add(line_item)

        quotation.current_version_no = next_version_no
        quotation.updated_by_id = actor.id
        await self.session.flush()  # ensure the FK target exists before commit
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(version)
        return version

    async def list_versions(
        self, quotation_id: uuid.UUID
    ) -> list[QuotationVersion]:
        """Return all versions for a quotation, newest first."""
        await self.get_by_id(quotation_id)  # 404 if missing/soft-deleted
        result = await self.session.execute(
            select(QuotationVersion)
            .where(QuotationVersion.quotation_id == quotation_id)
            .order_by(QuotationVersion.version_no.desc())
        )
        return list(result.scalars())

    async def delete(self, quotation_id: uuid.UUID, *, actor: User) -> None:
        """Hard-delete (quotations cascade from enquiry — no soft-delete)."""
        quotation = await self.get_by_id(quotation_id)
        await self.session.delete(quotation)
        await commit(self.session)
