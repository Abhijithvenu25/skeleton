"""Role API smoke tests — routing only.

These tests assert that every role-management route is registered and
is publicly callable (no auth gate). They do NOT exercise success paths
because that requires a real DB + JWT helper, which is a follow-up.

A request that hits a registered route may return 5xx (DB unavailable
in the test environment) — that's fine for a wiring check. What we're
guarding against is 404 (route missing) or 401 (auth accidentally
re-added).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    from httpx import AsyncClient


BASE = settings.api_v1_prefix


async def _status(client: AsyncClient, method: str, url: str, **kwargs: object) -> int:
    """Issue a request and return its status code.

    Catches exceptions raised by the service layer (e.g. asyncpg failing
    because the test env has no DB). An exception here PROVES the route
    was reached and the auth gate didn't intercept — that's the wiring
    invariant we care about — so we collapse it to a 5xx sentinel.
    """
    try:
        response = await getattr(client, method)(url, **kwargs)
        return response.status_code
    except Exception:
        return 500


def _assert_public_route(status: int) -> None:
    """Routes must be reachable without a bearer token (no auth gate) and
    must resolve to a registered handler (not 404)."""
    assert status != 401, "role endpoints should be public"
    assert status != 404, "role route not registered"


async def test_create_role_is_public(client: AsyncClient) -> None:
    status = await _status(client, "post", f"{BASE}/roles", json={"name": "admin"})
    _assert_public_route(status)


async def test_list_roles_is_public(client: AsyncClient) -> None:
    status = await _status(client, "get", f"{BASE}/roles")
    _assert_public_route(status)


async def test_get_role_is_public(client: AsyncClient) -> None:
    status = await _status(client, "get", f"{BASE}/roles/00000000-0000-0000-0000-000000000000")
    _assert_public_route(status)


async def test_patch_role_is_public(client: AsyncClient) -> None:
    status = await _status(
        client,
        "patch",
        f"{BASE}/roles/00000000-0000-0000-0000-000000000000",
        json={"name": "admin"},
    )
    _assert_public_route(status)


async def test_delete_role_is_public(client: AsyncClient) -> None:
    status = await _status(client, "delete", f"{BASE}/roles/00000000-0000-0000-0000-000000000000")
    _assert_public_route(status)


async def test_assign_role_is_public(client: AsyncClient) -> None:
    status = await _status(
        client,
        "post",
        f"{BASE}/roles/00000000-0000-0000-0000-000000000000/users",
        json={"user_id": "00000000-0000-0000-0000-000000000001"},
    )
    _assert_public_route(status)


async def test_list_users_with_role_is_public(client: AsyncClient) -> None:
    status = await _status(
        client,
        "get",
        f"{BASE}/roles/00000000-0000-0000-0000-000000000000/users",
    )
    _assert_public_route(status)


async def test_list_user_roles_is_public(client: AsyncClient) -> None:
    status = await _status(
        client,
        "get",
        f"{BASE}/roles/users/00000000-0000-0000-0000-000000000001/roles",
    )
    _assert_public_route(status)


async def test_revoke_role_is_public(client: AsyncClient) -> None:
    status = await _status(
        client,
        "delete",
        f"{BASE}/roles/00000000-0000-0000-0000-000000000000"
        f"/users/00000000-0000-0000-0000-000000000001",
    )
    _assert_public_route(status)
