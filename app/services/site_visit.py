import uuid
from typing import Sequence
from datetime import datetime
from fastapi import UploadFile, Depends
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.site_visit import SiteVisit
from app.models.enquiry import Enquiry
from app.models.company import Company
from app.models.attachment import Attachment
from app.models.audit_log import EnquiryAuditLog
from app.models.enums import SiteVisitStatus, AttachmentDocumentType, EnquiryAuditAction
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
        visit_count: int,
        engineer_id: uuid.UUID | None = None,
        sales_executive_id: uuid.UUID | None = None,
        client_representative: str | None = None,
        client_representative_no: str | None = None,
        status: SiteVisitStatus = SiteVisitStatus.scheduled,
        notes: str | None = None,
        requirements: str | None = None,
        measurements: str | None = None,
        existing_conditions: str | None = None,
        challenges: str | None = None,
        recommendation: str | None = None,
        photos: Sequence[UploadFile] = [],
        videos: Sequence[UploadFile] = [],
        drawings: Sequence[UploadFile] = [],
        measurement_sheets: Sequence[UploadFile] = [],
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
            visit_count=visit_count,
            enquiry_id=enquiry_id,
            company_id=enquiry.company_id,
            engineer_id=engineer_id,
            sales_executive_id=sales_executive_id,
            client_representative=client_representative,
            client_representative_no=client_representative_no,
            visit_date=visit_date,
            status=status,
            notes=notes,
            requirements=requirements,
            measurements=measurements,
            existing_conditions=existing_conditions,
            challenges=challenges,
            recommendation=recommendation,
        )
        
        self.session.add(site_visit)
        await self.session.flush()

        from datetime import UTC
        audit_log = EnquiryAuditLog(
            enquiry_id=enquiry_id,
            action=EnquiryAuditAction.site_visit_scheduled,
            action_date=datetime.now(tz=UTC),
            description=f"Site Visit {visit_number} (Visit #{visit_count}) scheduled",
        )
        self.session.add(audit_log)

        def get_category_for_doctype(doc_type: AttachmentDocumentType) -> str:
            mapping = {
                AttachmentDocumentType.photos: "photos",
                AttachmentDocumentType.videos: "videos",
                AttachmentDocumentType.drawings: "drawings",
                AttachmentDocumentType.measurement_sheets: "measurement_sheets",
                AttachmentDocumentType.other: "other",
            }
            return mapping.get(doc_type, "other")

        async def upload_group(files: Sequence[UploadFile], doc_type: AttachmentDocumentType):
            category = get_category_for_doctype(doc_type)
            for f in files:
                if not getattr(f, "filename", None):
                    continue
                stored = await self.storage.upload_uploadfile(file=f, category=category)
                attachment = Attachment(
                    file=stored.url,
                    file_type=f.content_type or "application/octet-stream",
                    document_type=doc_type,
                    site_visit_id=site_visit.id,
                )
                self.session.add(attachment)

        await upload_group(photos, AttachmentDocumentType.photos)
        await upload_group(videos, AttachmentDocumentType.videos)
        await upload_group(drawings, AttachmentDocumentType.drawings)
        await upload_group(measurement_sheets, AttachmentDocumentType.measurement_sheets)

        await self.session.commit()
        return await self.get(site_visit.id)

    async def update_site_visit(
        self,
        site_visit_id: uuid.UUID,
        *,
        visit_date: datetime | None = None,
        visit_count: int | None = None,
        engineer_id: uuid.UUID | None = None,
        sales_executive_id: uuid.UUID | None = None,
        client_representative: str | None = None,
        client_representative_no: str | None = None,
        status: SiteVisitStatus | None = None,
        notes: str | None = None,
        requirements: str | None = None,
        measurements: str | None = None,
        existing_conditions: str | None = None,
        challenges: str | None = None,
        recommendation: str | None = None,
        photos: Sequence[UploadFile] = [],
        videos: Sequence[UploadFile] = [],
        drawings: Sequence[UploadFile] = [],
        measurement_sheets: Sequence[UploadFile] = [],
    ) -> SiteVisit:
        site_visit = await self.get(site_visit_id)

        if visit_date is not None:
            site_visit.visit_date = visit_date
        if visit_count is not None:
            site_visit.visit_count = visit_count
        if engineer_id is not None:
            site_visit.engineer_id = engineer_id
        if sales_executive_id is not None:
            site_visit.sales_executive_id = sales_executive_id
        if client_representative is not None:
            site_visit.client_representative = client_representative
        if client_representative_no is not None:
            site_visit.client_representative_no = client_representative_no
        if status is not None:
            site_visit.status = status
        if notes is not None:
            site_visit.notes = notes
        if requirements is not None:
            site_visit.requirements = requirements
        if measurements is not None:
            site_visit.measurements = measurements
        if existing_conditions is not None:
            site_visit.existing_conditions = existing_conditions
        if challenges is not None:
            site_visit.challenges = challenges
        if recommendation is not None:
            site_visit.recommendation = recommendation

        def get_category_for_doctype(doc_type: AttachmentDocumentType) -> str:
            mapping = {
                AttachmentDocumentType.photos: "photos",
                AttachmentDocumentType.videos: "videos",
                AttachmentDocumentType.drawings: "drawings",
                AttachmentDocumentType.measurement_sheets: "measurement_sheets",
                AttachmentDocumentType.other: "other",
            }
            return mapping.get(doc_type, "other")

        async def upload_group(files: Sequence[UploadFile], doc_type: AttachmentDocumentType):
            category = get_category_for_doctype(doc_type)
            for f in files:
                if not getattr(f, "filename", None):
                    continue
                stored = await self.storage.upload_uploadfile(file=f, category=category)
                attachment = Attachment(
                    file=stored.url,
                    file_type=f.content_type or "application/octet-stream",
                    document_type=doc_type,
                    site_visit_id=site_visit.id,
                )
                self.session.add(attachment)

        await upload_group(photos, AttachmentDocumentType.photos)
        await upload_group(videos, AttachmentDocumentType.videos)
        await upload_group(drawings, AttachmentDocumentType.drawings)
        await upload_group(measurement_sheets, AttachmentDocumentType.measurement_sheets)

        await self.session.commit()
        return await self.get(site_visit.id)

    async def list(
        self,
        skip: int,
        limit: int,
        search: str | None = None,
        visit_date: datetime | None = None,
        engineer_id: uuid.UUID | None = None,
        status: SiteVisitStatus | None = None,
        sales_executive_id: uuid.UUID | None = None,
    ) -> tuple[Sequence[SiteVisit], int]:
        stmt = select(SiteVisit).options(
            joinedload(SiteVisit.engineer),
            joinedload(SiteVisit.sales_executive),
            selectinload(SiteVisit.attachments)
        )

        if search:
            stmt = stmt.where(
                or_(
                    SiteVisit.visit_number.ilike(f"%{search}%"),
                    SiteVisit.enquiry.has(Enquiry.enquiry_number.ilike(f"%{search}%")),
                    SiteVisit.company.has(Company.company_name.ilike(f"%{search}%")),
                )
            )

        if visit_date:
            # You may want to cast visit_date to DATE if the time portion is ignored,
            # or just exact match. Here we'll do an exact match or you can change to date match.
            # Assuming exact match or >= date match based on typical behavior.
            from sqlalchemy import cast, Date
            stmt = stmt.where(cast(SiteVisit.visit_date, Date) == cast(visit_date, Date))
        
        if engineer_id:
            stmt = stmt.where(SiteVisit.engineer_id == engineer_id)
            
        if status:
            stmt = stmt.where(SiteVisit.status == status)
            
        if sales_executive_id:
            stmt = stmt.where(SiteVisit.sales_executive_id == sales_executive_id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt) or 0

        stmt = stmt.order_by(SiteVisit.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.scalars(stmt)
        return result.all(), total

