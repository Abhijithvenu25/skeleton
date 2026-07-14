from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.api.deps import DbSession, CurrentUser
from app.api.v1.uploads import StorageServiceDep
from app.models.enums import EnquirySource, EnquiryPriority,EnquiryStatus
from app.api.v1._response import created_single, ok_single, ok_list
from app.api.v1._enquiry_response import build_enquiry_detail_out
from app.schemas.common import ApiResponse
from app.schemas.enquiry import EnquiryOut, EnquiryDetailOut, LostEnquiryOut
from app.schemas.audit_log import EnquiryAuditLogOut
from app.services.enquiry import EnquiryService
from fastapi import Query

router = APIRouter(prefix="/enquiries", tags=["enquiries"])

def _get_enquiry_service(db: DbSession, storage: StorageServiceDep) -> EnquiryService:
    return EnquiryService(session=db, storage=storage)

EnquiryServiceDep = Annotated[EnquiryService, Depends(_get_enquiry_service)]

@router.post(
    "",
    response_model=ApiResponse[EnquiryDetailOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new enquiry with attachments",
)
async def create_enquiry(
    service: EnquiryServiceDep,
    current_user: CurrentUser,
    company_name: str = Form(...),
    company_website: str | None = Form(None),
    company_address: str | None = Form(None),
    company_city: str | None = Form(None),
    company_state: str | None = Form(None),
    company_country: str | None = Form(None),
    company_pincode: str | None = Form(None),
    contact_person: str = Form(...),
    designation: str | None = Form(None),
    mobile: str | None = Form(None),
    alternate_mobile: str | None = Form(None),
    email: str | None = Form(None),
    project_name: str = Form(...),
    project_type_id: uuid.UUID = Form(...),
    project_location: str | None = Form(None),
    estimated_budget: float | None = Form(None),
    expected_start_date: date | None = Form(None),
    source: EnquirySource | None = Form(None),
    priority: EnquiryPriority = Form(EnquiryPriority.medium),
    sales_executive_id: uuid.UUID | None = Form(None),
    project_description: str | None = Form(None),
    remarks: str | None = Form(None),
    boq: list[UploadFile | str] = File(default=[]),
    drawings: list[UploadFile | str] = File(default=[]),
    photos: list[UploadFile | str] = File(default=[]),
    tender_documents: list[UploadFile | str] = File(default=[]),
    other_files: list[UploadFile | str] = File(default=[]),
) -> ApiResponse[EnquiryDetailOut]:
    enquiry = await service.create_enquiry(
        company_name=company_name,
        company_website=company_website,
        company_address=company_address,
        company_city=company_city,
        company_state=company_state,
        company_country=company_country,
        company_pincode=company_pincode,
        contact_person=contact_person,
        designation=designation,
        mobile=mobile,
        alternate_mobile=alternate_mobile,
        email=email,
        project_name=project_name,
        project_type_id=project_type_id,
        project_location=project_location,
        estimated_budget=estimated_budget,
        expected_start_date=expected_start_date,
        source=source,
        priority=priority,
        sales_executive_id=sales_executive_id,
        project_description=project_description,
        remarks=remarks,
        boq_files=boq,
        drawings_files=drawings,
        photos_files=photos,
        tender_files=tender_documents,
        other_files=other_files,
    )
    return created_single(
        build_enquiry_detail_out(enquiry),
        message="Enquiry created successfully.",
    )

@router.get(
    "/lost",
    response_model=ApiResponse[LostEnquiryOut],
    status_code=status.HTTP_200_OK,
)
async def list_lost_enquiries(
    service: EnquiryServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    stage_lost: str | None = Query(None),
    lost_reason: str | None = Query(None),
) -> ApiResponse[LostEnquiryOut]:
    skip = (page - 1) * size
    items, total = await service.list_lost(
        skip=skip,
        limit=size,
        search=search,
        stage_lost=stage_lost,
        lost_reason=lost_reason,
    )
    
    out = []
    for i in items:
        out.append(LostEnquiryOut(
            id=i.id,
            enquiry_number=i.enquiry_number,
            company_name=i.company.company_name if i.company else "",
            stage_lost=i.stage_lost,
            lost_reason=i.lost_reason,
            date_lost=i.date_lost,
            follow_up_date=i.follow_up_date,
        ))
    return ok_list(out, page=page, size=size, total=total, message="Lost enquiries fetched successfully.")

@router.get(
    "/{enquiry_id}",
    response_model=ApiResponse[EnquiryDetailOut],
    status_code=status.HTTP_200_OK,
)
async def get_enquiry(
    enquiry_id: uuid.UUID,
    service: EnquiryServiceDep,
) -> ApiResponse[EnquiryDetailOut]:
    enquiry = await service.get(enquiry_id)
    return ok_single(build_enquiry_detail_out(enquiry), message="Enquiry fetched successfully.")

@router.get(
    "",
    response_model=ApiResponse[EnquiryDetailOut],
    status_code=status.HTTP_200_OK,
)
async def list_enquiries(
    service: EnquiryServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    status: list[EnquiryStatus] | None = Query(None),
    priority: list[EnquiryPriority] | None = Query(None),
    sales_executive_id: list[uuid.UUID] | None = Query(None),
    project_type_id: list[uuid.UUID] | None = Query(None),
    is_deleted: bool = Query(False),
) -> ApiResponse[EnquiryDetailOut]:
    skip = (page - 1) * size
    items, total = await service.list(
        skip=skip,
        limit=size,
        search=search,
        status=status,
        priority=priority,
        sales_executive_id=sales_executive_id,
        project_type_id=project_type_id,
        is_deleted=is_deleted,
    )
    out = [build_enquiry_detail_out(i) for i in items]
    return ok_list(out, page=page, size=size, total=total, message="Enquiries fetched successfully.")

@router.patch(
    "/{enquiry_id}",
    response_model=ApiResponse[EnquiryDetailOut],
    status_code=status.HTTP_200_OK,
)
async def update_enquiry_api(
    enquiry_id: uuid.UUID,
    service: EnquiryServiceDep,
    company_name: str | None = Form(None),
    company_website: str | None = Form(None),
    company_address: str | None = Form(None),
    company_city: str | None = Form(None),
    company_state: str | None = Form(None),
    company_country: str | None = Form(None),
    company_pincode: str | None = Form(None),
    contact_person: str | None = Form(None),
    designation: str | None = Form(None),
    mobile: str | None = Form(None),
    alternate_mobile: str | None = Form(None),
    email: str | None = Form(None),
    project_name: str | None = Form(None),
    project_type_id: uuid.UUID | None = Form(None),
    project_location: str | None = Form(None),
    estimated_budget: float | None = Form(None),
    expected_start_date: date | None = Form(None),
    source: EnquirySource | None = Form(None),
    priority: EnquiryPriority | None = Form(None),
    sales_executive_id: uuid.UUID | None = Form(None),
    project_description: str | None = Form(None),
    remarks: str | None = Form(None),
    stage_lost: str | None = Form(None),
    lost_reason: str | None = Form(None),
    date_lost: date | None = Form(None),
    follow_up_date: date | None = Form(None),
    reinstated: bool | None = Form(None),
    status_param: EnquiryStatus | None = Form(None, alias="status"),
    boq: list[UploadFile | str] | None = File(default=None),
    drawings: list[UploadFile | str] | None = File(default=None),
    photos: list[UploadFile | str] | None = File(default=None),
    tender_documents: list[UploadFile | str] | None = File(default=None),
    other_files: list[UploadFile | str] | None = File(default=None),
) -> ApiResponse[EnquiryDetailOut]:
    enquiry = await service.update_enquiry(
        enquiry_id=enquiry_id,
        company_name=company_name,
        company_website=company_website,
        company_address=company_address,
        company_city=company_city,
        company_state=company_state,
        company_country=company_country,
        company_pincode=company_pincode,
        contact_person=contact_person,
        designation=designation,
        mobile=mobile,
        alternate_mobile=alternate_mobile,
        email=email,
        project_name=project_name,
        project_type_id=project_type_id,
        project_location=project_location,
        estimated_budget=estimated_budget,
        expected_start_date=expected_start_date,
        source=source,
        priority=priority,
        sales_executive_id=sales_executive_id,
        project_description=project_description,
        remarks=remarks,
        stage_lost=stage_lost,
        lost_reason=lost_reason,
        date_lost=date_lost,
        follow_up_date=follow_up_date,
        reinstated=reinstated,
        status=status_param,
        boq_files=boq,
        drawings_files=drawings,
        photos_files=photos,
        tender_files=tender_documents,
        other_files=other_files,
    )
    return ok_single(build_enquiry_detail_out(enquiry), message="Enquiry updated successfully.")

@router.get(
    "/{enquiry_id}/audit-logs",
    response_model=ApiResponse[EnquiryAuditLogOut],
    status_code=status.HTTP_200_OK,
)
async def get_enquiry_audit_logs_api(
    enquiry_id: uuid.UUID,
    service: EnquiryServiceDep,
) -> ApiResponse[EnquiryAuditLogOut]:
    logs = await service.list_audit_logs(enquiry_id)
    return ok_list(list(logs), message="Audit logs fetched successfully.")

@router.delete(
    "/{enquiry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_enquiry_api(
    enquiry_id: uuid.UUID,
    service: EnquiryServiceDep,
) -> None:
    await service.delete(enquiry_id)

@router.delete(
    "/{enquiry_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_enquiry_attachment(
    enquiry_id: uuid.UUID,
    attachment_id: uuid.UUID,
    service: EnquiryServiceDep,
) -> None:
    await service.delete_attachment(attachment_id)

