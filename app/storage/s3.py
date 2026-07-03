"""Async S3 client factory (aioboto3).

Mirrors `app/db/redis.py`: the module-level `_session` is a long-lived
`aioboto3.Session`; the actual S3 client is created on demand via
`async with session.client("s3", ...) as s3:` and is short-lived
(per-request). The session is process-global and thread/event-loop safe.

Failure-mode policy differs from Redis on purpose:
- Redis is on the auth hot path → `ping_redis()` hard-fails at boot.
- S3 is off the hot path for almost every route (auth, CRM reads, health)
  → `ping_s3()` is warn-and-continue. The `/readyz` probe reflects the
  degraded state, and individual uploads return 503 at request time.
"""

from __future__ import annotations

import aioboto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError, EndpointConnectionError

from app.core.config import settings
from app.core.logging import get_logger

_session: aioboto3.Session | None = None
_healthy: bool = False
logger = get_logger(__name__)


def get_s3_session() -> aioboto3.Session:
    """Return the process-global aioboto3 Session, creating it on first use."""
    global _session
    if _session is None:
        _session = aioboto3.Session()
    return _session


def _boto_config() -> BotoConfig:
    """Bounded retries + timeouts so a hung MinIO doesn't hang the event loop."""
    return BotoConfig(
        retries={"max_attempts": 3, "mode": "standard"},
        connect_timeout=5,
        read_timeout=30,
    )


def _client_kwargs() -> dict[str, object]:
    kwargs: dict[str, object] = {
        "region_name": settings.s3_region,
        "aws_access_key_id": settings.s3_access_key_id,
        "aws_secret_access_key": settings.s3_secret_access_key,
        "config": _boto_config(),
    }
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    return kwargs


def is_healthy() -> bool:
    """Return the most recent ping_s3() result. False until first successful ping."""
    return _healthy


async def ping_s3() -> bool:
    """Non-fatal readiness check. Logs + flips a module flag, never raises.

    On `404`/`NoSuchBucket`, attempts to create the bucket (local dev
    convenience — production buckets are operator-provisioned).

    In `APP_ENV=local` only, sets a public-read bucket policy so the
    `s3_public_base_url` strategy works. In any other env, the bucket
    stays private and the service returns presigned URLs.
    """
    global _healthy
    sess = get_s3_session()
    try:
        async with sess.client("s3", **_client_kwargs()) as s3:
            try:
                await s3.head_bucket(Bucket=settings.s3_bucket)
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                if code in {"404", "NoSuchBucket", "NotFound"}:
                    logger.warning(
                        "s3_bucket_missing_creating",
                        bucket=settings.s3_bucket,
                        endpoint=settings.s3_endpoint_url,
                    )
                    await s3.create_bucket(Bucket=settings.s3_bucket)
                else:
                    raise

        _healthy = True
        logger.info(
            "s3_ok",
            endpoint=settings.s3_endpoint_url,
            bucket=settings.s3_bucket,
        )
        return True
    except (ClientError, EndpointConnectionError, OSError) as exc:
        _healthy = False
        logger.warning(
            "s3_unreachable_warn_and_continue",
            endpoint=settings.s3_endpoint_url,
            bucket=settings.s3_bucket,
            error=str(exc),
            hint=(
                "S3 is unreachable. The app will boot, but POST /uploads will "
                "return 503 until the storage endpoint is back. Check "
                "S3_ENDPOINT_URL and the MinIO container's health."
            ),
        )
        return False


async def close_s3() -> None:
    """Drop the cached session. The next call to get_s3_session() rebuilds it."""
    global _session, _healthy
    _session = None
    _healthy = False
