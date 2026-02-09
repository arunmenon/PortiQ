"""Document AI extraction tables

Revision ID: 014
Revises: 013
Create Date: 2026-02-08

Creates: document_extractions, extracted_line_items
Enums: extractionstatus, extractionconfidencetier, documenttype
RLS: admin bypass + owner (uploaded_by) + org membership through rfqs
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "014"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Create enum types ──────────────────────────────────────────────
    op.execute("""
        CREATE TYPE extractionstatus AS ENUM (
            'PENDING', 'PARSING', 'NORMALIZING', 'MATCHING',
            'ROUTING', 'COMPLETED', 'FAILED'
        );
    """)
    op.execute("""
        CREATE TYPE extractionconfidencetier AS ENUM (
            'AUTO', 'QUICK_REVIEW', 'FULL_REVIEW'
        );
    """)
    op.execute("""
        CREATE TYPE documenttype AS ENUM (
            'SYSTEM_REQUISITION', 'PURCHASE_ORDER', 'INVENTORY_LIST',
            'MAINTENANCE_EXPORT', 'HANDWRITTEN_FORM', 'MARKED_CATALOG',
            'NAMEPLATE_PHOTO', 'MIXED_FORM'
        );
    """)

    # ── 2. Create document_extractions table ──────────────────────────────
    op.execute("""
        CREATE TABLE document_extractions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            rfq_id UUID REFERENCES rfqs(id) ON DELETE SET NULL,
            uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
            filename VARCHAR(255) NOT NULL,
            file_type VARCHAR(50) NOT NULL,
            file_size_bytes INTEGER NOT NULL,
            document_type documenttype,
            status extractionstatus NOT NULL DEFAULT 'PENDING',
            azure_result_url TEXT,
            raw_extraction JSONB,
            error_message TEXT,
            total_items_found INTEGER NOT NULL DEFAULT 0,
            items_auto INTEGER NOT NULL DEFAULT 0,
            items_quick_review INTEGER NOT NULL DEFAULT 0,
            items_full_review INTEGER NOT NULL DEFAULT 0,
            processing_started_at TIMESTAMPTZ,
            processing_completed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute(
        "CREATE INDEX ix_document_extractions_rfq_id ON document_extractions (rfq_id);"
    )
    op.execute(
        "CREATE INDEX ix_document_extractions_uploaded_by ON document_extractions (uploaded_by);"
    )
    op.execute(
        "CREATE INDEX ix_document_extractions_status ON document_extractions (status);"
    )

    # ── 3. Create extracted_line_items table ───────────────────────────────
    op.execute("""
        CREATE TABLE extracted_line_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            extraction_id UUID NOT NULL REFERENCES document_extractions(id) ON DELETE CASCADE,
            line_number INTEGER NOT NULL,
            raw_text TEXT NOT NULL,
            normalized_description VARCHAR(500),
            detected_quantity NUMERIC(12,3),
            detected_unit VARCHAR(20),
            detected_impa_code VARCHAR(10),
            matched_impa_code VARCHAR(10),
            matched_product_id UUID REFERENCES products(id) ON DELETE SET NULL,
            match_confidence DOUBLE PRECISION,
            match_method VARCHAR(20),
            confidence_tier extractionconfidencetier,
            specifications JSONB,
            is_duplicate BOOLEAN NOT NULL DEFAULT false,
            duplicate_of_id UUID REFERENCES extracted_line_items(id) ON DELETE SET NULL,
            user_verified BOOLEAN NOT NULL DEFAULT false,
            user_corrected_impa VARCHAR(10),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_extracted_line_items_extraction_line UNIQUE (extraction_id, line_number)
        );
    """)
    op.execute(
        "CREATE INDEX ix_extracted_line_items_extraction_id ON extracted_line_items (extraction_id);"
    )
    op.execute(
        "CREATE INDEX ix_extracted_line_items_matched_product_id ON extracted_line_items (matched_product_id);"
    )
    op.execute(
        "CREATE INDEX ix_extracted_line_items_confidence_tier ON extracted_line_items (confidence_tier);"
    )

    # ── 4. RLS policies ──────────────────────────────────────────────────

    # 4a. document_extractions: admin bypass + owner + org membership via rfqs
    op.execute("ALTER TABLE document_extractions ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE document_extractions FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY document_extractions_select_policy ON document_extractions FOR SELECT
          USING (
            is_admin_bypass_active()
            OR uploaded_by::text = get_tenant_setting('app.current_user_id')
            OR EXISTS (
              SELECT 1 FROM rfqs r
              WHERE r.id = document_extractions.rfq_id
                AND r.buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY document_extractions_insert_policy ON document_extractions FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR uploaded_by::text = get_tenant_setting('app.current_user_id')
          );
    """)
    op.execute("""
        CREATE POLICY document_extractions_update_policy ON document_extractions FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR uploaded_by::text = get_tenant_setting('app.current_user_id')
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR uploaded_by::text = get_tenant_setting('app.current_user_id')
          );
    """)
    op.execute("""
        CREATE POLICY document_extractions_delete_policy ON document_extractions FOR DELETE
          USING (
            is_admin_bypass_active()
            OR uploaded_by::text = get_tenant_setting('app.current_user_id')
          );
    """)

    # 4b. extracted_line_items: visible via extraction ownership
    op.execute("ALTER TABLE extracted_line_items ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE extracted_line_items FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY extracted_line_items_select_policy ON extracted_line_items FOR SELECT
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM document_extractions de
              WHERE de.id = extracted_line_items.extraction_id
                AND (
                  de.uploaded_by::text = get_tenant_setting('app.current_user_id')
                  OR EXISTS (
                    SELECT 1 FROM rfqs r
                    WHERE r.id = de.rfq_id
                      AND r.buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
                  )
                )
            )
          );
    """)
    op.execute("""
        CREATE POLICY extracted_line_items_insert_policy ON extracted_line_items FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM document_extractions de
              WHERE de.id = extracted_line_items.extraction_id
                AND de.uploaded_by::text = get_tenant_setting('app.current_user_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY extracted_line_items_update_policy ON extracted_line_items FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM document_extractions de
              WHERE de.id = extracted_line_items.extraction_id
                AND de.uploaded_by::text = get_tenant_setting('app.current_user_id')
            )
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM document_extractions de
              WHERE de.id = extracted_line_items.extraction_id
                AND de.uploaded_by::text = get_tenant_setting('app.current_user_id')
            )
          );
    """)


