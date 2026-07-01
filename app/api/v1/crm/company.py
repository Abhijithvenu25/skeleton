"""Company endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import Page
from app.schemas.crm.company import (
    CompanyIn,
    CompanyOut,
    CompanyPatch,
)
from app.services.crm._common import build_page
from app.services.crm.company import CompanyService

router = APIRouter(prefix="/companies", tags=["crm-companies"])


def _get_service(session: DbSession) -> CompanyService:
    return CompanyService(session=session)


ServiceDep = Annotated[CompanyService, Depends(_get_service)]


@router.get("", response_model=Page[CompanyOut], summary="List active companies")
async def list_companies(
    service: ServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> Page[CompanyOut]:
    items, total = await service.list(page=page, size=size)
    return build_page([CompanyOut.model_validate(c) for c in items], total, page, size)


@router.post("", response_model=CompanyOut, status_code=status.HTTP_201_CREATED, summary="Create company")
async def create_company(
    payload: CompanyIn,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> CompanyOut:
    company = await service.create(payload, actor=_current_user)
    return CompanyOut.model_validate(company)


@router.get("/{company_id}", response_model=CompanyOut, summary="Get company")
async def get_company(company_id: uuid.UUID, service: ServiceDep) -> CompanyOut:
    company = await service.get_by_id(company_id)
    return CompanyOut.model_validate(company)


@router.patch("/{company_id}", response_model=CompanyOut, summary="Update company")
async def update_company(
    company_id: uuid.UUID,
    payload: CompanyPatch,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> CompanyOut:
    company = await service.update(company_id, payload, actor=_current_user)
    return CompanyOut.model_validate(company)


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete company",
)
async def delete_company(
    company_id: uuid.UUID,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> None:
    await service.soft_delete(company_id, actor=_current_user)
