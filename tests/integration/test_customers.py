"""Integration tests for the customer API."""

from __future__ import annotations

import pytest

from app.core.security import create_access_token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_and_list_customers(client, db_session, user_factory):
    user = await user_factory(email="dave@example.com")
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    r = await client.post(
        "/api/v1/customers",
        json={"name": "Acme Co", "email": "contact@acme.com", "phone": "+1-555-0001"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["name"] == "Acme Co"
    assert created["owner_id"] == str(user.id)

    r = await client.get("/api/v1/customers", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Acme Co"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pagination_and_search(client, user_factory):
    user = await user_factory(email="eve@example.com")
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    for name in ("Alpha Inc", "Beta LLC", "Acme", "Acme Beta"):
        r = await client.post("/api/v1/customers", json={"name": name}, headers=headers)
        assert r.status_code == 201

    r = await client.get("/api/v1/customers?size=2&page=1", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 4
    assert body["pages"] == 2
    assert len(body["items"]) == 2

    r = await client.get("/api/v1/customers?q=acme", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    for item in body["items"]:
        assert "acme" in item["name"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_and_delete(client, user_factory, db_session):
    user = await user_factory(email="frank@example.com")
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    r = await client.post(
        "/api/v1/customers", json={"name": "Old Name", "phone": "111"}, headers=headers
    )
    customer_id = r.json()["id"]

    r = await client.patch(
        f"/api/v1/customers/{customer_id}", json={"name": "New Name"}, headers=headers
    )
    assert r.status_code == 200
    assert r.json()["name"] == "New Name"

    r = await client.delete(f"/api/v1/customers/{customer_id}", headers=headers)
    assert r.status_code == 200

    r = await client.get(f"/api/v1/customers/{customer_id}", headers=headers)
    assert r.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tenant_isolation(client, user_factory):
    owner = await user_factory(email="owner@example.com")
    intruder = await user_factory(email="intruder@example.com")
    owner_h = {"Authorization": f"Bearer {create_access_token(str(owner.id))}"}
    intruder_h = {"Authorization": f"Bearer {create_access_token(str(intruder.id))}"}

    r = await client.post(
        "/api/v1/customers", json={"name": "Private"}, headers=owner_h
    )
    cid = r.json()["id"]

    r = await client.get(f"/api/v1/customers/{cid}", headers=intruder_h)
    assert r.status_code == 403
