"""QuotationLineItem service (used mostly for read/audit; primary writes
go through QuotationService.add_version)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.quotation_line_item import QuotationLineItem
from app.models.user import User
from app.services.crm._common import paginate


class QuotationLineItemService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self,
        *,
        page: int = 1,
        size: int = 20,
        quotation_version_id: uuid.UUID | None = None,
    ) -> tuple[list[QuotationLineItem], int]:
        where = []
        if quotation_version_id is not None:
            where.append(QuotationLineItem.quotation_version_id == quotation_version_id)
        return await paginate(
            self.session,
            QuotationLineItem,
            page=page,
            size=size,
            order_by=QuotationLineItem.sort_order,
            where=where,
        )

    async def get_by_id(self, line_id: uuid.UUID) -> QuotationLineItem:
        line = await QuotationLineItem.get_by_id(self.session, line_id)
        if line is None:
            raise NotFoundError(f"QuotationLineItem {line_id} not found")
        return line

    async def list_for_version(
        self, version_id: uuid.UUID
    ) -> list[QuotationLineItem]:
        result = await self.session.execute(
            select(QuotationLineItem)
            .where(QuotationLineItem.quotation_version_id == version_id)
            .order_by(QuotationLineItem.sort_order)
        )
        return list(result.scalars())

    async def delete(self, line_id: uuid.UUID, *, actor: User) -> None:
        line = await self.get_by_id(line_id)
        await self.session.delete(line)
        await self.session.commit()