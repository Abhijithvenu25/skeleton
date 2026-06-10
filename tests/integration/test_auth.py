"""Integration tests for the auth flow."""

from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_login_refresh_logout_flow(client):
    # Register
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@example.com",
            "password": "alicepassword123",
            "full_name": "Alice",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user"]["email"] == "alice@example.com"
    access = body["token"]["access_token"]
    refresh = body["token"]["refresh_token"]
    assert access and refresh

    # /me with the access token
    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    assert r.json()["email"] == "alice@example.com"

    # Refresh rotation
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200, r.text
    rotated = r.json()
    assert rotated["access_token"]
    assert rotated["refresh_token"] != refresh  # rotated

    # Reusing the old refresh token must fail
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 401

    # Logout
    r = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {rotated['access_token']}"},
    )
    assert r.status_code == 200

    # After logout, the rotated refresh must be invalid
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": rotated["refresh_token"]})
    assert r.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_invalid_credentials(client, user_factory):
    await user_factory(email="bob@example.com", password="bobpassword123")
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": "wrong"},
    )
    assert r.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_success(client, user_factory):
    await user_factory(email="carol@example.com", password="carolpassword123")
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "carol@example.com", "password": "carolpassword123"},
    )
    assert r.status_code == 200
    assert r.json()["token"]["access_token"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_rate_limited(client):
    # Set a low limit for this test by hammering register many times.
    payload = {
        "email": "ratelimit@example.com",
        "password": "ratelimitpass123",
    }
    last = None
    # 6 attempts with default 5/min cap → at least one 429 expected
    for _ in range(7):
        last = await client.post("/api/v1/auth/register", json=payload)
        if last.status_code == 429:
            break
        # Use a new email each time so we hit registration, not the conflict path
        payload["email"] = f"rl-{__import__('uuid').uuid4().hex[:8]}@example.com"
    assert last is not None
    assert last.status_code == 429


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unauthorized_me(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code in (401, 403)
