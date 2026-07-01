"""Project service."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.project import Project
from app.models.user import User
from app.schemas.crm.project import ProjectIn, ProjectPatch
from app.services.crm._common import (
    apply_audit_create,
    apply_audit_soft_delete,
    apply_audit_update,
    paginate,
)


class ProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self,
        *,
        page: int = 1,
        size: int = 20,
        company_id: uuid.UUID | None = None,
    ) -> tuple[list[Project], int]:
        where = [Project.deleted_at.is_(None)]
        if company_id is not None:
            where.append(Project.company_id == company_id)
        return await paginate(
            self.session,
            Project,
            page=page,
            size=size,
            order_by=Project.name,
            where=where,
        )

    async def get_by_id(self, project_id: uuid.UUID) -> Project:
        project = await Project.get_by_id(self.session, project_id)
        if project is None or project.deleted_at is not None:
            raise NotFoundError(f"Project {project_id} not found")
        return project

    async def create(self, payload: ProjectIn, *, actor: User) -> Project:
        project = Project(
            company_id=payload.company_id,
            name=payload.name,
            project_type=payload.project_type.value,
            location=payload.location,
            description=payload.description,
        )
        apply_audit_create(project, actor=actor)
        self.session.add(project)
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def update(
        self, project_id: uuid.UUID, payload: ProjectPatch, *, actor: User
    ) -> Project:
        project = await self.get_by_id(project_id)
        if payload.name is not None:
            project.name = payload.name
        if payload.project_type is not None:
            project.project_type = payload.project_type.value
        if payload.location is not None:
            project.location = payload.location
        if payload.description is not None:
            project.description = payload.description
        apply_audit_update(project, actor=actor)
        await self.session.commit()
        return project

    async def soft_delete(self, project_id: uuid.UUID, *, actor: User) -> None:
        project = await self.get_by_id(project_id)
        apply_audit_soft_delete(project, actor=actor)
        await self.session.commit()