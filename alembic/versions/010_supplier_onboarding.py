"""Supplier onboarding — profiles, KYC documents, and review logs

Revision ID: 010
Revises: 009
Create Date: 2026-02-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create new enum types ──────────────────────────────────────────
    op.execute("""
        CREATE TYPE suppliertier AS ENUM (
            'PENDING', 'BASIC', 'VERIFIED', 'PREFERRED', 'PREMIUM'
        );
    """)
    op.execute("""
        CREATE TYPE onboardingstatus AS ENUM (
            'STARTED', 'DOCUMENTS_PENDING', 'DOCUMENTS_SUBMITTED',
            'VERIFICATION_IN_PROGRESS', 'VERIFICATION_PASSED', 'VERIFICATION_FAILED',
            'MANUAL_REVIEW_PENDING', 'MANUAL_REVIEW_IN_PROGRESS',
            'APPROVED', 'REJECTED', 'SUSPENDED'
        );
    """)
    op.execute("""
        CREATE TYPE kycdocumenttype AS ENUM (
            'GST_CERTIFICATE', 'PAN_CARD', 'ADDRESS_PROOF',
            'INCORPORATION_CERT', 'BANK_STATEMENT', 'REFERENCE_LETTER',
            'AUDITED_FINANCIALS', 'INSURANCE_CERTIFICATE',
            'QUALITY_CERTIFICATION', 'DIRECTOR_ID'
        );
    """)
    op.execute("""
        CREATE TYPE kycdocumentstatus AS ENUM (
            'PENDING', 'VERIFIED', 'REJECTED', 'EXPIRED'
        );
    """)
    op.execute("""
        CREATE TYPE reviewaction AS ENUM (
            'SUBMITTED_FOR_REVIEW', 'REVIEW_STARTED',
            'APPROVED', 'REJECTED', 'SUSPENDED', 'REACTIVATED',
            'TIER_UPGRADE_REQUESTED', 'TIER_UPGRADED'
        );
    """)

    # ── 2. Create supplier_profiles table ─────────────────────────────────
    op.execute("""
        CREATE TABLE supplier_profiles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            tier suppliertier NOT NULL DEFAULT 'PENDING',
            onboarding_status onboardingstatus NOT NULL DEFAULT 'STARTED',
            company_name VARCHAR(255) NOT NULL,
            contact_name VARCHAR(255) NOT NULL,
            contact_email VARCHAR(255) NOT NULL,
            contact_phone VARCHAR(20),
            gst_number VARCHAR(20),
            pan_number VARCHAR(20),
            cin_number VARCHAR(25),
            address_line1 VARCHAR(255),
            address_line2 VARCHAR(255),
            city VARCHAR(100),
            state VARCHAR(100),
            pincode VARCHAR(10),
            country VARCHAR(100) NOT NULL DEFAULT 'India',
            categories JSONB NOT NULL DEFAULT '[]',
            port_coverage JSONB NOT NULL DEFAULT '[]',
            verification_results JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_supplier_profiles_org UNIQUE (organization_id)
        );
    """)
    op.execute("CREATE INDEX ix_supplier_profiles_org_id ON supplier_profiles (organization_id);")
    op.execute("CREATE INDEX ix_supplier_profiles_tier ON supplier_profiles (tier);")
    op.execute("CREATE INDEX ix_supplier_profiles_status ON supplier_profiles (onboarding_status);")

    # ── 3. Create supplier_kyc_documents table ────────────────────────────
    op.execute("""
        CREATE TABLE supplier_kyc_documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            supplier_id UUID NOT NULL REFERENCES supplier_profiles(id) ON DELETE CASCADE,
            document_type kycdocumenttype NOT NULL,
            file_key VARCHAR(512) NOT NULL,
            file_name VARCHAR(255) NOT NULL,
            status kycdocumentstatus NOT NULL DEFAULT 'PENDING',
            verified_at TIMESTAMPTZ,
            verified_by UUID REFERENCES users(id) ON DELETE SET NULL,
            expiry_date TIMESTAMPTZ,
            rejection_reason VARCHAR(500),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX ix_kyc_docs_supplier_id ON supplier_kyc_documents (supplier_id);")
    op.execute("CREATE INDEX ix_kyc_docs_status ON supplier_kyc_documents (status);")

    # ── 4. Create supplier_review_logs table ──────────────────────────────
    op.execute("""
        CREATE TABLE supplier_review_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            supplier_id UUID NOT NULL REFERENCES supplier_profiles(id) ON DELETE CASCADE,
            reviewer_id UUID REFERENCES users(id) ON DELETE SET NULL,
            action reviewaction NOT NULL,
            from_status onboardingstatus NOT NULL,
            to_status onboardingstatus NOT NULL,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX ix_review_logs_supplier_id ON supplier_review_logs (supplier_id);")
    op.execute("CREATE INDEX ix_review_logs_action ON supplier_review_logs (action);")

    # ── 5. RLS policies ──────────────────────────────────────────────────

    # 5a. supplier_profiles: org-scoped + platform admin read all
    op.execute("ALTER TABLE supplier_profiles ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE supplier_profiles FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY supplier_profiles_select_policy ON supplier_profiles FOR SELECT
          USING (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY supplier_profiles_insert_policy ON supplier_profiles FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY supplier_profiles_update_policy ON supplier_profiles FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY supplier_profiles_delete_policy ON supplier_profiles FOR DELETE
          USING (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)

    # 5b. supplier_kyc_documents: via supplier ownership
    op.execute("ALTER TABLE supplier_kyc_documents ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE supplier_kyc_documents FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY kyc_docs_select_policy ON supplier_kyc_documents FOR SELECT
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM supplier_profiles sp
              WHERE sp.id = supplier_kyc_documents.supplier_id
                AND sp.organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY kyc_docs_insert_policy ON supplier_kyc_documents FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM supplier_profiles sp
              WHERE sp.id = supplier_kyc_documents.supplier_id
                AND sp.organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY kyc_docs_update_policy ON supplier_kyc_documents FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM supplier_profiles sp
              WHERE sp.id = supplier_kyc_documents.supplier_id
                AND sp.organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM supplier_profiles sp
              WHERE sp.id = supplier_kyc_documents.supplier_id
                AND sp.organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY kyc_docs_delete_policy ON supplier_kyc_documents FOR DELETE
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM supplier_profiles sp
              WHERE sp.id = supplier_kyc_documents.supplier_id
                AND sp.organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)

    # 5c. supplier_review_logs: via supplier ownership
    op.execute("ALTER TABLE supplier_review_logs ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE supplier_review_logs FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY review_logs_select_policy ON supplier_review_logs FOR SELECT
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM supplier_profiles sp
              WHERE sp.id = supplier_review_logs.supplier_id
                AND sp.organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY review_logs_insert_policy ON supplier_review_logs FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM supplier_profiles sp
              WHERE sp.id = supplier_review_logs.supplier_id
                AND sp.organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)


def downgrade() -> None:
    # ── Reverse 5c: Drop review_logs RLS ──────────────────────────────────
    op.execute("DROP POLICY IF EXISTS review_logs_insert_policy ON supplier_review_logs;")
    op.execute("DROP POLICY IF EXISTS review_logs_select_policy ON supplier_review_logs;")
    op.execute("ALTER TABLE supplier_review_logs DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 5b: Drop kyc_docs RLS ────────────────────────────────────
    op.execute("DROP POLICY IF EXISTS kyc_docs_delete_policy ON supplier_kyc_documents;")
    op.execute("DROP POLICY IF EXISTS kyc_docs_update_policy ON supplier_kyc_documents;")
    op.execute("DROP POLICY IF EXISTS kyc_docs_insert_policy ON supplier_kyc_documents;")
    op.execute("DROP POLICY IF EXISTS kyc_docs_select_policy ON supplier_kyc_documents;")
    op.execute("ALTER TABLE supplier_kyc_documents DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 5a: Drop supplier_profiles RLS ───────────────────────────
    op.execute("DROP POLICY IF EXISTS supplier_profiles_delete_policy ON supplier_profiles;")
    op.execute("DROP POLICY IF EXISTS supplier_profiles_update_policy ON supplier_profiles;")
    op.execute("DROP POLICY IF EXISTS supplier_profiles_insert_policy ON supplier_profiles;")
    op.execute("DROP POLICY IF EXISTS supplier_profiles_select_policy ON supplier_profiles;")
    op.execute("ALTER TABLE supplier_profiles DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 4: Drop supplier_review_logs ──────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_review_logs_action;")
    op.execute("DROP INDEX IF EXISTS ix_review_logs_supplier_id;")
    op.execute("DROP TABLE IF EXISTS supplier_review_logs;")

    # ── Reverse 3: Drop supplier_kyc_documents ────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_kyc_docs_status;")
    op.execute("DROP INDEX IF EXISTS ix_kyc_docs_supplier_id;")
    op.execute("DROP TABLE IF EXISTS supplier_kyc_documents;")

    # ── Reverse 2: Drop supplier_profiles ─────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_supplier_profiles_status;")
    op.execute("DROP INDEX IF EXISTS ix_supplier_profiles_tier;")
    op.execute("DROP INDEX IF EXISTS ix_supplier_profiles_org_id;")
    op.execute("DROP TABLE IF EXISTS supplier_profiles;")

    # ── Reverse 1: Drop enum types ────────────────────────────────────────
    op.execute("DROP TYPE IF EXISTS reviewaction;")
    op.execute("DROP TYPE IF EXISTS kycdocumentstatus;")
    op.execute("DROP TYPE IF EXISTS kycdocumenttype;")
    op.execute("DROP TYPE IF EXISTS onboardingstatus;")
    op.execute("DROP TYPE IF EXISTS suppliertier;")
