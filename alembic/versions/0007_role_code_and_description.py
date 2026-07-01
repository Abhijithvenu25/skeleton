"""add role_code and description columns to roles

Revision ID: 0007_role_code_and_description
Revises: 0006_drop_crm_tables
Create Date: 2026-07-02 00:00:00

Adds two columns to the `roles` table:

- `role_code` (TEXT, UNIQUE, indexed). Auto-generated business code in
  the form `R-<n>` (e.g. R-1, R-2, ...). Generated at insert time by the
  application (RoleService.create) — concurrent safety is enforced by
  the UNIQUE constraint + IntegrityError catch in the service, mirroring
  the existing pattern for `name` uniqueness.

- `description` (TEXT, nullable). Free-form human-readable description.

upgrade():
    1. Add the two columns. `role_code` is added WITHOUT a UNIQUE
       constraint first so the backfill can run freely; the unique
       index is added afterwards.
    2. Backfill `role_code` for existing rows in `created_at ASC` order
       — stable, deterministic. New rows will get codes assigned by the
       service from `max(numeric_suffix) + 1`.
    3. Add the UNIQUE index on `role_code`. (Using a unique INDEX rather
       than `UNIQUE` column constraint so PostgreSQL names it under the
       project's NAMING_CONVENTION as `uq_roles_role_code`.)

downgrade():
    Drops the unique index, then drops the columns. Inverse of upgrade.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import sqlalchemy as sa

from alembic import op

revision: str = "0007_role_code_and_description"
down_revision: str | None = "0006_drop_crm_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add columns. role_code is TEXT NOT NULL with no DEFAULT so the
    # backfill can populate it explicitly before we enforce uniqueness.
    op.add_column(
        "roles",
        sa.Column("role_code", sa.Text(), nullable=True),
    )
    op.add_column(
        "roles",
        sa.Column("description", sa.Text(), nullable=True),
    )

    # 2. Backfill role_code for any pre-existing rows in stable order.
    # row_number() over (ORDER BY created_at, id) makes the assignment
    # deterministic even if two rows share a created_at to the microsecond.
    op.execute(
        """
        UPDATE roles
        SET role_code = 'R-' || sub.rn
        FROM (
            SELECT id, row_number() OVER (ORDER BY created_at ASC, id ASC) AS rn
            FROM roles
        ) AS sub
        WHERE roles.id = sub.id
        """
    )

    # Now that every row has a value, flip NOT NULL and add the UNIQUE
    # index. Using a unique INDEX (rather than column-level UNIQUE) so
    # PostgreSQL names it `uq_roles_role_code` under the project's
    # NAMING_CONVENTION and the IntegrityError handler can map the
    # collision to a clean 409.
    op.alter_column("roles", "role_code", nullable=False)
    op.create_index(
        "uq_roles_role_code",
        "roles",
        ["role_code"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_roles_role_code", table_name="roles")
    op.drop_column("roles", "description")
    op.drop_column("roles", "role_code")