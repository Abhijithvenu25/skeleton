"""Aggregator for v1 routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, crm, health, uploads

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(uploads.router)

# CRM resource routers — one per entity in the ERD. Routers are stored under
# their singular module name (e.g. `crm.role`); the URL prefix on each router
# carries the plural form (`/roles`, `/companies`, ...).
api_router.include_router(crm.role.router)
api_router.include_router(crm.staff_profile.router)
api_router.include_router(crm.company.router)
api_router.include_router(crm.contact.router)
api_router.include_router(crm.project.router)
api_router.include_router(crm.enquiry.router)
api_router.include_router(crm.site_visit.router)
api_router.include_router(crm.quotation.router)
api_router.include_router(crm.quotation_line_item.router)
api_router.include_router(crm.lost_enquiry.router)
