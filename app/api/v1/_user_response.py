"""Shared helper for hydrating a User ORM row into a UserOut response.

The user router (`user.py`) and the role router's `list_users_with_role`
endpoint (`role.py`) both need to turn a `User` model instance into the
API-shaped `UserOut`, with `roles` as a list of `UserRoleBrief`.

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

from app.models.user import User
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


def build_user_out(user: User) -> UserOut:
    """Build a UserOut from a User model instance.

    `roles` reuses the selectin-loaded `User.roles` relationship (free).
    No extra query is needed now that the flat primary-role fields have
    been removed from UserOut.
    """
    brief_roles = [
        UserRoleBrief(role_id=r.id, role_name=r.name, role_code=r.role_code) for r in user.roles
    ]
    payload = _user_to_dict(user, brief_roles)
    return UserOut.model_validate(payload)
