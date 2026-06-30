"""Enquiry endpoints (includes the mark-lost funnel terminal)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import Page
from app.schemas.crm.enquiry import (
    EnquiryIn,
    EnquiryOut,
    EnquiryPatch,
    MarkLostIn,
)
from app.services.crm._common import build_page
from app.services.crm.enquiry import EnquiryService

router = APIRouter(prefix="/enquiries", tags=["crm-enquiries"])


def _get_service(session: DbSession) -> EnquiryService:
    return EnquiryService(session=session)


ServiceDep = Annotated[EnquiryService, Depends(_get_service)]


@router.get("", response_model=Page[EnquiryOut], summary="List enquiries")
async def list_enquiries(
    service: ServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status_: str | None = Query(None, alias="status"),
    sales_executive_id: uuid.UUID | None = Query(None),
) -> Page[EnquiryOut]:
    items, total = await service.list(
        page=page,
        size=size,
        status=status_,
        sales_executive_id=sales_executive_id,
    )
    return build_page(
        [EnquiryOut.model_validate(e) for e in items], total, page, size
    )


@router.post("", response_model=EnquiryOut, status_code=status.HTTP_201_CREATED, summary="Create enquiry")
async def create_enquiry(
    payload: EnquiryIn,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> EnquiryOut:
    enquiry = await service.create(payload, actor=_current_user)
    return EnquiryOut.model_validate(enquiry)


@router.get("/{enquiry_id}", response_model=EnquiryOut, summary="Get enquiry")
async def get_enquiry(enquiry_id: uuid.UUID, service: ServiceDep) -> EnquiryOut:
    enquiry = await service.get_by_id(enquiry_id)
    return EnquiryOut.model_validate(enquiry)


@router.patch("/{enquiry_id}", response_model=EnquiryOut, summary="Update enquiry")
async def update_enquiry(
    enquiry_id: uuid.UUID,
    payload: EnquiryPatch,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> EnquiryOut:
    enquiry = await service.update(enquiry_id, payload, actor=_current_user)
    return EnquiryOut.model_validate(enquiry)


@router.delete(
    "/{enquiry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete enquiry",
)
async def delete_enquiry(
    enquiry_id: uuid.UUID,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> None:
    await service.soft_delete(enquiry_id, actor=_current_user)


@router.post(
    "/{enquiry_id}/mark-lost",
    response_model=EnquiryOut,
    summary="Mark enquiry as lost (creates lost_enquiries row + flips status)",
)
async def mark_enquiry_lost(
    enquiry_id: uuid.UUID,
    payload: MarkLostIn,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> EnquiryOut:
    enquiry, _lost = await service.mark_lost(enquiry_id, payload, actor=_current_user)
    return EnquiryOut.model_validate(enquiry)
