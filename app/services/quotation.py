import uuid
from typing import Sequence
from fastapi import HTTPException, status
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.quotation import Quotation
from app.models.quotation_line_item import QuotationLineItem
from app.models.enquiry import Enquiry
from app.models.audit_log import EnquiryAuditLog
from app.models.enums import EnquiryAuditAction, EnquiryStatus
from app.schemas.quotation import QuotationCreate, QuotationUpdate

class QuotationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _generate_quotation_number(self) -> str:
        stmt = (
            select(Quotation.quotation_number)
            .where(Quotation.quotation_number.like("QUO-%"))
            .order_by(desc(Quotation.created_at))
            .limit(1)
        )
        last_num_str = await self.session.scalar(stmt)
        if last_num_str:
            try:
                last_num = int(last_num_str.split("-")[1])
                new_num = last_num + 1
            except ValueError:
                new_num = 1
        else:
            new_num = 1
        return f"QUO-{new_num:03d}"

    async def create(self, user_id: uuid.UUID, data: QuotationCreate) -> Quotation:
        # Fetch enquiry to get company_id
        enquiry = await self.session.get(Enquiry, data.enquiry_id)
        if not enquiry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enquiry not found",
            )
            
        # Update Enquiry Status
        enquiry.status = EnquiryStatus.quotation
            
        quotation_number = await self._generate_quotation_number()
        
        quotation = Quotation(
            quotation_number=quotation_number,
            subject=data.subject,
            enquiry_id=data.enquiry_id,
            company_id=enquiry.company_id,
            executive_id=user_id,
            quotation_date=data.quotation_date,
            valid_until=data.valid_until,
            site_visit_id=data.site_visit_id,
            subtotal=data.subtotal,
            global_discount=data.global_discount,
            vat_rate=data.vat_rate,
            expected_profit=data.expected_profit,
            total_estimated_cost=data.total_estimated_cost,
            terms_and_conditions=data.terms_and_conditions,
            remarks=data.remarks,
            amount=data.amount,
            is_draft=data.is_draft,
        )
        self.session.add(quotation)
        
        for item in data.line_items:
            line_item = QuotationLineItem(
                quotation=quotation,
                description=item.description,
                quantity=item.quantity,
                unit=item.unit,
                rate=item.rate,
                amount=item.amount,
                estimated_cost=item.estimated_cost,
                profit_estimator=item.profit_estimator,
            )
            self.session.add(line_item)
            
        audit_log = EnquiryAuditLog(
            enquiry_id=enquiry.id,
            action=EnquiryAuditAction.quotation_generated,
            description=f"Quotation {quotation_number} generated",
        )
        self.session.add(audit_log)
        
        await self.session.commit()
        await self.session.refresh(quotation)
        
        stmt = select(Quotation).options(selectinload(Quotation.line_items)).where(Quotation.id == quotation.id)
        return await self.session.scalar(stmt)

    async def update(self, quotation_id: uuid.UUID, data: QuotationUpdate) -> Quotation:
        stmt = select(Quotation).options(selectinload(Quotation.line_items)).where(Quotation.id == quotation_id)
        quotation = await self.session.scalar(stmt)
        if not quotation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quotation not found",
            )
            
        update_data = data.model_dump(exclude_unset=True, exclude={"line_items"})
        for field, value in update_data.items():
            setattr(quotation, field, value)
            
        if data.line_items is not None:
            existing_items_map = {item.id: item for item in quotation.line_items}
            incoming_item_ids = {item.id for item in data.line_items if item.id is not None}
            
            # Delete items not in incoming payload
            for item_id, existing_item in existing_items_map.items():
                if item_id not in incoming_item_ids:
                    await self.session.delete(existing_item)
            
            # Update existing or create new
            for item in data.line_items:
                if item.id and item.id in existing_items_map:
                    # Update
                    existing_item = existing_items_map[item.id]
                    existing_item.description = item.description
                    existing_item.quantity = item.quantity
                    existing_item.unit = item.unit
                    existing_item.rate = item.rate
                    existing_item.amount = item.amount
                    existing_item.estimated_cost = item.estimated_cost
                    existing_item.profit_estimator = item.profit_estimator
                else:
                    # Create new
                    new_item = QuotationLineItem(
                        quotation_id=quotation.id,
                        description=item.description,
                        quantity=item.quantity,
                        unit=item.unit,
                        rate=item.rate,
                        amount=item.amount,
                        estimated_cost=item.estimated_cost,
                        profit_estimator=item.profit_estimator,
                    )
                    self.session.add(new_item)
                    
        await self.session.commit()
        await self.session.refresh(quotation)
        
        # Refetch to get fresh line items collection after deletes/inserts
        stmt = select(Quotation).options(selectinload(Quotation.line_items)).where(Quotation.id == quotation.id)
        return await self.session.scalar(stmt)

    async def get(self, quotation_id: uuid.UUID) -> Quotation:
        stmt = select(Quotation).options(selectinload(Quotation.line_items)).where(Quotation.id == quotation_id)
        quotation = await self.session.scalar(stmt)
        if not quotation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quotation not found",
            )
        return quotation

    async def list_all(self, page: int = 1, size: int = 10) -> tuple[Sequence[Quotation], int]:
        count_stmt = select(func.count()).select_from(Quotation)
        total = await self.session.scalar(count_stmt) or 0
        
        stmt = (
            select(Quotation)
            .options(selectinload(Quotation.line_items))
            .order_by(desc(Quotation.created_at))
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.session.scalars(stmt)
        return result.all(), total
