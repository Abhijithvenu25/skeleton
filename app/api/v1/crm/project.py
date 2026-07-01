"""Project endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import Page
from app.schemas.crm.project import (
    ProjectIn,
    ProjectOut,
    ProjectPatch,
)
from app.services.crm._common import build_page
from app.services.crm.project import ProjectService

router = APIRouter(prefix="/projects", tags=["crm-projects"])


def _get_service(session: DbSession) -> ProjectService:
    return ProjectService(session=session)


ServiceDep = Annotated[ProjectService, Depends(_get_service)]


@router.get("", response_model=Page[ProjectOut], summary="List projects")
async def list_projects(
    service: ServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    company_id: uuid.UUID | None = Query(None),
) -> Page[ProjectOut]:
    items, total = await service.list(page=page, size=size, company_id=company_id)
    return build_page([ProjectOut.model_validate(p) for p in items], total, page, size)


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED, summary="Create project")
async def create_project(
    payload: ProjectIn,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> ProjectOut:
    project = await service.create(payload, actor=_current_user)
    return ProjectOut.model_validate(project)


@router.get("/{project_id}", response_model=ProjectOut, summary="Get project")
async def get_project(project_id: uuid.UUID, service: ServiceDep) -> ProjectOut:
    project = await service.get_by_id(project_id)
    return ProjectOut.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectOut, summary="Update project")
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectPatch,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> ProjectOut:
    project = await service.update(project_id, payload, actor=_current_user)
    return ProjectOut.model_validate(project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete project",
)
async def delete_project(
    project_id: uuid.UUID,
    service: ServiceDep,
    _current_user: CurrentUser,
) -> None:
    await service.soft_delete(project_id, actor=_current_user)
