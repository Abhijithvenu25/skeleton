"""Integration tests for health endpoints."""

from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_healthz(client):
    r = await client.get("/api/v1/health/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_readyz(client):
    r = await client.get("/api/v1/health/readyz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["components"]["db"] == "ok"
    assert body["components"]["redis"] == "ok"
