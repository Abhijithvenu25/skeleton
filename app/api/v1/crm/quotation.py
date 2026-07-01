"""Quotation endpoints (including version creation with inline line items)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import Page
from app.schemas.crm.quotation import (
    QuotationIn,
    QuotationOut,
    QuotationPatch,
)
from app.schemas.crm.quotation_version import QuotationVersionIn, QuotationVersionOut
from app.services.crm._common import build_page
from app.services.crm.quotation import QuotationService

router = APIRouter(prefix="/quotations", tags=["crm-quotations"])


def _get_service(session: DbSession) -> QuotationService:
    return QuotationService(session=session)


ServiceDep = Annotated[QuotationService, Depends(_get_service)]


@router.get("", response_model=Page[QuotationOut], summary="List quotations")
async def list_quotations(
    service: ServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    enquiry_id: uuid.UUID | None = Query(None),
) -> Page[QuotationOut]:
    items, total = await service.list(page=page, size=size, enquiry_id=enquiry_id)
    return build_page(
        [QuotationOut.model_validate(q) for q in items], total, page, size
    )


@router.post("", response_model=QuotationOut, status_code=status.HTTP_201_CREATED, summary="Create quotation")
async def create_quotation(
    payload: QuotationIn,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> QuotationOut:
    quotation = await service.create(payload, actor=_current_user)
    return QuotationOut.model_validate(quotation)


@router.get("/{quotation_id}", response_model=QuotationOut, summary="Get quotation")
async def get_quotation(quotation_id: uuid.UUID, service: ServiceDep) -> QuotationOut:
    quotation = await service.get_by_id(quotation_id)
    return QuotationOut.model_validate(quotation)


@router.patch("/{quotation_id}", response_model=QuotationOut, summary="Update quotation")
async def update_quotation(
    quotation_id: uuid.UUID,
    payload: QuotationPatch,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> QuotationOut:
    quotation = await service.update(quotation_id, payload, actor=_current_user)
    return QuotationOut.model_validate(quotation)


@router.delete(
    "/{quotation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hard-delete quotation (cascade-managed)",
)
async def delete_quotation(
    quotation_id: uuid.UUID,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> None:
    await service.delete(quotation_id, actor=_current_user)


@router.post(
    "/{quotation_id}/versions",
    response_model=QuotationVersionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new version to a quotation (with line items)",
)
async def add_quotation_version(
    quotation_id: uuid.UUID,
    payload: QuotationVersionIn,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> QuotationVersionOut:
    version = await service.add_version(quotation_id, payload, actor=_current_user)
    return QuotationVersionOut.model_validate(version)


@router.get(
    "/{quotation_id}/versions",
    response_model=list[QuotationVersionOut],
    summary="List all versions for a quotation (audit trail)",
)
async def list_quotation_versions(
    quotation_id: uuid.UUID,
    service: ServiceDep,
) -> list[QuotationVersionOut]:
    versions = await service.list_versions(quotation_id)
    return [QuotationVersionOut.model_validate(v) for v in versions]
