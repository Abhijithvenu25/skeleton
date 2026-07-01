"""Application-level exceptions and FastAPI handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

if TYPE_CHECKING:
    from fastapi import FastAPI, Request

logger = get_logger(__name__)


# Map of unique-constraint name -> human-readable message template.
# `{value}` is substituted with the offending column value pulled from
# the original Postgres error. Unknown constraints fall through to a
# generic 409 with the constraint name in `details`.
_INTEGRITY_CONSTRAINT_MESSAGES: dict[str, str] = {
    "uq_roles_name":                    "Role '{value}' already exists",
    "ix_users_email":                   "Email already registered",
    "uq_staff_profiles_employee_code":   "Employee code '{value}' already in use",
    "uq_enquiries_enquiry_no":           "Enquiry number collision (retry the request)",
    "uq_site_visits_visit_no":          "Site-visit number collision (retry the request)",
    "uq_quotations_quote_no":            "Quotation number collision (retry the request)",
    "uq_quotation_versions_quote_version": "Quotation version already exists",
    "uq_lost_enquiries_enquiry_id":     "Lost enquiry already exists for this enquiry",
    "uq_contacts_company_primary":      "Company already has a primary contact",
}


def _extract_conflict_details(exc: Any) -> tuple[str | None, str | None, list[str]]:
    """Extract constraint name and offending value from a Postgres IntegrityError.

    Returns (constraint_name, offending_value, constraint_columns).
    - constraint_name: the unique-constraint or index that fired
    - offending_value: best-effort value (None if not extractable)
    - constraint_columns: list of column names in the constraint

    Falls back to (None, None, []) on non-Postgres or unrecognised errors.
    """
    constraint_name: str | None = None
    constraint_columns: list[str] = []
    offending_value: str | None = None

    # SQLAlchemy wraps the driver-specific error on .orig. For asyncpg / psycopg,
    # that's a psycopg2.errors.IntegrityError-like object with .diag.
    orig = getattr(exc, "orig", None)
    diag = getattr(orig, "diag", None)
    if diag is not None:
        constraint_name = getattr(diag, "constraint_name", None)
        constraint_columns = list(getattr(diag, "constraint_columns", []) or [])

    if constraint_columns:
        # Pull the value from bound params (exc.params is column->value
        # for INSERTs). This is the cleanest source: the formatted error
        # message often has it, but the bound-param dict is structured.
        params = getattr(exc, "params", None) or {}
        if isinstance(params, dict):
            first_col = constraint_columns[0]
            value = params.get(first_col)
            if value is not None:
                offending_value = str(value)

    return constraint_name, offending_value, constraint_columns


class AppError(Exception):
    """Base application error. Map to HTTP responses with a stable code."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str = "", *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message or self.code)
        self.message = message or self.code
        self.details: dict[str, Any] = details or {}


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class BadRequestError(AppError):
    status_code = 400
    code = "bad_request"


class RateLimitError(AppError):
    status_code = 429
    code = "rate_limited"


class S3UnavailableError(AppError):
    """Object storage (S3/MinIO) is unreachable or misconfigured.

    Maps to 503 so callers see a clear "retry shortly" instead of a 500
    with a stack trace. The StorageService should translate raw botocore
    exceptions to this; the handler below is the safety net for anything
    that escapes.
    """

    status_code = 503
    code = "storage_unavailable"


def _payload(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"code": code, "message": message}
    if details:
        body["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    from redis.exceptions import RedisError
    from sqlalchemy.exc import IntegrityError

    @app.exception_handler(AppError)
    async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_payload("validation_error", "Request validation failed", {"errors": exc.errors()}),
        )

    @app.exception_handler(RedisError)
    async def _redis_error_handler(_: Request, exc: RedisError) -> JSONResponse:
        # Runtime Redis failure (network blip, restart, OOM). Map to 503 so
        # callers see a clear "retry shortly" instead of a 500 with a stack
        # trace. Startup failures are caught earlier by ping_redis() in the
        # lifespan handler — this handler only fires for mid-request failures.
        logger.exception("redis_runtime_error", error=str(exc))
        return JSONResponse(
            status_code=503,
            content=_payload(
                "service_unavailable",
                "Auth service temporarily unavailable. Retry shortly.",
            ),
        )

    # Safety net for S3 errors that escaped the service layer. The service
    # layer maps most ClientError instances to S3UnavailableError already;
    # this handler exists so a future code path that forgets the wrap still
    # returns a clean 503 instead of a 500 with a stack trace.
    from botocore.exceptions import BotoCoreError, ClientError  # lazy: dep is optional

    @app.exception_handler(ClientError)
    async def _s3_client_error_handler(_: Request, exc: ClientError) -> JSONResponse:
        code = exc.response.get("Error", {}).get("Code", "")
        logger.exception("s3_runtime_error", code=code, error=str(exc))
        return JSONResponse(
            status_code=503,
            content=_payload(
                "storage_unavailable",
                "Object storage temporarily unavailable. Retry shortly.",
            ),
        )

    @app.exception_handler(BotoCoreError)
    async def _boto_core_error_handler(_: Request, exc: BotoCoreError) -> JSONResponse:
        logger.exception("botocore_runtime_error", error=str(exc))
        return JSONResponse(
            status_code=503,
            content=_payload(
                "storage_unavailable",
                "Object storage temporarily unavailable. Retry shortly.",
            ),
        )

    @app.exception_handler(IntegrityError)
    async def _integrity_error_handler(_: Request, exc: IntegrityError) -> JSONResponse:
        """Translate a database unique-constraint violation to 409.

        This is the safety net for any service that doesn't catch
        IntegrityError itself. Per-service catches (e.g. role.create) still
        win because they raise ConflictError before this handler runs;
        this only fires for unhandled cases. Result: no more 500s with
        stack traces for known cases like duplicate role names.
        """
        constraint_name, offending_value, constraint_columns = _extract_conflict_details(exc)
        logger.exception(
            "db_integrity_error",
            constraint=constraint_name,
            columns=constraint_columns,
        )
        template = (
            _INTEGRITY_CONSTRAINT_MESSAGES.get(constraint_name)
            if constraint_name
            else None
        )
        if template is not None:
            if "{value}" in template and offending_value is not None:
                message = template.format(value=offending_value)
            else:
                message = template
        else:
            # Unknown constraint — still 409, not 500. The constraint name
            # is in `details` for debugging.
            message = "Resource conflicts with an existing record"
        details: dict[str, Any] = {}
        if constraint_name:
            details["constraint"] = constraint_name
        if constraint_columns:
            details["columns"] = constraint_columns
        if offending_value is not None and constraint_name not in _INTEGRITY_CONSTRAINT_MESSAGES:
            details["value"] = offending_value
        return JSONResponse(
            status_code=409,
            content=_payload("conflict", message, details or None),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", error=str(exc))
        return JSONResponse(
            status_code=500,
            content=_payload("internal_error", "Internal server error"),
        )
