"""Health endpoints: liveness and readiness."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status
from sqlalchemy import text

from app.api.deps import DbSession, RedisDep
from app.storage.s3 import is_healthy as is_s3_healthy

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/healthz", status_code=status.HTTP_200_OK, summary="Liveness")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz", status_code=status.HTTP_200_OK, summary="Readiness")
async def readiness(db: DbSession, redis: RedisDep) -> dict[str, Any]:
    components: dict[str, str] = {}
    overall_ok = True

    try:
        await db.execute(text("SELECT 1"))
        components["db"] = "ok"
    except Exception as exc:
        components["db"] = f"error: {exc.__class__.__name__}"
        overall_ok = False

    try:
        await redis.ping()
        components["redis"] = "ok"
    except Exception as exc:
        components["redis"] = f"error: {exc.__class__.__name__}"
        overall_ok = False

    # S3 check uses the cached `is_healthy()` flag from the most recent
    # ping_s3() call (lifespan). We deliberately don't do a network
    # round-trip here — that would slow the readiness probe and could
    # flap during transient network blips.
    if is_s3_healthy():
        components["s3"] = "ok"
    else:
        components["s3"] = "error: unreachable"
        overall_ok = False

    return {"status": "ok" if overall_ok else "degraded", "components": components}
