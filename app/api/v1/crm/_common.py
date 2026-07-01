"""Shared helpers for CRM routers (currently just re-exports)."""

from __future__ import annotations

from app.api.deps import CurrentUser, DbSession
from app.services.crm._common import build_page

__all__ = ["CurrentUser", "DbSession", "build_page"]
