import uuid
from typing import Sequence
from datetime import datetime
from fastapi import UploadFile, Depends
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.site_visit import SiteVisit
from app.models.enquiry import Enquiry
from app.models.attachment import Attachment
from app.models.enums import SiteVisitStatus, AttachmentDocumentType
from app.core.exceptions import NotFoundError
from app.storage.service import StorageService

class SiteVisitService:
    def __init__(self, session: AsyncSession, storage: StorageService):
        self.session = session
        self.storage = storage

    async def get(self, site_visit_id: uuid.UUID) -> SiteVisit:
        stmt = (
            select(SiteVisit)
            .where(SiteVisit.id == site_visit_id)
            .options(
                joinedload(SiteVisit.engineer),
                joinedload(SiteVisit.sales_executive),
                selectinload(SiteVisit.attachments)
            )
        )
        visit = await self.session.scalar(stmt)
        if not visit:
            raise NotFoundError("Site Visit not found")
        return visit

    async def create_site_visit(
        self,
        *,
        enquiry_id: uuid.UUID,
        visit_date: datetime,
        engineer_id: uuid.UUID | None = None,
        sales_executive_id: uuid.UUID | None = None,
        status: SiteVisitStatus = SiteVisitStatus.scheduled,
        notes: str | None = None,
        attachments: Sequence[UploadFile] = [],
    ) -> SiteVisit:
        # Check if enquiry exists and get company_id
        stmt = select(Enquiry).where(Enquiry.id == enquiry_id)
        enquiry = await self.session.scalar(stmt)
        if not enquiry:
            raise NotFoundError("Enquiry not found")

        # Get latest visit number
        last_visit = await self.session.scalar(
            select(SiteVisit.visit_number)
            .where(SiteVisit.visit_number.like("VIS-%"))
            .order_by(SiteVisit.created_at.desc())
            .limit(1)
        )
        if last_visit:
            try:
                new_num = int(last_visit.split("-")[1]) + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1
        
        visit_number = f"VIS-{new_num:03d}"

        site_visit = SiteVisit(
            visit_number=visit_number,
            enquiry_id=enquiry_id,
            company_id=enquiry.company_id,
            engineer_id=engineer_id,
            sales_executive_id=sales_executive_id,
            visit_date=visit_date,
            status=status,
            notes=notes,
        )
        
        self.session.add(site_visit)
        await self.session.flush()

        if attachments:
            for f in attachments:
                if not getattr(f, "filename", None):
                    continue
                stored = await self.storage.upload_uploadfile(file=f, category="other")
                attachment = Attachment(
                    file=stored.url,
                    file_type=f.content_type or "application/octet-stream",
                    document_type=AttachmentDocumentType.other,
                    site_visit_id=site_visit.id,
                )
                self.session.add(attachment)

        await self.session.commit()
        return await self.get(site_visit.id)

