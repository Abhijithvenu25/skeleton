"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.db.redis import close_redis

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from starlette.requests import Request
    from starlette.responses import Response

configure_logging()
logger = get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a correlation ID and emit structured access logs."""

    async def dispatch(
        self, request: Request, call_next: object
    ) -> Response:
        request_id = request.headers.get("x-request-id") or structlog.contextvars.get_contextvars().get(
            "request_id"
        )
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path, method=request.method)
        try:
            response: Response = await call_next(request)  # type: ignore[operator]
        except Exception:
            logger.exception("request_failed")
            raise
        response.headers["x-request-id"] = str(request_id) if request_id else ""
        logger.info("request_completed", status_code=response.status_code)
        return response


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("app_starting", env=settings.app_env, name=settings.app_name)
    yield
    await close_redis()
    logger.info("app_stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url=f"{settings.api_v1_prefix}/docs",
        redoc_url=f"{settings.api_v1_prefix}/redoc",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id"],
    )
    if not settings.is_local:
        # Tighten host validation in non-local envs (caller can override if needed).
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

    # Errors
    register_exception_handlers(app)

    # Routes
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
