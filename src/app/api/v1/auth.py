"""Authentication endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import (
    CurrentUser,
    DbSession,
    RedisDep,
    rate_limit,
)
from app.core.config import settings
from app.core.security import decode_token
from app.schemas.auth import (
    AuthMeOut,
    AuthOut,
    LoginIn,
    RefreshIn,
    RegisterIn,
    RegisterOut,
    TokenPair,
)
from app.schemas.common import MessageResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_service(db: DbSession, redis: RedisDep) -> AuthService:
    return AuthService(session=db, redis=redis)


@router.post(
    "/register",
    response_model=AuthOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    dependencies=[Depends(rate_limit(key_prefix="register", limit=settings.rate_limit_register_per_min))],
)
async def register(
    payload: RegisterIn,
    db: DbSession,
    redis: RedisDep,
) -> AuthOut:
    service = _auth_service(db, redis)
    user, token = await service.register(payload)
    return AuthOut(user=RegisterOut.model_validate(user), token=token)


@router.post(
    "/login",
    response_model=AuthOut,
    summary="Login and obtain a token pair",
    dependencies=[Depends(rate_limit(key_prefix="login", limit=settings.rate_limit_login_per_min))],
)
async def login(payload: LoginIn, db: DbSession, redis: RedisDep) -> AuthOut:
    service = _auth_service(db, redis)
    user, token = await service.login(payload)
    return AuthOut(user=RegisterOut.model_validate(user), token=token)


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Rotate the refresh token (returns a new pair)",
)
async def refresh(
    payload: RefreshIn,
    db: DbSession,
    redis: RedisDep,
) -> TokenPair:
    service = _auth_service(db, redis)
    return await service.refresh(payload.refresh_token)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Revoke all refresh tokens for the current user",
)
async def logout(
    request: Request,
    db: DbSession,
    redis: RedisDep,
    current_user: CurrentUser,
) -> MessageResponse:
    service = _auth_service(db, redis)
    # Best-effort: decode the access token to know the subject (== user id).
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1]
        payload = decode_token(token, expected_type="access")
        await service.logout(payload)
    return MessageResponse(message="Logged out")


@router.get(
    "/me",
    response_model=AuthMeOut,
    summary="Return the current authenticated user",
)
async def me(
    current_user: CurrentUser,
    db: DbSession,
    redis: RedisDep,
) -> AuthMeOut:
    service = _auth_service(db, redis)
    user_out = await service.get_user(uuid.UUID(str(current_user.id)))
    return AuthMeOut(**user_out.model_dump())
