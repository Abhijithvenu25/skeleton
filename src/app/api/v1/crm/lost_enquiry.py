"""LostEnquiry endpoints (most usage is via POST /enquiries/{id}/mark-lost)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import Page
from app.schemas.crm.lost_enquiry import (
    LostEnquiryIn,
    LostEnquiryOut,
    LostEnquiryPatch,
)
from app.services.crm._common import build_page
from app.services.crm.lost_enquiry import LostEnquiryService

router = APIRouter(prefix="/lost-enquiries", tags=["crm-lost-enquiries"])


def _get_service(session: DbSession) -> LostEnquiryService:
    return LostEnquiryService(session=session)


ServiceDep = Annotated[LostEnquiryService, Depends(_get_service)]


@router.get("", response_model=Page[LostEnquiryOut], summary="List lost enquiries")
async def list_lost_enquiries(
    service: ServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> Page[LostEnquiryOut]:
    items, total = await service.list(page=page, size=size)
    return build_page(
        [LostEnquiryOut.model_validate(le) for le in items], total, page, size
    )


@router.post("", response_model=LostEnquiryOut, status_code=status.HTTP_201_CREATED, summary="Record a lost enquiry")
async def create_lost_enquiry(
    payload: LostEnquiryIn,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> LostEnquiryOut:
    lost = await service.create(payload, actor=_current_user)
    return LostEnquiryOut.model_validate(lost)


@router.get("/{lost_id}", response_model=LostEnquiryOut, summary="Get lost-enquiry record")
async def get_lost_enquiry(lost_id: uuid.UUID, service: ServiceDep) -> LostEnquiryOut:
    lost = await service.get_by_id(lost_id)
    return LostEnquiryOut.model_validate(lost)


@router.patch("/{lost_id}", response_model=LostEnquiryOut, summary="Update lost-enquiry record")
async def update_lost_enquiry(
    lost_id: uuid.UUID,
    payload: LostEnquiryPatch,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> LostEnquiryOut:
    lost = await service.update(lost_id, payload, actor=_current_user)
    return LostEnquiryOut.model_validate(lost)


@router.delete(
    "/{lost_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete lost-enquiry record (cascade-managed otherwise)",
)
async def delete_lost_enquiry(
    lost_id: uuid.UUID,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> None:
    await service.delete(lost_id, actor=_current_user)
