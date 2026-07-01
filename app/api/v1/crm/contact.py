"""Contact endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import Page
from app.schemas.crm.contact import (
    ContactIn,
    ContactOut,
    ContactPatch,
)
from app.services.crm._common import build_page
from app.services.crm.contact import ContactService

router = APIRouter(prefix="/contacts", tags=["crm-contacts"])


def _get_service(session: DbSession) -> ContactService:
    return ContactService(session=session)


ServiceDep = Annotated[ContactService, Depends(_get_service)]


@router.get("", response_model=Page[ContactOut], summary="List contacts")
async def list_contacts(
    service: ServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    company_id: uuid.UUID | None = Query(None),
) -> Page[ContactOut]:
    items, total = await service.list(page=page, size=size, company_id=company_id)
    return build_page([ContactOut.model_validate(c) for c in items], total, page, size)


@router.post("", response_model=ContactOut, status_code=status.HTTP_201_CREATED, summary="Create contact")
async def create_contact(
    payload: ContactIn,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> ContactOut:
    contact = await service.create(payload, actor=_current_user)
    return ContactOut.model_validate(contact)


@router.get("/{contact_id}", response_model=ContactOut, summary="Get contact")
async def get_contact(contact_id: uuid.UUID, service: ServiceDep) -> ContactOut:
    contact = await service.get_by_id(contact_id)
    return ContactOut.model_validate(contact)


@router.patch("/{contact_id}", response_model=ContactOut, summary="Update contact")
async def update_contact(
    contact_id: uuid.UUID,
    payload: ContactPatch,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> ContactOut:
    contact = await service.update(contact_id, payload, actor=_current_user)
    return ContactOut.model_validate(contact)


@router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete contact",
)
async def delete_contact(
    contact_id: uuid.UUID,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> None:
    await service.soft_delete(contact_id, actor=_current_user)
