"""Customer endpoints (CRUD + pagination + search)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Query, status

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


def _service(db: DbSession) -> CustomerService:
    return CustomerService(session=db)


@router.post(
    "",
    response_model=CustomerOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a customer",
)
async def create_customer(
    payload: CustomerIn,
    db: DbSession,
    current_user: CurrentUser,
) -> CustomerOut:
    return await _service(db).create(owner_id=uuid.UUID(str(current_user.id)), payload=payload)


@router.get(
    "",
    response_model=CustomerPage,
    summary="List customers (paginated, searchable)",
)
async def list_customers(
    db: DbSession,
    current_user: CurrentUser,
    q: Annotated[str | None, Query(description="Search in name/email/company/phone")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[CustomerOut]:
    return await _service(db).list(
        owner_id=uuid.UUID(str(current_user.id)),
        q=q,
        page=page,
        size=size,
    )


@router.get(
    "/{customer_id}",
    response_model=CustomerOut,
    summary="Get a customer by id",
)
async def get_customer(
    customer_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> CustomerOut:
    return await _service(db).get(
        owner_id=uuid.UUID(str(current_user.id)),
        customer_id=customer_id,
    )


@router.patch(
    "/{customer_id}",
    response_model=CustomerOut,
    summary="Partially update a customer",
)
async def patch_customer(
    customer_id: uuid.UUID,
    payload: CustomerPatch,
    db: DbSession,
    current_user: CurrentUser,
) -> CustomerOut:
    return await _service(db).patch(
        owner_id=uuid.UUID(str(current_user.id)),
        customer_id=customer_id,
        payload=payload,
    )


@router.delete(
    "/{customer_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft-delete a customer",
)
async def delete_customer(
    customer_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> MessageResponse:
    await _service(db).delete(
        owner_id=uuid.UUID(str(current_user.id)),
        customer_id=customer_id,
    )
    return MessageResponse(message="Customer deleted")
