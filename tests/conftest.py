"""Shared test fixtures: httpx AsyncClient over the ASGI app.

These smoke tests don't need a real DB or Redis — they only assert that
the CurrentUser dependency is wired on each route. Full integration
tests (real DB + JWT helper) belong to a follow-up PR.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from app.asgi import app
from httpx import ASGITransport, AsyncClient

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
