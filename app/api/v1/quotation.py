from __future__ import annotations
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, status, Query
from datetime import date
from app.api.deps import DbSession, CurrentUser
from app.api.v1._response import created_single, ok_single, ok_list
from app.schemas.common import ApiResponse
from app.models.enums import QuotationStatus
from app.schemas.quotation import QuotationCreate, QuotationOut, QuotationUpdate
from app.services.quotation import QuotationService

router = APIRouter(prefix="/quotations", tags=["quotations"])

def _get_quotation_service(db: DbSession) -> QuotationService:
    return QuotationService(session=db)

QuotationServiceDep = Annotated[QuotationService, Depends(_get_quotation_service)]

@router.post(
    "",
    response_model=ApiResponse[QuotationOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new quotation",
)
async def create_quotation(
    data: QuotationCreate,
    service: QuotationServiceDep,
    current_user: CurrentUser,
) -> ApiResponse[QuotationOut]:
    quotation = await service.create(current_user.id, data)
    return created_single(
        QuotationOut.model_validate(quotation),
        message="Quotation created successfully.",
    )

@router.patch(
    "/{quotation_id}",
    response_model=ApiResponse[QuotationOut],
    status_code=status.HTTP_200_OK,
    summary="Update a quotation",
)
async def update_quotation(
    quotation_id: uuid.UUID,
    data: QuotationUpdate,
    service: QuotationServiceDep,
    current_user: CurrentUser,
) -> ApiResponse[QuotationOut]:
    """
    Update an existing quotation and its line items.
    """
    quotation = await service.update(quotation_id, data, current_user.id)
    return ok_single(QuotationOut.model_validate(quotation), message="Quotation updated successfully.")

@router.get(
    "",
    response_model=ApiResponse[QuotationOut],
    status_code=status.HTTP_200_OK,
    summary="List all quotations",
)
async def list_quotations(
    service: QuotationServiceDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    search: str | None = Query(None),
    status: list[QuotationStatus] | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    created_by_id: uuid.UUID | None = Query(None),
) -> ApiResponse[QuotationOut]:
    quotations, total = await service.list_all(
        page=page, 
        size=size,
        search=search,
        statuses=status,
        start_date=start_date,
        end_date=end_date,
        created_by_id=created_by_id
    )
    out_list = [QuotationOut.model_validate(q) for q in quotations]
    return ok_list(out_list, page=page, size=size, total=total, message="Quotations fetched successfully.")

@router.get(
    "/{quotation_id}",
    response_model=ApiResponse[QuotationOut],
    status_code=status.HTTP_200_OK,
    summary="Get a quotation by ID",
)
async def get_quotation(
    quotation_id: uuid.UUID,
    service: QuotationServiceDep,
    current_user: CurrentUser,
) -> ApiResponse[QuotationOut]:
    quotation = await service.get(quotation_id)
    return ok_single(QuotationOut.model_validate(quotation), message="Quotation fetched successfully.")
