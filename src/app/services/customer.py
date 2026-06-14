"""Customer service: CRUD + pagination + search."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.customer import Customer
from app.schemas.customer import CustomerIn, CustomerPatch


class CustomerService:
    """Encapsulates the customer business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ---- Internal helpers ---------------------------------------------------

    async def _owned_or_404(self, customer_id: uuid.UUID, owner_id: uuid.UUID) -> Customer:
        customer = await Customer.get_by_id(self.session, customer_id)
        if customer is None or customer.deleted_at is not None:
            raise NotFoundError("Customer not found")
        if customer.owner_id != owner_id:
            raise ForbiddenError("Not allowed to access this customer")
        return customer

    # ---- Public API ---------------------------------------------------------

    async def create(
        self,
        *,
        owner_id: uuid.UUID,
        payload: CustomerIn,
    ) -> Customer:
        customer = Customer(
            owner_id=owner_id,
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
            company=payload.company,
            notes=payload.notes,
        )
        self.session.add(customer)
        await self.session.commit()
        await self.session.refresh(customer)
        return customer

    async def list(
        self,
        *,
        owner_id: uuid.UUID,
        query: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Customer], int]:
        offset = (page - 1) * size
        return await Customer.search_by_owner(
            self.session,
            owner_id,
            query=query,
            offset=offset,
            limit=size,
        )

    async def get(self, *, customer_id: uuid.UUID, owner_id: uuid.UUID) -> Customer:
        return await self._owned_or_404(customer_id, owner_id)

    async def patch(
        self,
        *,
        customer_id: uuid.UUID,
        owner_id: uuid.UUID,
        payload: CustomerPatch,
    ) -> Customer:
        customer = await self._owned_or_404(customer_id, owner_id)

        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(customer, key, value)
        await self.session.commit()
        await self.session.refresh(customer)
        return customer

    async def soft_delete(self, *, customer_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        customer = await self._owned_or_404(customer_id, owner_id)
        from datetime import UTC, datetime

        customer.deleted_at = datetime.now(tz=UTC)
        await self.session.commit()
