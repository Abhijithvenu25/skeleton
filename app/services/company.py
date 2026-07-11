from typing import Sequence
from sqlalchemy import select, func, Row
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.company import Company
from app.models.enquiry import Enquiry

class CompanyService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_companies_with_enquiry(
        self,
        skip: int,
        limit: int,
        search: str | None = None,
    ) -> tuple[Sequence[Row], int]:
        stmt = (
            select(
                Company.id.label("company_id"),
                Company.company_name,
                Enquiry.id.label("enquiry_id")
            )
            .outerjoin(Enquiry, Enquiry.company_id == Company.id)
        )
        
        if search:
            stmt = stmt.where(Company.company_name.ilike(f"%{search}%"))
            
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt) or 0
        
        stmt = stmt.order_by(Company.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.all(), total
