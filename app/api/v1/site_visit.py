from fastapi import APIRouter, Form, UploadFile, File, status, Depends, Query
import uuid
from datetime import datetime
from typing import Annotated
from app.api.deps import CurrentUser, DbSession
from app.api.v1.uploads import StorageServiceDep
from app.schemas.common import ApiResponse
from app.schemas.site_visit import SiteVisitOut, SiteVisitAttachmentsOut, AttachmentFile
from app.services.site_visit import SiteVisitService
from app.models.enums import SiteVisitStatus
from app.api.v1._response import created_single, ok_list, ok_single

router = APIRouter(prefix="/site-visits", tags=["site_visits"])

def _get_site_visit_service(db: DbSession, storage: StorageServiceDep) -> SiteVisitService:
    return SiteVisitService(db, storage)

SiteVisitServiceDep = Annotated[SiteVisitService, Depends(_get_site_visit_service)]

def build_site_visit_out(visit) -> SiteVisitOut:
    photos = []
    videos = []
    drawings = []
    measurement_sheets = []

    if visit.attachments:
        for a in visit.attachments:
            file_obj = AttachmentFile(id=a.id, url=a.file)
            if a.document_type == "Photos":
                photos.append(file_obj)
            elif a.document_type == "Videos":
                videos.append(file_obj)
            elif a.document_type == "Drawings":
                drawings.append(file_obj)
            elif a.document_type == "Measurement Sheets":
                measurement_sheets.append(file_obj)

    return SiteVisitOut(
        id=visit.id,
        visit_number=visit.visit_number,
        visit_count=visit.visit_count,
        enquiry_id=visit.enquiry_id,
        company_id=visit.company_id,
        engineer=visit.engineer.full_name if visit.engineer else None,
        sales_executive=visit.sales_executive.full_name if visit.sales_executive else None,
        visit_date=visit.visit_date,
        status=visit.status,
        client_representative=visit.client_representative,
        client_representative_no=visit.client_representative_no,
        notes=visit.notes,
        requirements=visit.requirements,
        measurements=visit.measurements,
        existing_conditions=visit.existing_conditions,
        challenges=visit.challenges,
        recommendation=visit.recommendation,
        attachments=SiteVisitAttachmentsOut(
            photos=photos,
            videos=videos,
            drawings=drawings,
            measurement_sheets=measurement_sheets,
        )
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
    visit_count: int = Form(...),
    engineer_id: uuid.UUID | None = Form(None),
    sales_executive_id: uuid.UUID | None = Form(None),
    client_representative: str | None = Form(None),
    client_representative_no: str | None = Form(None),
    visit_status: SiteVisitStatus = Form(SiteVisitStatus.scheduled, alias="status"),
    notes: str | None = Form(None),
    requirements: str | None = Form(None),
    measurements: str | None = Form(None),
    existing_conditions: str | None = Form(None),
    challenges: str | None = Form(None),
    recommendation: str | None = Form(None),
    photos: list[UploadFile] = File(default=[]),
    videos: list[UploadFile] = File(default=[]),
    drawings: list[UploadFile] = File(default=[]),
    measurement_sheets: list[UploadFile] = File(default=[]),
) -> ApiResponse[SiteVisitOut]:
    
    visit = await service.create_site_visit(
        enquiry_id=enquiry_id,
        visit_date=visit_date,
        visit_count=visit_count,
        engineer_id=engineer_id,
        sales_executive_id=sales_executive_id,
        client_representative=client_representative,
        client_representative_no=client_representative_no,
        status=visit_status,
        notes=notes,
        requirements=requirements,
        measurements=measurements,
        existing_conditions=existing_conditions,
        challenges=challenges,
        recommendation=recommendation,
        photos=photos,
        videos=videos,
        drawings=drawings,
        measurement_sheets=measurement_sheets,
    )
    
    return created_single(
        build_site_visit_out(visit),
        message="Site visit created successfully.",
    )

@router.get(
    "",
    response_model=ApiResponse[SiteVisitOut],
    status_code=status.HTTP_200_OK,
)
async def list_site_visits_api(
    service: SiteVisitServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    visit_date: datetime | None = Query(None),
    engineer_id: uuid.UUID | None = Query(None),
    visit_status: SiteVisitStatus | None = Query(None, alias="status"),
    sales_executive_id: uuid.UUID | None = Query(None),
) -> ApiResponse[SiteVisitOut]:
    skip = (page - 1) * size
    items, total = await service.list(
        skip=skip,
        limit=size,
        search=search,
        visit_date=visit_date,
        engineer_id=engineer_id,
        status=visit_status,
        sales_executive_id=sales_executive_id,
    )

    out = [build_site_visit_out(i) for i in items]
    return ok_list(out, page=page, size=size, total=total, message="Site visits fetched successfully.")

@router.get(
    "/{site_visit_id}",
    response_model=ApiResponse[SiteVisitOut],
    status_code=status.HTTP_200_OK,
)
async def get_site_visit_api(
    site_visit_id: uuid.UUID,
    service: SiteVisitServiceDep,
) -> ApiResponse[SiteVisitOut]:
    visit = await service.get(site_visit_id)
    return ok_single(build_site_visit_out(visit), message="Site visit fetched successfully.")

@router.patch(
    "/{site_visit_id}",
    response_model=ApiResponse[SiteVisitOut],
    status_code=status.HTTP_200_OK,
)
async def update_site_visit_api(
    site_visit_id: uuid.UUID,
    service: SiteVisitServiceDep,
    visit_date: datetime | None = Form(None),
    visit_count: int | None = Form(None),
    engineer_id: uuid.UUID | None = Form(None),
    sales_executive_id: uuid.UUID | None = Form(None),
    client_representative: str | None = Form(None),
    client_representative_no: str | None = Form(None),
    visit_status: SiteVisitStatus | None = Form(None, alias="status"),
    notes: str | None = Form(None),
    requirements: str | None = Form(None),
    measurements: str | None = Form(None),
    existing_conditions: str | None = Form(None),
    challenges: str | None = Form(None),
    recommendation: str | None = Form(None),
    photos: list[UploadFile] = File(default=[]),
    videos: list[UploadFile] = File(default=[]),
    drawings: list[UploadFile] = File(default=[]),
    measurement_sheets: list[UploadFile] = File(default=[]),
) -> ApiResponse[SiteVisitOut]:
    visit = await service.update_site_visit(
        site_visit_id=site_visit_id,
        visit_date=visit_date,
        visit_count=visit_count,
        engineer_id=engineer_id,
        sales_executive_id=sales_executive_id,
        client_representative=client_representative,
        client_representative_no=client_representative_no,
        status=visit_status,
        notes=notes,
        requirements=requirements,
        measurements=measurements,
        existing_conditions=existing_conditions,
        challenges=challenges,
        recommendation=recommendation,
        photos=photos,
        videos=videos,
        drawings=drawings,
        measurement_sheets=measurement_sheets,
    )
    return ok_single(build_site_visit_out(visit), message="Site visit updated successfully.")
