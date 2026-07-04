from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession
from app.api.v1._response import created_single, ok_list, ok_single
from app.schemas.common import ApiResponse, MessageResponse
from app.schemas.project_type import (
    ProjectTypeList,
    ProjectTypeOut,
    ProjectTypeCreate,
    ProjectTypePatch,
)
from app.services.project_type import ProjectTypeService

router = APIRouter(prefix="/project-types", tags=["project_types"])

def _get_pt_service(db: DbSession) -> ProjectTypeService:
    return ProjectTypeService(session=db)

ProjectTypeServiceDep = Annotated[ProjectTypeService, Depends(_get_pt_service)]

@router.get(
    "",
    response_model=ApiResponse[ProjectTypeOut],
    summary="List project types",
)
async def list_project_types(
    service: ProjectTypeServiceDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
) -> ApiResponse[ProjectTypeOut]:
    rows, total = await service.list(skip, limit, search)
    out = [ProjectTypeOut.model_validate(r) for r in rows]
    return ok_list(
        out,
        page=(skip // limit) + 1,
        size=limit,
        total=total,
        message="Project types fetched successfully."
    )

@router.post(
    "",
    response_model=ApiResponse[ProjectTypeOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project type",
)
async def create_project_type(
    payload: ProjectTypeCreate,
    service: ProjectTypeServiceDep,
    current_user: CurrentUser,
) -> ApiResponse[ProjectTypeOut]:
    project_type = await service.create(type_name=payload.type_name, description=payload.description)
    return created_single(
        ProjectTypeOut.model_validate(project_type),
        "Project type created successfully.",
    )

@router.get(
    "/{type_id}",
    response_model=ApiResponse[ProjectTypeOut],
    summary="Get a project type by ID",
)
async def get_project_type(
    type_id: uuid.UUID,
    service: ProjectTypeServiceDep,
    current_user: CurrentUser,
) -> ApiResponse[ProjectTypeOut]:
    project_type = await service.get(type_id)
    return ok_single(
        ProjectTypeOut.model_validate(project_type),
        "Project type fetched successfully.",
    )

@router.patch(
    "/{type_id}",
    response_model=ApiResponse[ProjectTypeOut],
    summary="Update a project type",
)
async def update_project_type(
    type_id: uuid.UUID,
    payload: ProjectTypePatch,
    service: ProjectTypeServiceDep,
    current_user: CurrentUser,
) -> ApiResponse[ProjectTypeOut]:
    project_type = await service.update(
        type_id=type_id,
        type_name=payload.type_name,
        description=payload.description,
    )
    return ok_single(
        ProjectTypeOut.model_validate(project_type),
        "Project type updated successfully.",
    )

@router.delete(
    "/{type_id}",
    response_model=ApiResponse[MessageResponse],
    summary="Delete a project type",
)
async def delete_project_type(
    type_id: uuid.UUID,
    service: ProjectTypeServiceDep,
    current_user: CurrentUser,
) -> ApiResponse[MessageResponse]:
    await service.delete(type_id)
    return ok_single(
        MessageResponse(message="Project type deleted successfully."),
        "Project type deleted successfully.",
    )
