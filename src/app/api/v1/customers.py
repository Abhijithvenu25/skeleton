"""Customer endpoints (CRUD + pagination + search)."""

from __future__ import annotations

import math
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import MessageResponse, Page
from app.schemas.customer import (
    CustomerIn,
    CustomerOut,
    CustomerPage,
    CustomerPatch,
)
from app.services.customer import CustomerService

router = APIRouter(prefix="/customers", tags=["customers"])


def _get_customer_service(db: DbSession) -> CustomerService:
    return CustomerService(session=db)


CustomerServiceDep = Annotated[CustomerService, Depends(_get_customer_service)]


@router.post(
    "",
    response_model=CustomerOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a customer",
)
async def create_customer(
    payload: CustomerIn,
    service: CustomerServiceDep,
    current_user: CurrentUser,
) -> CustomerOut:
    customer = await service.create(
        owner_id=uuid.UUID(str(current_user.id)),
        payload=payload,
    )
    return CustomerOut.model_validate(customer)


@router.get(
    "",
    response_model=CustomerPage,
    summary="List customers (paginated, searchable)",
)
async def list_customers(
    service: CustomerServiceDep,
    current_user: CurrentUser,
    q: Annotated[str | None, Query(description="Search in name/email/company/phone")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[CustomerOut]:
    items, total = await service.list(
        owner_id=uuid.UUID(str(current_user.id)),
        query=q,
        page=page,
        size=size,
    )
    pages = max(1, math.ceil(total / size)) if total else 1
    return Page[CustomerOut](
        items=[CustomerOut.model_validate(c) for c in items],
        total=int(total),
        page=page,
        size=size,
        pages=pages,
    )


@router.get(
    "/{customer_id}",
    response_model=CustomerOut,
    summary="Get a customer by id",
)
async def get_customer(
    customer_id: uuid.UUID,
    service: CustomerServiceDep,
    current_user: CurrentUser,
) -> CustomerOut:
    customer = await service.get(
        customer_id=customer_id,
        owner_id=uuid.UUID(str(current_user.id)),
    )
    return CustomerOut.model_validate(customer)


@router.patch(
    "/{customer_id}",
    response_model=CustomerOut,
    summary="Partially update a customer",
)
async def patch_customer(
    customer_id: uuid.UUID,
    payload: CustomerPatch,
    service: CustomerServiceDep,
    current_user: CurrentUser,
) -> CustomerOut:
    customer = await service.patch(
        customer_id=customer_id,
        owner_id=uuid.UUID(str(current_user.id)),
        payload=payload,
    )
    return CustomerOut.model_validate(customer)


@router.delete(
    "/{customer_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft-delete a customer",
)
async def delete_customer(
    customer_id: uuid.UUID,
    service: CustomerServiceDep,
    current_user: CurrentUser,
) -> MessageResponse:
    await service.soft_delete(
        customer_id=customer_id,
        owner_id=uuid.UUID(str(current_user.id)),
    )
    return MessageResponse(message="Customer deleted")
