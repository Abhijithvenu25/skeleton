from __future__ import annotations
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, status
from app.api.deps import DbSession, CurrentUser
from app.api.v1._response import created_single
from app.schemas.common import ApiResponse
from app.schemas.quotation import QuotationCreate, QuotationOut
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
    quotation = await service.create(user_id=current_user.id, data=data)
    return created_single(
        quotation,
        message="Quotation created successfully.",
    )
