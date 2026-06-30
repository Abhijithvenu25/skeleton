"""drop customers table

Revision ID: 0002_drop_customers
Revises: 0001_initial
Create Date: 2026-06-28 00:00:00

Removes the customers table and its indexes. The corresponding model, schemas,
service, and router were removed in the same change.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from alembic import op

revision: str = "0002_drop_customers"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

if TYPE_CHECKING:
    from collections.abc import Sequence


def upgrade() -> None:
    op.drop_index("ix_customers_active_name", table_name="customers")
    op.drop_index("ix_customers_company", table_name="customers")
    op.drop_index("ix_customers_phone", table_name="customers")
    op.drop_index("ix_customers_email", table_name="customers")
    op.drop_index("ix_customers_name", table_name="customers")
    op.drop_index("ix_customers_owner_id", table_name="customers")
    op.drop_table("customers")


def downgrade() -> None:
    # Customer model is intentionally absent from the codebase; downgrade is a
    # no-op stub so the migration graph stays linear. Re-create the table by
    # hand if you ever need to roll back.
    raise NotImplementedError(
        "downgrade is not supported for 0002_drop_customers; "
        "the Customer model no longer exists in the codebase."
    )
