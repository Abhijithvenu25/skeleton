"""SiteVisit endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import Page
from app.schemas.crm.site_visit import (
    SiteVisitIn,
    SiteVisitOut,
    SiteVisitPatch,
)
from app.services.crm._common import build_page
from app.services.crm.site_visit import SiteVisitService

router = APIRouter(prefix="/site-visits", tags=["crm-site-visits"])


def _get_service(session: DbSession) -> SiteVisitService:
    return SiteVisitService(session=session)


ServiceDep = Annotated[SiteVisitService, Depends(_get_service)]


@router.get("", response_model=Page[SiteVisitOut], summary="List site visits")
async def list_site_visits(
    service: ServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    enquiry_id: uuid.UUID | None = Query(None),
) -> Page[SiteVisitOut]:
    items, total = await service.list(page=page, size=size, enquiry_id=enquiry_id)
    return build_page(
        [SiteVisitOut.model_validate(v) for v in items], total, page, size
    )


@router.post("", response_model=SiteVisitOut, status_code=status.HTTP_201_CREATED, summary="Create site visit")
async def create_site_visit(
    payload: SiteVisitIn,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> SiteVisitOut:
    visit = await service.create(payload, actor=_current_user)
    return SiteVisitOut.model_validate(visit)


@router.get("/{visit_id}", response_model=SiteVisitOut, summary="Get site visit")
async def get_site_visit(visit_id: uuid.UUID, service: ServiceDep) -> SiteVisitOut:
    visit = await service.get_by_id(visit_id)
    return SiteVisitOut.model_validate(visit)


@router.patch("/{visit_id}", response_model=SiteVisitOut, summary="Update site visit")
async def update_site_visit(
    visit_id: uuid.UUID,
    payload: SiteVisitPatch,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> SiteVisitOut:
    visit = await service.update(visit_id, payload, actor=_current_user)
    return SiteVisitOut.model_validate(visit)


@router.delete(
    "/{visit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hard-delete site visit (cascade-managed)",
)
async def delete_site_visit(
    visit_id: uuid.UUID,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> None:
    await service.delete(visit_id, actor=_current_user)
