"""Unit tests for response-envelope helpers.

Pure-function tests — no DB / no HTTP. They pin the contract:
- single-resource responses are list-shaped (data[0])
- paginated lists carry PaginationInfo
- created_single reports status=201
- pagination math: total=0 -> 0 pages, mid-page -> correct has_next/has_prev
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.api.v1._response import created_single, ok_list, ok_single
from app.schemas.common import ApiResponse, PaginationInfo
from app.schemas.role import RoleOut


def _fake_role() -> RoleOut:
    now = datetime.now(UTC)
    return RoleOut(
        id=uuid.uuid4(),
        name="admin",
        permissions={"*": ["*"]},
        role_code="R-1",
        description=None,
        created_at=now,
        updated_at=now,
    )


def test_ok_single_wraps_in_list_and_sets_status_200() -> None:
    role = _fake_role()
    env = ok_single(role, "role fetched successfully.")

    assert isinstance(env, ApiResponse)
    dumped = env.model_dump()
    assert dumped["status"] == 200
    assert dumped["message"] == "role fetched successfully."
    assert dumped["data"] == [role.model_dump()]
    assert dumped["pagination"] is None


def test_created_single_sets_status_201() -> None:
    env = created_single(_fake_role(), "role created successfully.")
    assert env.status == 201
    assert len(env.data) == 1
    assert env.message == "role created successfully."


def test_ok_list_builds_pagination_mid_page() -> None:
    items = [_fake_role() for _ in range(20)]
    env = ok_list(items, page=3, size=20, total=100, message="roles fetched successfully.")

    assert env.status == 200
    assert len(env.data) == 20
    assert env.message == "roles fetched successfully."
    assert env.pagination == PaginationInfo(
        current_page=3,
        total_pages=5,
        total_records=100,
        has_next=True,
        has_previous=True,
    )


def test_ok_list_page_one_has_no_previous() -> None:
    env = ok_list([_fake_role()], page=1, size=20, total=100, message="x")
    assert env.pagination is not None
    assert env.pagination.has_previous is False
    assert env.pagination.has_next is True


def test_ok_list_last_page_has_no_next() -> None:
    env = ok_list([_fake_role()], page=5, size=20, total=100, message="x")
    assert env.pagination is not None
    assert env.pagination.has_previous is True
    assert env.pagination.has_next is False


def test_ok_list_empty_returns_zero_pages() -> None:
    env: ApiResponse[RoleOut] = ok_list(
        [], page=1, size=20, total=0, message="roles fetched successfully."
    )
    assert env.data == []
    assert env.pagination == PaginationInfo(
        current_page=1,
        total_pages=0,
        total_records=0,
        has_next=False,
        has_previous=False,
    )


def test_ok_list_partial_final_page() -> None:
    env = ok_list([_fake_role()] * 7, page=4, size=20, total=67, message="x")
    assert env.pagination is not None
    # ceil(67 / 20) == 4
    assert env.pagination.total_pages == 4
    assert env.pagination.has_next is False  # last page
    assert env.pagination.has_previous is True
