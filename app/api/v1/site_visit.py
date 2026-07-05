from fastapi import APIRouter, Form, UploadFile, File, status, Depends
import uuid
from datetime import datetime
from typing import Annotated
from app.api.deps import CurrentUser, DbSession
from app.api.v1.uploads import StorageServiceDep
from app.schemas.common import ApiResponse
from app.schemas.site_visit import SiteVisitOut, AttachmentFile
from app.services.site_visit import SiteVisitService
from app.models.enums import SiteVisitStatus
from app.api.v1._response import created_single

router = APIRouter(prefix="/site-visits", tags=["site_visits"])

def _get_site_visit_service(db: DbSession, storage: StorageServiceDep) -> SiteVisitService:
    return SiteVisitService(db, storage)

SiteVisitServiceDep = Annotated[SiteVisitService, Depends(_get_site_visit_service)]

def build_site_visit_out(visit) -> SiteVisitOut:
    return SiteVisitOut(
        id=visit.id,
        visit_number=visit.visit_number,
        enquiry_id=visit.enquiry_id,
        company_id=visit.company_id,
        engineer=visit.engineer.full_name if visit.engineer else None,
        sales_executive=visit.sales_executive.full_name if visit.sales_executive else None,
        visit_date=visit.visit_date,
        status=visit.status,
        notes=visit.notes,
        attachments=[AttachmentFile(id=a.id, url=a.file) for a in visit.attachments] if visit.attachments else []
    )

@router.post(
    "",
    response_model=ApiResponse[SiteVisitOut],
    status_code=status.HTTP_201_CREATED,
)
async def create_site_visit_api(
    service: SiteVisitServiceDep,
    enquiry_id: uuid.UUID = Form(...),
    visit_date: datetime = Form(...),
    engineer_id: uuid.UUID | None = Form(None),
    sales_executive_id: uuid.UUID | None = Form(None),
    visit_status: SiteVisitStatus = Form(SiteVisitStatus.scheduled, alias="status"),
    notes: str | None = Form(None),
    attachments: list[UploadFile] = File(default=[]),
) -> ApiResponse[SiteVisitOut]:
    
    visit = await service.create_site_visit(
        enquiry_id=enquiry_id,
        visit_date=visit_date,
        engineer_id=engineer_id,
        sales_executive_id=sales_executive_id,
        status=visit_status,
        notes=notes,
        attachments=attachments,
    )
    
    return created_single(
        build_site_visit_out(visit),
        message="Site visit created successfully.",
    )
