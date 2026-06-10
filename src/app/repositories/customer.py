"""Customer repository — pure DB queries."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer


class CustomerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, customer_id: uuid.UUID) -> Customer | None:
        return await self._session.get(Customer, customer_id)

    async def list(
        self,
        *,
        owner_id: uuid.UUID,
        q: str | None = None,
        include_deleted: bool = False,
        page: int = 1,
        size: int = 20,
    ) -> tuple[Sequence[Customer], int]:
        stmt = select(Customer).where(Customer.owner_id == owner_id)
        count_stmt = select(func.count(Customer.id)).where(Customer.owner_id == owner_id)

        if not include_deleted:
            stmt = stmt.where(Customer.deleted_at.is_(None))
            count_stmt = count_stmt.where(Customer.deleted_at.is_(None))

        if q:
            pattern = f"%{q.lower()}%"
            # Use ILIKE on name/email/company/phone; lowercased substring.
            search_filter = or_(
                func.lower(Customer.name).like(pattern),
                func.lower(func.coalesce(Customer.email, "")).like(pattern),
                func.lower(func.coalesce(Customer.company, "")).like(pattern),
                func.coalesce(Customer.phone, "").like(q),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total = (await self._session.execute(count_stmt)).scalar_one()

        offset = (page - 1) * size
        stmt = stmt.order_by(Customer.created_at.desc()).offset(offset).limit(size)
        result = await self._session.execute(stmt)
        items = list(result.scalars().unique().all())
        return items, int(total)

    async def create(
        self,
        *,
        owner_id: uuid.UUID,
        name: str,
        email: str | None = None,
        phone: str | None = None,
        company: str | None = None,
        notes: str | None = None,
    ) -> Customer:
        customer = Customer(
            owner_id=owner_id,
            name=name,
            email=email,
            phone=phone,
            company=company,
            notes=notes,
        )
        self._session.add(customer)
        await self._session.flush()
        return customer

    async def update(self, customer: Customer, **fields: object) -> Customer:
        for key, value in fields.items():
            setattr(customer, key, value)
        await self._session.flush()
        return customer

    async def soft_delete(self, customer: Customer) -> None:
        from datetime import datetime, timezone

        customer.deleted_at = datetime.now(tz=UTC)
        await self._session.flush()
