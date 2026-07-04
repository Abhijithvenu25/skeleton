"""Storage service: upload, delete, key generation, URL building.

Public surface:
- `generate_key(category, filename)` — pure, raises `BadRequestError` for bad input.
- `StorageService.upload_file(key, body, content_type)` — returns the public URL.
- `StorageService.upload_uploadfile(file, category)` — streams a FastAPI
  `UploadFile` to S3 with the same size-cap + extension-validation as the
  legacy `POST /uploads` flow.
- `StorageService.delete_file(key)` — best-effort delete; `NotFoundError` if absent.

The key shape is `{category}/{YYYY}/{MM}/{uuid8}_{safe_stem}.{ext}` so a future
lifecycle rule (e.g. expire `photos/` after N days) can target a prefix
without code changes.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Final

from botocore.exceptions import ClientError, EndpointConnectionError
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import BadRequestError, NotFoundError, S3UnavailableError
from app.core.logging import get_logger
from app.storage.s3 import get_s3_session, is_healthy


@dataclass(frozen=True)
class StoredObject:
    """Result of an upload — what callers need to persist for later deletion
    or display (`key` is enough to delete; `url` is what the client shows).
    """

    url: str
    key: str
    size: int
    content_type: str

logger = get_logger(__name__)

ALLOWED_CATEGORIES: Final[frozenset[str]] = frozenset({"boq", "drawings", "photos", "pdf", "other"})

# Per-category extension allow-list. `None` means "any extension not in
# DENY_EXT is allowed" (used for `other`).
CATEGORY_EXT_ALLOW: Final[dict[str, frozenset[str] | None]] = {
    "boq": frozenset({"xlsx", "xls", "csv", "ods", "pdf", "doc", "docx"}),
    "drawings": frozenset({"dwg", "dxf", "pdf", "png", "jpg", "jpeg"}),
    "photos": frozenset({"jpg", "jpeg", "png", "webp", "heic", "heif"}),
    "pdf": frozenset({"pdf"}),
    "other": None,
}

DENY_EXT: Final[frozenset[str]] = frozenset(
    {"exe", "bat", "sh", "ps1", "js", "jar", "com", "msi", "scr", "vbs"}
)

_SAFE_STEM = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_STEM_LEN = 80
_MAX_EXT_LEN = 16


def _sanitize_stem(stem: str) -> str:
    # NFKC normalize so visually-confusable unicode gets folded to ASCII.
    stem = unicodedata.normalize("NFKC", stem)
    stem = _SAFE_STEM.sub("_", stem).strip("._")
    return stem


def generate_key(category: str, filename: str) -> str:
    """Build a collision-resistant, sanitized object key.

    Shape: `{category}/{YYYY}/{MM}/{uuid8}_{safe_stem}.{ext}`.
    Raises `BadRequestError` for bad category / bad filename / bad extension.
    """
    if category not in ALLOWED_CATEGORIES:
        raise BadRequestError(
            "invalid_category",
            details={"category": category, "allowed": sorted(ALLOWED_CATEGORIES)},
        )

    # Strip directory components — a malicious "../etc/passwd" must not survive.
    name = PurePosixPath(filename).name
    if not name or name.startswith("."):
        raise BadRequestError("invalid_filename", details={"filename": filename})

    if "." not in name:
        raise BadRequestError("filename_requires_extension", details={"filename": filename})

    stem, _, ext = name.rpartition(".")
    ext = ext.lower()
    if not ext or len(ext) > _MAX_EXT_LEN:
        raise BadRequestError("invalid_extension", details={"filename": filename})

    if ext in DENY_EXT:
        raise BadRequestError("extension_not_allowed", details={"extension": ext})

    allowed = CATEGORY_EXT_ALLOW[category]
    if allowed is not None and ext not in allowed:
        raise BadRequestError(
            "extension_not_allowed_for_category",
            details={"category": category, "extension": ext, "allowed": sorted(allowed)},
        )

    safe_stem = _sanitize_stem(stem)
    if not safe_stem:
        raise BadRequestError("invalid_filename", details={"filename": filename})
    if len(safe_stem) > _MAX_STEM_LEN:
        safe_stem = safe_stem[:_MAX_STEM_LEN]

    now = datetime.now(UTC)
    uid = uuid.uuid4().hex[:8]
    return f"{category}/{now:%Y}/{now:%m}/{uid}_{safe_stem}.{ext}"


def public_url(key: str) -> str:
    """Build a stable public URL for `key` using `s3_public_base_url`.

    Raises `RuntimeError` if no public base is configured — call
    `presigned_get_url(key)` for private buckets in that case.
    """
    base = settings.s3_public_base_url
    if not base:
        raise RuntimeError("no_public_base_url_configured_call_presigned_get_url")
    return f"{base.rstrip('/')}/{key}"


async def presigned_get_url(key: str) -> str:
    """Generate a presigned GET URL with TTL = s3_presigned_ttl_seconds."""
    sess = get_s3_session()
    async with sess.client("s3", **_client_kwargs()) as s3:
        url: str = await s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": key},
            ExpiresIn=settings.s3_presigned_ttl_seconds,
        )
        return url


def _client_kwargs() -> dict[str, object]:
    kwargs: dict[str, object] = {
        "region_name": settings.s3_region,
        "aws_access_key_id": settings.s3_access_key_id,
        "aws_secret_access_key": settings.s3_secret_access_key,
    }
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    return kwargs


class StorageService:
    """Server-side S3 operations: upload + delete.

    Failures map to existing `AppError` subclasses:
    - `ClientError(Code=NoSuchKey)`        → `NotFoundError`
    - `ClientError(Code=EntityTooLarge)`   → `BadRequestError("file_too_large")`
    - everything else (ClientError, EndpointConnectionError, OSError)
                                            → `S3UnavailableError` (503)
    """

    async def upload_file(
        self,
        *,
        key: str,
        body: bytes,
        content_type: str,
    ) -> str:
        if not is_healthy():
            # Short-circuit before opening a connection: the latest ping failed.
            # /readyz will already be reporting `degraded`; we still need a
            # clean 503 here so the client gets a real error not a timeout.
            raise S3UnavailableError()

        sess = get_s3_session()
        try:
            async with sess.client("s3", **_client_kwargs()) as s3:
                await s3.put_object(
                    Bucket=settings.s3_bucket,
                    Key=key,
                    Body=body,
                    ContentType=content_type,
                )
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            logger.exception("s3_put_failed", key=key, code=code)
            if code == "EntityTooLarge":
                raise BadRequestError("file_too_large") from exc
            raise S3UnavailableError() from exc
        except (EndpointConnectionError, OSError) as exc:
            logger.exception("s3_put_transport_failed", key=key)
            raise S3UnavailableError() from exc

        if settings.s3_public_base_url:
            return public_url(key)
        return await presigned_get_url(key)

    async def upload_uploadfile(
        self,
        *,
        file: UploadFile,
        category: str,
    ) -> StoredObject:
        """Stream an `UploadFile` to S3 with full input + size validation.

        Same contract as the legacy `POST /uploads` endpoint:
        - filename + content_type required (`BadRequestError`)
        - category must be in `ALLOWED_CATEGORIES`
        - extension checked against `CATEGORY_EXT_ALLOW` / `DENY_EXT`
        - hard size cap = `settings.s3_max_upload_bytes`
        - empty bodies rejected

        Returns a `StoredObject` so callers can persist `key` (for future
        deletes) and `url` (for client display) together.
        """
        if not file.filename:
            raise BadRequestError("filename_required")
        if not file.content_type:
            raise BadRequestError("content_type_required")
        if category not in ALLOWED_CATEGORIES:
            raise BadRequestError(
                "invalid_category",
                details={"category": category, "allowed": sorted(ALLOWED_CATEGORIES)},
            )

        # Build the safe key BEFORE streaming — a hostile filename with
        # `evil.exe` shouldn't get a single byte onto the wire to S3.
        key = generate_key(category, file.filename)

        # 1 MiB streamed chunks; bail as soon as the cap is exceeded so a
        # 1 GB upload doesn't OOM us.
        max_bytes = settings.s3_max_upload_bytes
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = await file.read(1024 * 1024)
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
        url = await self.upload_file(
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
        )
        return StoredObject(
            url=url,
            key=key,
            size=total,
            content_type=file.content_type,
        )

    async def delete_file(self, key: str) -> None:
        sess = get_s3_session()
        try:
            async with sess.client("s3", **_client_kwargs()) as s3:
                await s3.delete_object(Bucket=settings.s3_bucket, Key=key)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code == "NoSuchKey":
                raise NotFoundError("object_not_found") from exc
            logger.exception("s3_delete_failed", key=key, code=code)
            raise S3UnavailableError() from exc
        except (EndpointConnectionError, OSError) as exc:
            logger.exception("s3_delete_transport_failed", key=key)
            raise S3UnavailableError() from exc
