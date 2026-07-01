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

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.exceptions import BadRequestError
from app.core.logging import get_logger
from app.storage.service import (
    ALLOWED_CATEGORIES,
    StorageService,
    generate_key,
)

router = APIRouter(prefix="/uploads", tags=["uploads"])
logger = get_logger(__name__)

CategoryLiteral = Literal["boq", "drawings", "photos", "pdf", "other"]


class UploadOut(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)
    key: str = Field(..., min_length=1, max_length=512)
    size: int = Field(..., ge=0)
    content_type: str = Field(..., min_length=1, max_length=128)


def _get_service() -> StorageService:
    return StorageService()


ServiceDep = Annotated[StorageService, Depends(_get_service)]


@router.post(
    "",
    response_model=UploadOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file to object storage and return its public URL",
)
async def upload_file(
    file: Annotated[UploadFile, File(description="File to upload")],
    category: Annotated[CategoryLiteral, Form()] = "other",
    service: ServiceDep = ...,  # type: ignore[assignment]
    _current_user: CurrentUser = ...,  # type: ignore[assignment]
) -> UploadOut:
    # 1. Cheap input validation — fail before we read the body.
    if not file.filename:
        raise BadRequestError("filename_required")
    if not file.content_type:
        raise BadRequestError("content_type_required")
    if category not in ALLOWED_CATEGORIES:
        raise BadRequestError(
            "invalid_category",
            details={"category": category, "allowed": sorted(ALLOWED_CATEGORIES)},
        )

    # 2. Build the safe key FIRST. Rejecting on filename/extension before we
    #    stream means a hostile client with `evil.exe` doesn't get a single
    #    byte onto the wire to S3.
    key = generate_key(category, file.filename)

    # 3. Stream the body with a hard size cap. We read in 1 MiB chunks and
    #    bail as soon as the cap is exceeded so a 1 GB upload doesn't OOM us.
    max_bytes = settings.s3_max_upload_bytes
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)  # 1 MiB
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise BadRequestError(
                "file_too_large",
                details={"max_bytes": max_bytes},
            )
        chunks.append(chunk)
    if total == 0:
        raise BadRequestError("empty_file")

    body = b"".join(chunks)

    # 4. Upload. Service maps S3 transport failures to S3UnavailableError.
    url = await service.upload_file(
        key=key,
        body=body,
        content_type=file.content_type,
    )

    logger.info(
        "upload_completed",
        key=key,
        category=category,
        size=total,
        content_type=file.content_type,
        user_id=str(_current_user.id),
    )
    return UploadOut(
        url=url,
        key=key,
        size=total,
        content_type=file.content_type,
    )