def downgrade() -> None:
    # ── Reverse 4b: Drop extracted_line_items RLS ─────────────────────────
    op.execute(
        "DROP POLICY IF EXISTS extracted_line_items_update_policy ON extracted_line_items;"
    )
    op.execute(
        "DROP POLICY IF EXISTS extracted_line_items_insert_policy ON extracted_line_items;"
    )
    op.execute(
        "DROP POLICY IF EXISTS extracted_line_items_select_policy ON extracted_line_items;"
    )
    op.execute("ALTER TABLE extracted_line_items DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 4a: Drop document_extractions RLS ─────────────────────────
    op.execute(
        "DROP POLICY IF EXISTS document_extractions_delete_policy ON document_extractions;"
    )
    op.execute(
        "DROP POLICY IF EXISTS document_extractions_update_policy ON document_extractions;"
    )
    op.execute(
        "DROP POLICY IF EXISTS document_extractions_insert_policy ON document_extractions;"
    )
    op.execute(
        "DROP POLICY IF EXISTS document_extractions_select_policy ON document_extractions;"
    )
    op.execute("ALTER TABLE document_extractions DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 3: Drop extracted_line_items ──────────────────────────────
    op.execute(
        "DROP INDEX IF EXISTS ix_extracted_line_items_confidence_tier;"
    )
    op.execute(
        "DROP INDEX IF EXISTS ix_extracted_line_items_matched_product_id;"
    )
    op.execute(
        "DROP INDEX IF EXISTS ix_extracted_line_items_extraction_id;"
    )
    op.execute("DROP TABLE IF EXISTS extracted_line_items;")

    # ── Reverse 2: Drop document_extractions ──────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_document_extractions_status;")
    op.execute("DROP INDEX IF EXISTS ix_document_extractions_uploaded_by;")
    op.execute("DROP INDEX IF EXISTS ix_document_extractions_rfq_id;")
    op.execute("DROP TABLE IF EXISTS document_extractions;")

    # ── Reverse 1: Drop enum types ───────────────────────────────────────
    op.execute("DROP TYPE IF EXISTS documenttype;")
    op.execute("DROP TYPE IF EXISTS extractionconfidencetier;")
    op.execute("DROP TYPE IF EXISTS extractionstatus;")
