from fastapi import APIRouter, status, Depends, Query
from typing import Annotated
from app.api.deps import CurrentUser, DbSession
from app.schemas.common import ApiResponse
from app.schemas.company import CompanyListOut
from app.services.company import CompanyService
from app.api.v1._response import ok_list

router = APIRouter(prefix="/companies", tags=["companies"])

def _get_company_service(db: DbSession) -> CompanyService:
    return CompanyService(db)

CompanyServiceDep = Annotated[CompanyService, Depends(_get_company_service)]

@router.get(
    "",
    response_model=ApiResponse[CompanyListOut],
    status_code=status.HTTP_200_OK,
)
async def list_companies_api(
    service: CompanyServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
) -> ApiResponse[CompanyListOut]:
    skip = (page - 1) * size
    items, total = await service.list_companies_with_enquiry(
        skip=skip,
        limit=size,
        search=search,
    )

    out = []
    for item in items:
        out.append(CompanyListOut(
            company_id=item.company_id,
            company_name=item.company_name,
            enquiry_id=item.enquiry_id,
        ))
        
    return ok_list(out, page=page, size=size, total=total, message="Companies fetched successfully.")
