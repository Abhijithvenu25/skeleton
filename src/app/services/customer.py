"""Customer service — business logic around customer CRUD and search."""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.customer import Customer
from app.repositories.customer import CustomerRepository
from app.schemas.common import Page
from app.schemas.customer import CustomerIn, CustomerOut, CustomerPatch


@dataclass(slots=True)
class CustomerService:
    session: AsyncSession

    def _repo(self) -> CustomerRepository:
        return CustomerRepository(self.session)

    async def create(self, *, owner_id: uuid.UUID, payload: CustomerIn) -> CustomerOut:
        customer = await self._repo().create(
            owner_id=owner_id,
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
            company=payload.company,
            notes=payload.notes,
        )
        await self.session.commit()
        return CustomerOut.model_validate(customer)

    async def get(self, *, owner_id: uuid.UUID, customer_id: uuid.UUID) -> CustomerOut:
        customer = self._assert_owner(await self._repo().get_by_id(customer_id), owner_id)
        return CustomerOut.model_validate(customer)

    async def list(
        self,
        *,
        owner_id: uuid.UUID,
        q: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> Page[CustomerOut]:
        items, total = await self._repo().list(
            owner_id=owner_id, q=q, page=page, size=size
        )
        pages = max(1, math.ceil(total / size)) if total else 1
        return Page[CustomerOut](
            items=[CustomerOut.model_validate(c) for c in items],
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    async def patch(
        self,
        *,
        owner_id: uuid.UUID,
        customer_id: uuid.UUID,
        payload: CustomerPatch,
    ) -> CustomerOut:
        customer = self._assert_owner(
            await self._repo().get_by_id(customer_id), owner_id
        )
        data = payload.model_dump(exclude_unset=True)
        if data:
            await self._repo().update(customer, **data)
        await self.session.commit()
        return CustomerOut.model_validate(customer)

    async def delete(self, *, owner_id: uuid.UUID, customer_id: uuid.UUID) -> None:
        customer = self._assert_owner(
            await self._repo().get_by_id(customer_id), owner_id
        )
        await self._repo().soft_delete(customer)
        await self.session.commit()

    @staticmethod
    def _assert_owner(customer: Customer | None, owner_id: uuid.UUID) -> Customer:
        if customer is None or customer.deleted_at is not None:
            raise NotFoundError("Customer not found")
        if customer.owner_id != owner_id:
            raise ForbiddenError("Not allowed to access this customer")
        return customer
