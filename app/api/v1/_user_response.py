"""Shared helper for hydrating a User ORM row into a UserOut response.

The user router (`user.py`) and the role router's `list_users_with_role`
endpoint (`role.py`) both need to turn a `User` model instance into the
API-shaped `UserOut`, with `roles` as a list of `UserRoleBrief` and the
flat primary `role_id`/`role_name`/`role_code` populated.

`UserOut.model_validate(user)` does NOT work directly when the response
shape contains a `roles` field with renamed columns (`role_id`,
`role_name`, `role_code`) — Pydantic eagerly coerces each element of
`user.roles` (a list of `Role` instances) into `UserRoleBrief`, but
attribute-name matching fails because `Role.id` ≠ `UserRoleBrief.role_id`.
The fix is to validate from a dict with `roles` already in the brief
shape so Pydantic skips the inner coercion entirely.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.user import UserOut, UserRoleBrief


def _user_to_dict(user: User, brief_roles: list[UserRoleBrief]) -> dict[str, Any]:
    """Project the User ORM row into the dict shape UserOut expects.

    The relationship attributes (`roles`) are replaced with the
    pre-built brief list; everything else is taken verbatim from the
    ORM row.
    """
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "created_at": user.created_at,
        "roles": brief_roles,
    }


async def build_user_out(session: AsyncSession, user: User) -> UserOut:
    """Build a UserOut from a User model instance.

    `roles` reuses the selectin-loaded `User.roles` relationship (free).
    `role_id` / `role_name` / `role_code` come from a targeted ordered
    join — the earliest grant is the "primary" role. One extra query.
    """
    stmt = (
        select(Role.id, Role.name, Role.role_code)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
        .order_by(UserRole.granted_at.asc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.first()

    brief_roles = [
        UserRoleBrief(role_id=r.id, role_name=r.name, role_code=r.role_code) for r in user.roles
    ]

    # Validate from a dict with `roles` already in brief shape. Passing
    # the ORM row directly would coerce each `Role` into `UserRoleBrief`
    # by attribute-name matching, which silently fails because `Role.id`
    # doesn't match `UserRoleBrief.role_id`.
    payload = _user_to_dict(user, brief_roles)
    out = UserOut.model_validate(payload)
    if row is not None:
        out.role_id = row[0]
        out.role_name = row[1]
        out.role_code = row[2]
    return out
