"""drop CRM tables (no longer referenced by application code)

Revision ID: 0006_drop_crm_tables
Revises: 0005_drop_roles_name_check
Create Date: 2026-07-01 00:00:00

The CRM routes, services, schemas, and models have been removed. The
underlying tables are no longer referenced by any application code, so this
migration drops them to keep fresh installs lean.

Tables DROPPED (children before parents to satisfy FKs):
- quotation_line_items, quotation_versions
- quotations, site_visits, lost_enquiries
- enquiries, projects, contacts, companies
- staff_profiles

Tables KEPT (still used by auth/user code):
- users (from 0001)
- roles, user_roles (from 0003/0004 — referenced by User.roles and the
  `get_current_user_with_role` RBAC helper)

This migration is a no-op for databases that never had the CRM tables
(e.g. an install where 0003 was skipped).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from alembic import op

revision: str = "0006_drop_crm_tables"
down_revision: str | None = "0005_drop_roles_name_check"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = __import__("sqlalchemy").inspect(bind)

    # Drop in dependency order (leaves first). Each `drop_table` is wrapped
    # in a check because older databases may not have every table — but
    # on a fresh `alembic upgrade head` run, all of these were created by
    # 0003_crm_module.py so they should exist.
    for table in [
        "quotation_line_items",
        "quotation_versions",
        "quotations",
        "site_visits",
        "lost_enquiries",
        "enquiries",
        "projects",
        "contacts",
        "companies",
        "staff_profiles",
    ]:
        if table in inspector.get_table_names():
            op.drop_table(table)


def downgrade() -> None:
    # Downgrade is a no-op: we can't re-create the dropped tables here
    # without copying the schema from 0003_crm_module.py. If you need to
    # roll back, run `alembic downgrade 0005` instead.
    pass