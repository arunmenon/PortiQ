"""Dispute resolution tables

Revision ID: 019
Revises: 018
Create Date: 2026-02-14

Creates: disputes, dispute_comments, dispute_transitions
Enums: disputetype, disputestatus, disputepriority, disputeresolutiontype
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "019"
down_revision: str | None = "018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Create enum types ──────────────────────────────────────────────
    op.execute("""
        CREATE TYPE disputetype AS ENUM (
            'QUANTITY_SHORTAGE', 'QUALITY_ISSUE', 'WRONG_PRODUCT',
            'DAMAGED_GOODS', 'PRICE_DISPUTE', 'LATE_DELIVERY', 'OTHER'
        );
    """)
    op.execute("""
        CREATE TYPE disputestatus AS ENUM (
            'OPEN', 'UNDER_REVIEW', 'AWAITING_SUPPLIER',
            'AWAITING_BUYER', 'RESOLVED', 'ESCALATED', 'CLOSED'
        );
    """)
    op.execute("""
        CREATE TYPE disputepriority AS ENUM (
            'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
        );
    """)
    op.execute("""
        CREATE TYPE disputeresolutiontype AS ENUM (
            'CREDIT_NOTE', 'REFUND', 'REPLACEMENT',
            'PRICE_ADJUSTMENT', 'NO_ACTION', 'SPLIT'
        );
    """)

    # ── 2. Create disputes table ───────────────────────────────────────────
    op.execute("""
        CREATE TABLE disputes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            dispute_number VARCHAR(50) NOT NULL,
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

            -- Links
            delivery_id UUID REFERENCES deliveries(id) ON DELETE SET NULL,
            delivery_item_id UUID REFERENCES delivery_items(id) ON DELETE SET NULL,
            order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            vendor_order_id UUID REFERENCES vendor_orders(id) ON DELETE SET NULL,

            -- Parties
            raised_by_org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            raised_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            supplier_org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            assigned_reviewer_id UUID REFERENCES users(id) ON DELETE SET NULL,

            -- Dispute details
            dispute_type disputetype NOT NULL,
            status disputestatus NOT NULL DEFAULT 'OPEN',
            priority disputepriority NOT NULL DEFAULT 'MEDIUM',

            title VARCHAR(500) NOT NULL,
            description TEXT NOT NULL,

            -- Financial
            disputed_amount NUMERIC(15, 2),
            currency VARCHAR(3) NOT NULL DEFAULT 'USD',
            resolution_type disputeresolutiontype,
            resolution_amount NUMERIC(15, 2),
            resolution_notes TEXT,

            -- SLA
            response_due_at TIMESTAMPTZ,
            resolution_due_at TIMESTAMPTZ,
            sla_breached BOOLEAN NOT NULL DEFAULT FALSE,

            -- Timestamps
            resolved_at TIMESTAMPTZ,
            resolved_by UUID REFERENCES users(id) ON DELETE SET NULL,
            escalated_at TIMESTAMPTZ,
            escalated_by UUID REFERENCES users(id) ON DELETE SET NULL,
            closed_at TIMESTAMPTZ,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_disputes_dispute_number UNIQUE (dispute_number)
        );
    """)
    op.execute("CREATE INDEX ix_disputes_organization_id ON disputes (organization_id);")
    op.execute("CREATE INDEX ix_disputes_order_id ON disputes (order_id);")
    op.execute("CREATE INDEX ix_disputes_delivery_id ON disputes (delivery_id) WHERE delivery_id IS NOT NULL;")
    op.execute("CREATE INDEX ix_disputes_status ON disputes (status);")
    op.execute("CREATE INDEX ix_disputes_supplier_org_id ON disputes (supplier_org_id);")

    # ── 3. Create dispute_comments table ───────────────────────────────────
    op.execute("""
        CREATE TABLE dispute_comments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            dispute_id UUID NOT NULL REFERENCES disputes(id) ON DELETE CASCADE,
            author_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            author_org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

            content TEXT NOT NULL,
            is_internal BOOLEAN NOT NULL DEFAULT FALSE,

            -- Attachment (optional)
            attachment_s3_key VARCHAR(500),
            attachment_filename VARCHAR(255),
            attachment_content_type VARCHAR(50),

            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX ix_dispute_comments_dispute_id ON dispute_comments (dispute_id);")

    # ── 4. Create dispute_transitions table ────────────────────────────────
    op.execute("""
        CREATE TABLE dispute_transitions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            dispute_id UUID NOT NULL REFERENCES disputes(id) ON DELETE CASCADE,
            from_status disputestatus NOT NULL,
            to_status disputestatus NOT NULL,
            transitioned_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            reason TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX ix_dispute_transitions_dispute_id ON dispute_transitions (dispute_id);")

    # ── 5. RLS policies ───────────────────────────────────────────────────
    # disputes: admin OR organization_id OR raised_by_org OR supplier_org
    op.execute("ALTER TABLE disputes ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE disputes FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY disputes_select_policy ON disputes FOR SELECT
          USING (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
            OR raised_by_org_id::text = get_tenant_setting('app.current_organization_id')
            OR supplier_org_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY disputes_insert_policy ON disputes FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR raised_by_org_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY disputes_update_policy ON disputes FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
            OR raised_by_org_id::text = get_tenant_setting('app.current_organization_id')
            OR supplier_org_id::text = get_tenant_setting('app.current_organization_id')
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
            OR raised_by_org_id::text = get_tenant_setting('app.current_organization_id')
            OR supplier_org_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)

    # dispute_comments: via disputes ownership + internal visibility
    op.execute("ALTER TABLE dispute_comments ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE dispute_comments FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY dispute_comments_select_policy ON dispute_comments FOR SELECT
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM disputes d
              WHERE d.id = dispute_comments.dispute_id
                AND (
                  d.organization_id::text = get_tenant_setting('app.current_organization_id')
                  OR d.raised_by_org_id::text = get_tenant_setting('app.current_organization_id')
                  OR d.supplier_org_id::text = get_tenant_setting('app.current_organization_id')
                )
            )
            AND (
              NOT dispute_comments.is_internal
              OR dispute_comments.author_org_id::text = get_tenant_setting('app.current_organization_id')
              OR is_admin_bypass_active()
            )
          );
    """)
    op.execute("""
        CREATE POLICY dispute_comments_insert_policy ON dispute_comments FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM disputes d
              WHERE d.id = dispute_comments.dispute_id
                AND (
                  d.raised_by_org_id::text = get_tenant_setting('app.current_organization_id')
                  OR d.supplier_org_id::text = get_tenant_setting('app.current_organization_id')
                )
            )
          );
    """)

    # dispute_transitions: via disputes ownership (read-only for non-admin)
    op.execute("ALTER TABLE dispute_transitions ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE dispute_transitions FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY dispute_transitions_select_policy ON dispute_transitions FOR SELECT
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM disputes d
              WHERE d.id = dispute_transitions.dispute_id
                AND (
                  d.organization_id::text = get_tenant_setting('app.current_organization_id')
                  OR d.raised_by_org_id::text = get_tenant_setting('app.current_organization_id')
                  OR d.supplier_org_id::text = get_tenant_setting('app.current_organization_id')
                )
            )
          );
    """)
    op.execute("""
        CREATE POLICY dispute_transitions_insert_policy ON dispute_transitions FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM disputes d
              WHERE d.id = dispute_transitions.dispute_id
                AND (
                  d.raised_by_org_id::text = get_tenant_setting('app.current_organization_id')
                  OR d.supplier_org_id::text = get_tenant_setting('app.current_organization_id')
                )
            )
          );
    """)


def downgrade() -> None:
    # ── Reverse RLS ────────────────────────────────────────────────────────
    op.execute("DROP POLICY IF EXISTS dispute_transitions_insert_policy ON dispute_transitions;")
    op.execute("DROP POLICY IF EXISTS dispute_transitions_select_policy ON dispute_transitions;")
    op.execute("ALTER TABLE dispute_transitions DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS dispute_comments_insert_policy ON dispute_comments;")
    op.execute("DROP POLICY IF EXISTS dispute_comments_select_policy ON dispute_comments;")
    op.execute("ALTER TABLE dispute_comments DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS disputes_update_policy ON disputes;")
    op.execute("DROP POLICY IF EXISTS disputes_insert_policy ON disputes;")
    op.execute("DROP POLICY IF EXISTS disputes_select_policy ON disputes;")
    op.execute("ALTER TABLE disputes DISABLE ROW LEVEL SECURITY;")

    # ── Drop tables ────────────────────────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_dispute_transitions_dispute_id;")
    op.execute("DROP TABLE IF EXISTS dispute_transitions;")

    op.execute("DROP INDEX IF EXISTS ix_dispute_comments_dispute_id;")
    op.execute("DROP TABLE IF EXISTS dispute_comments;")

    op.execute("DROP INDEX IF EXISTS ix_disputes_supplier_org_id;")
    op.execute("DROP INDEX IF EXISTS ix_disputes_status;")
    op.execute("DROP INDEX IF EXISTS ix_disputes_delivery_id;")
    op.execute("DROP INDEX IF EXISTS ix_disputes_order_id;")
    op.execute("DROP INDEX IF EXISTS ix_disputes_organization_id;")
    op.execute("DROP TABLE IF EXISTS disputes;")

    # ── Drop enum types ────────────────────────────────────────────────────
    op.execute("DROP TYPE IF EXISTS disputeresolutiontype;")
    op.execute("DROP TYPE IF EXISTS disputepriority;")
    op.execute("DROP TYPE IF EXISTS disputestatus;")
    op.execute("DROP TYPE IF EXISTS disputetype;")
