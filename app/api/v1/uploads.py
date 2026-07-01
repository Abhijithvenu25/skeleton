"""File upload endpoint (server-side streaming to S3-compatible storage).

POST /api/v1/uploads — multipart/form-data with:
- `file: UploadFile` (required)
- `category: Literal["boq", "drawings", "photos", "pdf", "other"]` (optional, default "other")

Returns `{url, key, size, content_type}` on 201. The natural follow-up is to
pass `url` as `file_url` when creating a QuotationVersion:

    POST /uploads          → {"url": "http://.../foo.pdf", ...}
    POST /quotations/{id}/versions  {"file_url": "<that url>", ...}
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, UploadFile, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, StorageServiceDep
from app.core.logging import get_logger

router = APIRouter(prefix="/uploads", tags=["uploads"])
logger = get_logger(__name__)

CategoryLiteral = Literal["boq", "drawings", "photos", "pdf", "other"]


class UploadOut(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)
    key: str = Field(..., min_length=1, max_length=512)
    size: int = Field(..., ge=0)
    content_type: str = Field(..., min_length=1, max_length=128)


@router.post(
    "",
    response_model=UploadOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file to object storage and return its public URL",
)
async def upload_file(
    file: Annotated[UploadFile, File(description="File to upload")],
    category: Annotated[CategoryLiteral, Form()] = "other",
    service: StorageServiceDep = ...,  # type: ignore[assignment]
    _current_user: CurrentUser = ...,  # type: ignore[assignment]
) -> UploadOut:
    # All validation + size-cap + S3 upload live in the service helper.
    stored = await service.upload_uploadfile(file=file, category=category)
    logger.info(
        "upload_completed",
        key=stored.key,
        category=category,
        size=stored.size,
        content_type=stored.content_type,
        user_id=str(_current_user.id),
    )
    return UploadOut(
        url=stored.url,
        key=stored.key,
        size=stored.size,
        content_type=stored.content_type,
    )
