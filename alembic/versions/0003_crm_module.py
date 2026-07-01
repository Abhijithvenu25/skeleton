"""crm module: roles, staff_profiles, companies, contacts, projects,
enquiries, site_visits, quotations, quotation_versions, quotation_line_items,
lost_enquiries

Revision ID: 0003_crm_module
Revises: 0002_drop_customers
Create Date: 2026-06-30 00:00:00

Creates the full CRM schema per docs/crm-erd.md:
- 11 tables with audit + soft-delete mixins
- CHECK constraints for enum-like columns
- Partial indexes including a partial unique index on contacts.is_primary
- Three Postgres SEQUENCEs + triggers for ENQ-001, VIS-001, QT-001 numbering
- Seeds the 4 base roles + a disabled system user for audit FK backfill
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_crm_module"
down_revision: str | None = "0002_drop_customers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

if TYPE_CHECKING:
    pass


_SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000001"
_SYSTEM_USER_EMAIL = "system@kalisia.local"
_SYSTEM_USER_FULL_NAME = "System"
# Bcrypt hash that nobody can log in with (random salt + ~infinite cost). The
# `is_active=false` account is the real lock — this just satisfies NOT NULL.
_SYSTEM_USER_HASH = "$2b$12$0000000000000000000000.0000000000000000000000000000000000"


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. System user (audit FK backfill target)
    # ------------------------------------------------------------------
    # NOTE: values are constants (not user input) so inline interpolation is safe.
    op.execute(
        f"INSERT INTO users (id, email, hashed_password, full_name, "
        f"is_active, is_superuser, created_at, updated_at) VALUES ("
        f"'{_SYSTEM_USER_ID}', '{_SYSTEM_USER_EMAIL}', '{_SYSTEM_USER_HASH}', "
        f"'{_SYSTEM_USER_FULL_NAME}', false, false, now(), now()) "
        f"ON CONFLICT (id) DO NOTHING"
    )

    # ------------------------------------------------------------------
    # 2. Sequences (ENQ-001, VIS-001, QT-001) — created BEFORE tables that
    #    reference them in triggers. Idempotent across re-runs.
    # ------------------------------------------------------------------
    for seq in ("enquiry_seq", "site_visit_seq", "quotation_seq"):
        op.execute(f"CREATE SEQUENCE IF NOT EXISTS {seq}")

    # ------------------------------------------------------------------
    # 3. Tables (in FK dependency order)
    # ------------------------------------------------------------------

    # 3.1 roles — no FKs, system table, no audit
    op.create_table(
        "roles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column(
            "permissions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("name", name="uq_roles_name"),
    )

    # 3.2 staff_profiles — PK = user_id, FKs to users + roles
    op.create_table(
        "staff_profiles",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "role_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("employee_code", sa.String(length=64), nullable=True),
        sa.Column("department", sa.String(length=128), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("joined_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            server_default=sa.text(f"'{_SYSTEM_USER_ID}'::uuid"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "updated_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("employee_code", name="uq_staff_profiles_employee_code"),
    )

    # 3.3 companies — soft-delete, audit
    op.create_table(
        "companies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("street", sa.String(length=255), nullable=True),
        sa.Column("address_line2", sa.String(length=255), nullable=True),
        sa.Column("landmark", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("state", sa.String(length=128), nullable=True),
        sa.Column("country", sa.String(length=128), nullable=True),
        sa.Column("pin", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            server_default=sa.text(f"'{_SYSTEM_USER_ID}'::uuid"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "updated_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "deleted_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_companies_active_name",
        "companies",
        ["name"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # 3.4 contacts — soft-delete, audit
    op.create_table(
        "contacts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=True),
        sa.Column("mobile", sa.String(length=32), nullable=True),
        sa.Column("designation", sa.String(length=128), nullable=True),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            server_default=sa.text(f"'{_SYSTEM_USER_ID}'::uuid"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "updated_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "deleted_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    # Partial unique: at most one is_primary contact per active company.
    op.create_index(
        "uq_contacts_company_primary",
        "contacts",
        ["company_id"],
        unique=True,
        postgresql_where=sa.text("is_primary AND deleted_at IS NULL"),
    )

    # 3.5 projects — soft-delete, audit
    op.create_table(
        "projects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("project_type", sa.String(length=32), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            server_default=sa.text(f"'{_SYSTEM_USER_ID}'::uuid"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "updated_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "deleted_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "project_type IN ('residential','commercial','industrial','renovation','other')",
            name="ck_projects_project_type",
        ),
    )

    # 3.6 enquiries — soft-delete, audit, trigger-assigned enquiry_no
    op.create_table(
        "enquiries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # enquiry_no: assigned by trigger; nullable window only during INSERT.
        sa.Column("enquiry_no", sa.String(length=32), nullable=False, server_default=""),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contacts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "sales_executive_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "engineer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default=sa.text("'medium'")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'enquiry'")),
        sa.Column("enquiry_date", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            server_default=sa.text(f"'{_SYSTEM_USER_ID}'::uuid"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "updated_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "deleted_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "source IN ('email','whatsapp','instagram','facebook','linkedin',"
            "'website','direct_call','referral','tender','other')",
            name="ck_enquiries_source",
        ),
        sa.CheckConstraint("priority IN ('high','medium','low')", name="ck_enquiries_priority"),
        sa.CheckConstraint(
            "status IN ('enquiry','site_visit','quotation','accepted','lost')",
            name="ck_enquiries_status",
        ),
        sa.UniqueConstraint("enquiry_no", name="uq_enquiries_enquiry_no"),
    )
    op.create_index(
        "ix_enquiries_exec_status",
        "enquiries",
        ["sales_executive_id", "status"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_enquiries_status_date",
        "enquiries",
        ["status", sa.text("enquiry_date DESC")],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_enquiries_engineer_status",
        "enquiries",
        ["engineer_id", "status"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # 3.7 site_visits — cascade-delete from enquiries, audit, trigger-assigned visit_no
    op.create_table(
        "site_visits",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("visit_no", sa.String(length=32), nullable=False, server_default=""),
        sa.Column(
            "enquiry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("enquiries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "engineer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "sales_executive_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'scheduled'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            server_default=sa.text(f"'{_SYSTEM_USER_ID}'::uuid"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "updated_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('scheduled','completed')", name="ck_site_visits_status"),
        sa.UniqueConstraint("visit_no", name="uq_site_visits_visit_no"),
    )
    op.create_index(
        "ix_site_visits_enquiry_scheduled",
        "site_visits",
        ["enquiry_id", sa.text("scheduled_at DESC")],
    )
    op.create_index(
        "ix_site_visits_engineer_date",
        "site_visits",
        ["engineer_id", "scheduled_at"],
    )

    # 3.8 quotations — cascade-delete from enquiries, audit, trigger-assigned quote_no
    op.create_table(
        "quotations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("quote_no", sa.String(length=32), nullable=False, server_default=""),
        sa.Column(
            "enquiry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("enquiries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("current_version_no", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("sent_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            server_default=sa.text(f"'{_SYSTEM_USER_ID}'::uuid"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "updated_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("current_version_no > 0", name="ck_quotations_current_version_no"),
        sa.CheckConstraint(
            "status IN ('draft','sent','accepted','rejected')",
            name="ck_quotations_status",
        ),
        sa.UniqueConstraint("quote_no", name="uq_quotations_quote_no"),
    )
    op.create_index(
        "ix_quotations_enquiry_status",
        "quotations",
        ["enquiry_id", "status"],
    )

    # 3.9 quotation_versions — cascade, immutable (created_at only), audit (created_by only)
    op.create_table(
        "quotation_versions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "quotation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quotations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("file_url", sa.String(length=512), nullable=True),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("version_no > 0", name="ck_quotation_versions_version_no"),
        sa.CheckConstraint("amount >= 0", name="ck_quotation_versions_amount"),
        sa.UniqueConstraint("quotation_id", "version_no", name="uq_quotation_versions_quote_version"),
    )

    # 3.10 quotation_line_items — cascade from quotation_versions, audit
    op.create_table(
        "quotation_line_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "quotation_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quotation_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("line_type", sa.String(length=16), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            server_default=sa.text(f"'{_SYSTEM_USER_ID}'::uuid"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "updated_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "line_type IN ('material','labour','tax','other')",
            name="ck_quotation_line_items_line_type",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_quotation_line_items_quantity"),
        sa.CheckConstraint("unit_price >= 0", name="ck_quotation_line_items_unit_price"),
        sa.CheckConstraint("line_total >= 0", name="ck_quotation_line_items_line_total"),
    )
    op.create_index(
        "ix_quotation_lines_version_order",
        "quotation_line_items",
        ["quotation_version_id", "sort_order"],
    )

    # 3.11 lost_enquiries — cascade-only, no deleted_at, audit
    op.create_table(
        "lost_enquiries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "enquiry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("enquiries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage_lost", sa.String(length=16), nullable=False),
        sa.Column("reason_lost", sa.Text(), nullable=True),
        sa.Column("date_lost", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("follow_up_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            server_default=sa.text(f"'{_SYSTEM_USER_ID}'::uuid"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "updated_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "stage_lost IN ('enquiry','site_visit','quotation')",
            name="ck_lost_enquiries_stage_lost",
        ),
        sa.UniqueConstraint("enquiry_id", name="uq_lost_enquiries_enquiry_id"),
    )
    op.create_index(
        "ix_lost_follow_up",
        "lost_enquiries",
        ["follow_up_date"],
        postgresql_where=sa.text("follow_up_date IS NOT NULL"),
    )

    # ------------------------------------------------------------------
    # 4. Triggers for ENQ-001, VIS-001, QT-001 numbering
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_enquiry_no() RETURNS trigger AS $$
        BEGIN
            IF NEW.enquiry_no IS NULL OR NEW.enquiry_no = '' THEN
                NEW.enquiry_no := 'ENQ-' || lpad(nextval('enquiry_seq')::text, 3, '0');
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_enquiries_no ON enquiries")
    op.execute(
        "CREATE TRIGGER trg_enquiries_no BEFORE INSERT ON enquiries "
        "FOR EACH ROW EXECUTE FUNCTION set_enquiry_no()"
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_site_visit_no() RETURNS trigger AS $$
        BEGIN
            IF NEW.visit_no IS NULL OR NEW.visit_no = '' THEN
                NEW.visit_no := 'VIS-' || lpad(nextval('site_visit_seq')::text, 3, '0');
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_site_visits_no ON site_visits")
    op.execute(
        "CREATE TRIGGER trg_site_visits_no BEFORE INSERT ON site_visits "
        "FOR EACH ROW EXECUTE FUNCTION set_site_visit_no()"
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_quotation_no() RETURNS trigger AS $$
        BEGIN
            IF NEW.quote_no IS NULL OR NEW.quote_no = '' THEN
                NEW.quote_no := 'QT-' || lpad(nextval('quotation_seq')::text, 3, '0');
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_quotations_no ON quotations")
    op.execute(
        "CREATE TRIGGER trg_quotations_no BEFORE INSERT ON quotations "
        "FOR EACH ROW EXECUTE FUNCTION set_quotation_no()"
    )

    # ------------------------------------------------------------------
    # 5. Role seed
    # ------------------------------------------------------------------
    op.execute(
        """
        INSERT INTO roles (name, permissions) VALUES
            ('sales_executive', '{}'::jsonb),
            ('engineer',        '{}'::jsonb),
            ('admin',           '{}'::jsonb),
            ('owner',           '{}'::jsonb)
        ON CONFLICT (name) DO NOTHING
        """
    )


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    # Reverse order: triggers, then tables (in reverse FK dependency), then
    # indexes, then sequences, then role seed, then system user.

    # 1. Triggers + functions
    op.execute("DROP TRIGGER IF EXISTS trg_enquiries_no ON enquiries")
    op.execute("DROP TRIGGER IF EXISTS trg_site_visits_no ON site_visits")
    op.execute("DROP TRIGGER IF EXISTS trg_quotations_no ON quotations")
    op.execute("DROP FUNCTION IF EXISTS set_enquiry_no()")
    op.execute("DROP FUNCTION IF EXISTS set_site_visit_no()")
    op.execute("DROP FUNCTION IF EXISTS set_quotation_no()")

    # 2. Tables (reverse FK order)
    op.drop_table("quotation_line_items")
    op.drop_table("quotation_versions")
    op.drop_table("quotations")
    op.drop_table("site_visits")
    op.drop_table("lost_enquiries")
    op.drop_table("enquiries")
    op.drop_table("projects")
    op.drop_table("contacts")
    op.drop_table("companies")
    op.drop_table("staff_profiles")
    op.drop_table("roles")

    # 3. Sequences
    op.execute("DROP SEQUENCE IF EXISTS quotation_seq")
    op.execute("DROP SEQUENCE IF EXISTS site_visit_seq")
    op.execute("DROP SEQUENCE IF EXISTS enquiry_seq")

    # 4. System user (only delete this ID — never touch real users)
    op.execute(f"DELETE FROM users WHERE id = '{_SYSTEM_USER_ID}'")
