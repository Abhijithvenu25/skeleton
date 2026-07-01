"""multi-role users via user_roles junction table

Revision ID: 0004_user_roles
Revises: 0003_crm_module
Create Date: 2026-06-30 00:00:00

Replaces the 1:1 `staff_profiles.role_id` foreign key with an N:M
`user_roles` junction table so a single user can hold multiple roles
(e.g. a sales executive who also performs site visits).

upgrade():
    1. Create user_roles(user_id, role_id, granted_at, granted_by_id)
       with PK(user_id, role_id) and a secondary index on role_id.
    2. Backfill from existing staff_profiles.role_id (only non-deleted
       profiles). Captures created_at/created_by_id for audit history.
    3. Drop the now-redundant staff_profiles.role_id column.

downgrade():
    Reverses in inverse order. role_id is re-added as nullable, then
    backfilled from user_roles taking the earliest grant per user
    (so a user with 3 historical grants keeps exactly one role after
    downgrade — matches the old cardinality). Then user_roles is dropped.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_user_roles"
down_revision: str | None = "0003_crm_module"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None



def upgrade() -> None:
    # 1. New N:M junction table
    op.create_table(
        "user_roles",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "role_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roles.id", ondelete="RESTRICT"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "granted_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("idx_user_roles_role", "user_roles", ["role_id"])

    # 2. Backfill from existing 1:1 staff_profiles.role_id (only live profiles)
    op.execute(
        """
        INSERT INTO user_roles (user_id, role_id, granted_at, granted_by_id)
        SELECT user_id, role_id, created_at, created_by_id
        FROM staff_profiles
        WHERE role_id IS NOT NULL
          AND deleted_at IS NULL
        """
    )

    # 3. Drop the now-redundant 1:1 column + its FK
    op.drop_constraint(
        "fk_staff_profiles_role_id_roles", "staff_profiles", type_="foreignkey"
    )
    op.drop_column("staff_profiles", "role_id")


def downgrade() -> None:
    # Inverse of upgrade: re-add role_id as nullable, backfill from user_roles
    # (earliest grant per user to preserve the original 1:1 cardinality), then
    # drop user_roles.
    op.add_column(
        "staff_profiles",
        sa.Column(
            "role_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_staff_profiles_role_id_roles",
        "staff_profiles",
        "roles",
        ["role_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    # Backfill: pick earliest grant per user so a user with N grants becomes
    # the single role they had first historically. Users with no grants stay NULL.
    op.execute(
        """
        UPDATE staff_profiles sp
        SET role_id = ur.role_id
        FROM (
            SELECT DISTINCT ON (user_id) user_id, role_id, granted_at
            FROM user_roles
            ORDER BY user_id, granted_at ASC
        ) ur
        WHERE sp.user_id = ur.user_id
        """
    )
    op.drop_index("idx_user_roles_role", table_name="user_roles")
    op.drop_table("user_roles")
    # role_id is left nullable on downgrade; the application only requires
    # NOT NULL going forward. To restore strictness, run a follow-up migration.
