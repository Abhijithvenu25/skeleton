"""add user_image column to users

Revision ID: 0008_user_image
Revises: 0007_role_code_and_description
Create Date: 2026-07-02 00:00:00

Adds a nullable `user_image` column to the `users` table. Stores an
S3 URL (https://...) for the user's avatar/profile image. No
behavior change for existing rows: the column is NULL by default and
no backfill runs.

Length budget: 2048 chars covers the longest plausible S3 URL
(presigned variants, region-prefixed endpoints, etc.) with headroom.
Existing column constraints (`email`, `is_active`, etc.) are untouched.

downgrade():
    Drops the column. Inverse of upgrade; any data in `user_image`
    is lost.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import sqlalchemy as sa

from alembic import op

revision: str = "0008_user_image"
down_revision: str | None = "0007_role_code_and_description"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("user_image", sa.String(length=2048), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "user_image")