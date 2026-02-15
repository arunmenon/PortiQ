"""Export jobs table

Revision ID: 021
Revises: 020
Create Date: 2026-02-14

Creates: export_jobs
Enums: exporttype, exportformat, exportjobstatus
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "021"
down_revision: str | None = "020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Create enum types ──────────────────────────────────────────────
    op.execute("""
        CREATE TYPE exporttype AS ENUM (
            'INVOICES', 'ORDERS', 'DELIVERIES', 'SETTLEMENTS',
            'INVOICE_SINGLE', 'DELIVERY_REPORT'
        );
    """)
    op.execute("""
        CREATE TYPE exportformat AS ENUM (
            'CSV', 'XLSX', 'PDF'
        );
    """)
    op.execute("""
        CREATE TYPE exportjobstatus AS ENUM (
            'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'EXPIRED'
        );
    """)

    # ── 2. Create export_jobs table ───────────────────────────────────────
    op.execute("""
        CREATE TABLE export_jobs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            requested_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            export_type exporttype NOT NULL,
            export_format exportformat NOT NULL,
            filters JSONB NOT NULL DEFAULT '{}',
            entity_id UUID,
            entity_type VARCHAR(30),
            status exportjobstatus NOT NULL DEFAULT 'PENDING',
            progress_percent INTEGER NOT NULL DEFAULT 0,
            error_message TEXT,
            s3_key VARCHAR(500),
            s3_bucket VARCHAR(100),
            file_name VARCHAR(255),
            file_size_bytes BIGINT,
            content_type VARCHAR(50),
            download_url_expires_at TIMESTAMPTZ,
            total_rows INTEGER,
            processed_rows INTEGER NOT NULL DEFAULT 0,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            expires_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX ix_export_jobs_organization_id ON export_jobs (organization_id);")
    op.execute("CREATE INDEX ix_export_jobs_requested_by ON export_jobs (requested_by);")
    op.execute("CREATE INDEX ix_export_jobs_status ON export_jobs (status);")

    # ── 3. RLS policies ──────────────────────────────────────────────────
    op.execute("ALTER TABLE export_jobs ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE export_jobs FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY export_jobs_select_policy ON export_jobs FOR SELECT
          USING (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY export_jobs_insert_policy ON export_jobs FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY export_jobs_update_policy ON export_jobs FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)


def downgrade() -> None:
    # ── Reverse RLS ────────────────────────────────────────────────────────
    op.execute("DROP POLICY IF EXISTS export_jobs_update_policy ON export_jobs;")
    op.execute("DROP POLICY IF EXISTS export_jobs_insert_policy ON export_jobs;")
    op.execute("DROP POLICY IF EXISTS export_jobs_select_policy ON export_jobs;")
    op.execute("ALTER TABLE export_jobs DISABLE ROW LEVEL SECURITY;")

    # ── Drop table ─────────────────────────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_export_jobs_status;")
    op.execute("DROP INDEX IF EXISTS ix_export_jobs_requested_by;")
    op.execute("DROP INDEX IF EXISTS ix_export_jobs_organization_id;")
    op.execute("DROP TABLE IF EXISTS export_jobs;")

    # ── Drop enum types ────────────────────────────────────────────────────
    op.execute("DROP TYPE IF EXISTS exportjobstatus;")
    op.execute("DROP TYPE IF EXISTS exportformat;")
    op.execute("DROP TYPE IF EXISTS exporttype;")
