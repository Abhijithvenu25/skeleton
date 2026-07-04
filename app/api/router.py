"""Aggregator for v1 routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, health, role, uploads, user, enquiry, project_type, site_visit

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(uploads.router)
api_router.include_router(role.router)
api_router.include_router(user.router)
api_router.include_router(enquiry.router)
api_router.include_router(project_type.router)
api_router.include_router(site_visit.router)
