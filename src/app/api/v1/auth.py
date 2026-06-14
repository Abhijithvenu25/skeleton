"""Authentication endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import (
    CurrentUser,
    DbSession,
    RedisDep,
    rate_limit,
)
from app.core.config import settings
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


def _get_auth_service(db: DbSession, redis: RedisDep) -> AuthService:
    return AuthService(session=db, redis=redis)


AuthServiceDep = Annotated[AuthService, Depends(_get_auth_service)]


@router.post(
    "/register",
    response_model=AuthOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    dependencies=[Depends(rate_limit(key_prefix="register", limit=settings.rate_limit_register_per_min))],
)
async def register(
    payload: RegisterIn,
    service: AuthServiceDep,
) -> AuthOut:
    user, token = await service.register(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
    )
    return AuthOut(
        user=RegisterOut.model_validate(user),
        token=token,
    )


@router.post(
    "/login",
    response_model=AuthOut,
    summary="Login and obtain a token pair",
    dependencies=[Depends(rate_limit(key_prefix="login", limit=settings.rate_limit_login_per_min))],
)
async def login(
    payload: LoginIn,
    service: AuthServiceDep,
) -> AuthOut:
    user, token = await service.login(email=payload.email, password=payload.password)
    return AuthOut(
        user=RegisterOut.model_validate(user),
        token=token,
    )


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Rotate the refresh token (returns a new pair)",
)
async def refresh(
    payload: RefreshIn,
    service: AuthServiceDep,
) -> TokenPair:
    return await service.refresh(payload.refresh_token)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Revoke all refresh tokens for the current user",
)
async def logout(
    request: Request,
    service: AuthServiceDep,
    current_user: CurrentUser,  # noqa: ARG001
) -> MessageResponse:
    await service.logout(request=request)
    return MessageResponse(message="Logged out")


@router.get(
    "/me",
    response_model=AuthMeOut,
    summary="Return the current authenticated user",
)
async def me(
    current_user: CurrentUser,
) -> AuthMeOut:
    return AuthMeOut.model_validate(current_user)
