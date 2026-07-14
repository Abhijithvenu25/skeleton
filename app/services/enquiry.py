from __future__ import annotations

import uuid
from datetime import date, UTC, datetime
from typing import TYPE_CHECKING, Sequence

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.client import Client
from app.models.project import Project
from app.models.project_type import ProjectType
from app.models.enquiry import Enquiry
from app.models.attachment import Attachment
from app.models.audit_log import EnquiryAuditLog
from app.models.enums import EnquirySource, EnquiryPriority, EnquiryStatus, AttachmentDocumentType, EnquiryAuditAction
from app.core.exceptions import NotFoundError

if TYPE_CHECKING:
    from app.storage.service import StorageService

class EnquiryService:
    def __init__(self, session: AsyncSession, storage: StorageService) -> None:
        self.session = session
        self.storage = storage

    async def get(self, enquiry_id: uuid.UUID) -> Enquiry:
        from sqlalchemy.orm import selectinload, joinedload
        stmt = (
            select(Enquiry)
            .where(Enquiry.id == enquiry_id)
            .where(Enquiry.is_deleted == False)
            .options(
                joinedload(Enquiry.company),
                joinedload(Enquiry.client),
                joinedload(Enquiry.project).joinedload(Project.project_type),
                joinedload(Enquiry.sales_executive),
                selectinload(Enquiry.attachments)
            )
        )
        enquiry = await self.session.scalar(stmt)
        if not enquiry:
            raise NotFoundError("Enquiry not found")
        return enquiry

    async def list_audit_logs(self, enquiry_id: uuid.UUID) -> Sequence[EnquiryAuditLog]:
        stmt = (
            select(EnquiryAuditLog)
            .where(EnquiryAuditLog.enquiry_id == enquiry_id)
            .order_by(EnquiryAuditLog.action_date.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list(
        self, 
        skip: int, 
        limit: int, 
        search: str | None = None,
        status: list[EnquiryStatus] | None = None,
        priority: list[EnquiryPriority] | None = None,
        sales_executive_id: list[uuid.UUID] | None = None,
        project_type_id: list[uuid.UUID] | None = None,
        is_deleted: bool = False,
    ) -> tuple[Sequence[Enquiry], int]:
        from sqlalchemy.orm import selectinload, joinedload
        from sqlalchemy import func, or_
        
        stmt = select(Enquiry).where(Enquiry.is_deleted == is_deleted).options(
            joinedload(Enquiry.company),
            joinedload(Enquiry.client),
            joinedload(Enquiry.project).joinedload(Project.project_type),
            joinedload(Enquiry.sales_executive),
            selectinload(Enquiry.attachments)
        )
        
        if search:
            stmt = stmt.where(
                or_(
                    Enquiry.enquiry_number.ilike(f"%{search}%"),
                    Enquiry.company.has(Company.company_name.ilike(f"%{search}%")),
                    Enquiry.client.has(Client.client_contact.ilike(f"%{search}%")),
                    Enquiry.client.has(Client.alternate_contact.ilike(f"%{search}%")),
                    Enquiry.project.has(Project.project_name.ilike(f"%{search}%")),
                )
            )

        if status:
            stmt = stmt.where(Enquiry.status.in_(status))
        if priority:
            stmt = stmt.where(Enquiry.priority.in_(priority))
        if sales_executive_id:
            stmt = stmt.where(Enquiry.sales_executive_id.in_(sales_executive_id))
        if project_type_id:
            stmt = stmt.where(Enquiry.project.has(Project.project_type_id.in_(project_type_id)))
            
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt) or 0
        
        stmt = stmt.order_by(Enquiry.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.scalars(stmt)
        return result.all(), total

    async def list_lost(
        self,
        skip: int,
        limit: int,
        search: str | None = None,
        stage_lost: str | None = None,
        lost_reason: str | None = None,
    ) -> tuple[Sequence[Enquiry], int]:
        from sqlalchemy.orm import joinedload
        from sqlalchemy import func, or_

        stmt = select(Enquiry).where(
            Enquiry.is_deleted == False,
            Enquiry.status == EnquiryStatus.lost
        ).options(
            joinedload(Enquiry.company)
        )

        if search:
            stmt = stmt.where(
                or_(
                    Enquiry.enquiry_number.ilike(f"%{search}%"),
                    Enquiry.company.has(Company.company_name.ilike(f"%{search}%")),
                )
            )

        if stage_lost:
            stmt = stmt.where(Enquiry.stage_lost == stage_lost)

        if lost_reason:
            stmt = stmt.where(Enquiry.lost_reason == lost_reason)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt) or 0

        stmt = stmt.order_by(Enquiry.date_lost.desc().nulls_last()).offset(skip).limit(limit)
        result = await self.session.scalars(stmt)
        return result.all(), total

    async def update_enquiry(
        self,
        enquiry_id: uuid.UUID,
        *,
        company_name: str | None = None,
        company_website: str | None = None,
        company_address: str | None = None,
        company_city: str | None = None,
        company_state: str | None = None,
        company_country: str | None = None,
        company_pincode: str | None = None,
        contact_person: str | None = None,
        designation: str | None = None,
        mobile: str | None = None,
        alternate_mobile: str | None = None,
        email: str | None = None,
        project_name: str | None = None,
        project_type_id: uuid.UUID | None = None,
        project_location: str | None = None,
        estimated_budget: float | None = None,
        expected_start_date: date | None = None,
        source: EnquirySource | None = None,
        priority: EnquiryPriority | None = None,
        sales_executive_id: uuid.UUID | None = None,
        project_description: str | None = None,
        remarks: str | None = None,
        stage_lost: str | None = None,
        lost_reason: str | None = None,
        date_lost: date | None = None,
        follow_up_date: date | None = None,
        reinstated: bool | None = None,
        status: EnquiryStatus | None = None,
        boq_files: Sequence[UploadFile | str] | None = None,
        drawings_files: Sequence[UploadFile | str] | None = None,
        photos_files: Sequence[UploadFile | str] | None = None,
        tender_files: Sequence[UploadFile | str] | None = None,
        other_files: Sequence[UploadFile | str] | None = None,
    ) -> Enquiry:
        enquiry = await self.get(enquiry_id)
        old_status = enquiry.status
        
        # update company
        if enquiry.company:
            if company_name is not None: enquiry.company.company_name = company_name
            if company_website is not None: enquiry.company.company_website = company_website
            if company_address is not None: enquiry.company.address_line1 = company_address
            if company_city is not None: enquiry.company.city = company_city
            if company_state is not None: enquiry.company.state = company_state
            if company_country is not None: enquiry.company.country = company_country
            if company_pincode is not None: enquiry.company.pincode = company_pincode
            
        # update client
        if enquiry.client:
            if contact_person is not None: enquiry.client.client_name = contact_person
            if designation is not None: enquiry.client.client_designation = designation
            if mobile is not None: enquiry.client.client_contact = mobile
            if alternate_mobile is not None: enquiry.client.alternate_contact = alternate_mobile
            if email is not None: enquiry.client.email = email
            
        # update project
        if enquiry.project:
            if project_name is not None: enquiry.project.project_name = project_name
            if project_type_id is not None:
                # check if valid
                stmt = select(ProjectType).where(ProjectType.id == project_type_id)
                if not await self.session.scalar(stmt):
                    raise NotFoundError("Project type not found")
                enquiry.project.project_type_id = project_type_id
            if project_location is not None: enquiry.project.project_location = project_location
            if estimated_budget is not None: enquiry.project.estimated_budget = estimated_budget
            if expected_start_date is not None: enquiry.project.expected_start_date = expected_start_date
            
        # update enquiry
        if source is not None: enquiry.enquiry_source = source
        if priority is not None: enquiry.priority = priority
        if sales_executive_id is not None: enquiry.sales_executive_id = sales_executive_id
        if project_description is not None:
            enquiry.description = project_description
        if remarks is not None:
            enquiry.remarks = remarks
        
        if stage_lost is not None:
            enquiry.stage_lost = stage_lost
        if lost_reason is not None:
            enquiry.lost_reason = lost_reason
        if date_lost is not None:
            enquiry.date_lost = date_lost
        if follow_up_date is not None:
            enquiry.follow_up_date = follow_up_date
        if reinstated is not None:
            enquiry.reinstated = reinstated
        if status is not None:
            enquiry.status = status
            if old_status != status:
                if status == EnquiryStatus.lost:
                    audit_log = EnquiryAuditLog(
                        enquiry_id=enquiry.id,
                        action=EnquiryAuditAction.enquiry_lost,
                        action_date=datetime.now(tz=UTC),
                        description="Enquiry marked as lost",
                    )
                    self.session.add(audit_log)
                elif old_status == EnquiryStatus.lost and status != EnquiryStatus.lost:
                    audit_log = EnquiryAuditLog(
                        enquiry_id=enquiry.id,
                        action=EnquiryAuditAction.enquiry_reinstated,
                        action_date=datetime.now(tz=UTC),
                        description=f"Enquiry reinstated to {status.value}",
                    )
                    self.session.add(audit_log)

        def get_category_for_doctype(doc_type: AttachmentDocumentType) -> str:
            mapping = {
                AttachmentDocumentType.boq: "boq",
                AttachmentDocumentType.drawings: "drawings",
                AttachmentDocumentType.photos: "photos",
                AttachmentDocumentType.tender: "pdf",
                AttachmentDocumentType.other: "other",
            }
            return mapping.get(doc_type, "other")

        async def upload_group(files: Sequence[UploadFile | str] | None, doc_type: AttachmentDocumentType):
            if files is None: return
            category = get_category_for_doctype(doc_type)
            
            retained_urls = {f for f in files if isinstance(f, str)}
            
            stmt = select(Attachment).where(
                Attachment.enquiry_id == enquiry.id,
                Attachment.document_type == doc_type
            )
            existing_atts = (await self.session.scalars(stmt)).all()
            for att in existing_atts:
                if att.file not in retained_urls:
                    self.session.delete(att)

            for f in files:
                if not getattr(f, "filename", None):
                    continue
                stored = await self.storage.upload_uploadfile(file=f, category=category)
                attachment = Attachment(
                    file=stored.url,
                    file_name=f.filename,
                    file_type=f.content_type or "application/octet-stream",
                    document_type=doc_type,
                    enquiry_id=enquiry.id,
                )
                self.session.add(attachment)

        await upload_group(boq_files, AttachmentDocumentType.boq)
        await upload_group(drawings_files, AttachmentDocumentType.drawings)
        await upload_group(photos_files, AttachmentDocumentType.photos)
        await upload_group(tender_files, AttachmentDocumentType.tender)
        await upload_group(other_files, AttachmentDocumentType.other)

        await self.session.commit()
        await self.session.refresh(enquiry)
        return enquiry

    async def delete(self, enquiry_id: uuid.UUID) -> None:
        enquiry = await self.get(enquiry_id)
        enquiry.is_deleted = True
        enquiry.deleted_at = datetime.now(tz=UTC)
        await self.session.commit()

    async def delete_attachment(self, attachment_id: uuid.UUID) -> None:
        stmt = select(Attachment).where(Attachment.id == attachment_id)
        attachment = await self.session.scalar(stmt)
        if not attachment:
            raise NotFoundError("Attachment not found")
        
        await self.session.delete(attachment)
        await self.session.commit()

    async def create_enquiry(
        self,
        *,
        company_name: str,
        company_website: str | None,
        company_address: str | None,
        company_city: str | None,
        company_state: str | None,
        company_country: str | None,
        company_pincode: str | None,
        contact_person: str,
        designation: str | None,
        mobile: str | None,
        alternate_mobile: str | None,
        email: str | None,
        project_name: str,
        project_type_id: uuid.UUID,
        project_location: str | None,
        estimated_budget: float | None,
        expected_start_date: date | None,
        source: EnquirySource | None,
        priority: EnquiryPriority,
        sales_executive_id: uuid.UUID | None = None,
        project_description: str | None = None,
        remarks: str | None = None,
        boq_files: Sequence[UploadFile | str] | None = None,
        drawings_files: Sequence[UploadFile | str] | None = None,
        photos_files: Sequence[UploadFile | str] | None = None,
        tender_files: Sequence[UploadFile | str] | None = None,
        other_files: Sequence[UploadFile | str] | None = None,
    ) -> Enquiry:
        company = Company(
            company_name=company_name,
            company_website=company_website,
            address_line1=company_address,
            city=company_city,
            state=company_state,
            country=company_country,
            pincode=company_pincode,
        )
        self.session.add(company)

        client = Client(
            client_name=contact_person,
            client_designation=designation,
            client_contact=mobile,
            alternate_contact=alternate_mobile,
            email=email,
        )
        self.session.add(client)

        stmt = select(ProjectType).where(ProjectType.id == project_type_id)
        if not await self.session.scalar(stmt):
            raise NotFoundError("Project type not found")

        project = Project(
            project_name=project_name,
            project_type_id=project_type_id,
            project_location=project_location,
            estimated_budget=estimated_budget,
            expected_start_date=expected_start_date,
        )
        self.session.add(project)

        await self.session.flush()

        last_enquiry = await self.session.scalar(
            select(Enquiry.enquiry_number)
            .where(Enquiry.enquiry_number.like("ENQ-%"))
            .order_by(Enquiry.created_at.desc())
            .limit(1)
        )
        
        if last_enquiry:
            try:
                last_num = int(last_enquiry.split("-")[1])
                new_num = last_num + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1
            
        enquiry_number = f"ENQ-{new_num:03d}"

        enquiry = Enquiry(
            enquiry_number=enquiry_number,
            enquiry_date=datetime.now(tz=UTC).date(),
            company_id=company.id,
            client_id=client.id,
            project_id=project.id,
            enquiry_source=source,
            priority=priority,
            sales_executive_id=sales_executive_id,
            description=project_description,
            remarks=remarks,
            status=EnquiryStatus.enquiry,
        )
        self.session.add(enquiry)
        await self.session.flush()

        audit_log = EnquiryAuditLog(
            enquiry_id=enquiry.id,
            action=EnquiryAuditAction.enquiry_created,
            action_date=datetime.now(tz=UTC),
            description=f"Enquiry {enquiry_number} created",
        )
        self.session.add(audit_log)

        def get_category_for_doctype(doc_type: AttachmentDocumentType) -> str:
            mapping = {
                AttachmentDocumentType.boq: "boq",
                AttachmentDocumentType.drawings: "drawings",
                AttachmentDocumentType.photos: "photos",
                AttachmentDocumentType.tender: "pdf",
                AttachmentDocumentType.other: "other",
            }
            return mapping.get(doc_type, "other")

        async def upload_group(files: Sequence[UploadFile | str], doc_type: AttachmentDocumentType):
            category = get_category_for_doctype(doc_type)
            for f in files:
                if not getattr(f, "filename", None):
                    continue
                stored = await self.storage.upload_uploadfile(file=f, category=category)
                attachment = Attachment(
                    file=stored.url,
                    file_name=f.filename,
                    file_type=f.content_type or "application/octet-stream",
                    document_type=doc_type,
                    enquiry_id=enquiry.id,
                )
                self.session.add(attachment)

        await upload_group(boq_files, AttachmentDocumentType.boq)
        await upload_group(drawings_files, AttachmentDocumentType.drawings)
        await upload_group(photos_files, AttachmentDocumentType.photos)
        await upload_group(tender_files, AttachmentDocumentType.tender)
        await upload_group(other_files, AttachmentDocumentType.other)

        await self.session.commit()
        return await self.get(enquiry.id)
