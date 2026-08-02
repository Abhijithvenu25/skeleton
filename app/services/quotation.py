import uuid
from typing import Sequence
from fastapi import HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.quotation import Quotation
from app.models.quotation_line_item import QuotationLineItem
from app.models.enquiry import Enquiry
from app.models.audit_log import EnquiryAuditLog
from app.models.enums import EnquiryAuditAction
from app.schemas.quotation import QuotationCreate

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
