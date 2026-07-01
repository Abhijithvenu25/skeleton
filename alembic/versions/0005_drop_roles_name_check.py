"""drop roles.name CHECK constraint

Revision ID: 0005_drop_roles_name_check
Revises: 0004_user_roles
Create Date: 2026-07-01 00:00:00

Removes the CHECK constraint that limits `roles.name` to
('sales_executive', 'engineer', 'admin', 'owner'). Roles are user-defined
and the application no longer wants to restrict them at the DB layer.

The original constraint was created in 0003_crm_module.py; this migration
is a no-op for fresh databases (0003 no longer creates it) but drops it
on environments that already applied 0003.

upgrade():
    Drop constraint ck_roles_name from roles.

downgrade():
    Re-add the constraint.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_drop_roles_name_check"
down_revision = "0004_user_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_roles_name", "roles", type_="check")


def downgrade() -> None:
    op.create_check_constraint(
        "ck_roles_name",
        "roles",
        "name IN ('sales_executive', 'engineer', 'admin', 'owner')",
    )