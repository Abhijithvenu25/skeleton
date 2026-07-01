"""QuotationLineItem endpoints (read-only for the audit UI; writes go through
POST /quotations/{id}/versions)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import Page
from app.schemas.crm.quotation_version import QuotationLineItemOut
from app.services.crm._common import build_page
from app.services.crm.quotation_line_item import QuotationLineItemService

router = APIRouter(prefix="/quotation-line-items", tags=["crm-quotation-line-items"])


def _get_service(session: DbSession) -> QuotationLineItemService:
    return QuotationLineItemService(session=session)


ServiceDep = Annotated[QuotationLineItemService, Depends(_get_service)]


@router.get("", response_model=Page[QuotationLineItemOut], summary="List line items")
async def list_line_items(
    service: ServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    quotation_version_id: uuid.UUID | None = Query(None),
) -> Page[QuotationLineItemOut]:
    items, total = await service.list(
        page=page, size=size, quotation_version_id=quotation_version_id
    )
    return build_page(
        [QuotationLineItemOut.model_validate(li) for li in items], total, page, size
    )


@router.get("/{line_id}", response_model=QuotationLineItemOut, summary="Get line item")
async def get_line_item(line_id: uuid.UUID, service: ServiceDep) -> QuotationLineItemOut:
    line = await service.get_by_id(line_id)
    return QuotationLineItemOut.model_validate(line)


@router.get(
    "/by-version/{version_id}",
    response_model=list[QuotationLineItemOut],
    summary="List line items for one version (in display order)",
)
async def list_lines_for_version(
    version_id: uuid.UUID,
    service: ServiceDep,
) -> list[QuotationLineItemOut]:
    lines = await service.list_for_version(version_id)
    return [QuotationLineItemOut.model_validate(li) for li in lines]


@router.delete(
    "/{line_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete line item",
)
async def delete_line_item(
    line_id: uuid.UUID,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> None:
    await service.delete(line_id, actor=_current_user)
