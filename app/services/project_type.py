from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ConflictError, NotFoundError
from app.models.project_type import ProjectType
from app.models.project import Project

class ProjectTypeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get_or_404(self, type_id: uuid.UUID) -> ProjectType:
        project_type = await ProjectType.get_by_id(self.session, type_id)
        if not project_type:
            raise NotFoundError(f"ProjectType {type_id} not found")
        return project_type

    async def list(self, skip: int, limit: int, search: str | None = None) -> tuple[list[ProjectType], int]:
        where = None
        if search:
            pattern = f"%{search.strip()}%"
            where = or_(ProjectType.type_name.ilike(pattern), ProjectType.description.ilike(pattern))

        count_stmt = select(func.count()).select_from(ProjectType)
        list_stmt = select(ProjectType).order_by(ProjectType.type_name.asc())
        
        if where is not None:
            count_stmt = count_stmt.where(where)
            list_stmt = list_stmt.where(where)

        total = int(await self.session.scalar(count_stmt) or 0)
        result = await self.session.scalars(list_stmt.offset(skip).limit(limit))
        rows: list[ProjectType] = list(result.all())
        return rows, total

    async def get(self, type_id: uuid.UUID) -> ProjectType:
        return await self._get_or_404(type_id)

    async def create(self, type_name: str, description: str | None) -> ProjectType:
        stmt = select(ProjectType).where(ProjectType.type_name == type_name)
        if await self.session.scalar(stmt) is not None:
            raise ConflictError("Project type with this name already exists")
            
        project_type = ProjectType(type_name=type_name, description=description)
        self.session.add(project_type)
        try:
            await self.session.commit()
            await self.session.refresh(project_type)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Project type with this name already exists") from exc
        return project_type

    async def update(self, type_id: uuid.UUID, type_name: str | None, description: str | None) -> ProjectType:
        project_type = await self._get_or_404(type_id)
        
        if type_name is not None and type_name != project_type.type_name:
            stmt = select(ProjectType).where(ProjectType.type_name == type_name)
            if await self.session.scalar(stmt) is not None:
                raise ConflictError("Project type with this name already exists")
            project_type.type_name = type_name
            
        if description is not None:
            project_type.description = description
            
        await self.session.commit()
        await self.session.refresh(project_type)
        return project_type

    async def delete(self, type_id: uuid.UUID) -> None:
        project_type = await self._get_or_404(type_id)
        
        stmt = select(Project).where(Project.project_type_id == type_id).limit(1)
        if await self.session.scalar(stmt) is not None:
            raise ConflictError("Cannot delete ProjectType because it is assigned to existing projects.")
            
        await self.session.delete(project_type)
        await self.session.commit()
