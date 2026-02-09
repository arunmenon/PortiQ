"""TCO engine tables

Revision ID: 015
Revises: 014
Create Date: 2026-02-08

Creates: tco_configurations, tco_calculations, tco_audit_trail
Enums: tcocalculationstatus, tcotemplatetype
RLS: admin bypass + organization-scoped access via buyer_organization_id
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "015"
down_revision: str | None = "014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Create enum types ──────────────────────────────────────────────
    op.execute("""
        CREATE TYPE tcocalculationstatus AS ENUM (
            'PENDING', 'CALCULATING', 'COMPLETED', 'FAILED', 'STALE'
        );
    """)
    op.execute("""
        CREATE TYPE tcotemplatetype AS ENUM (
            'COMMODITY', 'TECHNICAL', 'URGENT', 'STRATEGIC',
            'QUALITY_CRITICAL', 'CUSTOM'
        );
    """)

    # ── 2. Create tco_configurations table ────────────────────────────────
    op.execute("""
        CREATE TABLE tco_configurations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            template_type tcotemplatetype NOT NULL DEFAULT 'COMMODITY',
            weight_unit_price NUMERIC(5,4) NOT NULL DEFAULT 0.4000,
            weight_shipping NUMERIC(5,4) NOT NULL DEFAULT 0.1500,
            weight_lead_time NUMERIC(5,4) NOT NULL DEFAULT 0.1500,
            weight_quality NUMERIC(5,4) NOT NULL DEFAULT 0.1500,
            weight_payment_terms NUMERIC(5,4) NOT NULL DEFAULT 0.1000,
            weight_supplier_rating NUMERIC(5,4) NOT NULL DEFAULT 0.0500,
            is_default BOOLEAN NOT NULL DEFAULT false,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_tco_configurations_org_name UNIQUE (organization_id, name),
            CONSTRAINT ck_tco_configurations_weights_sum CHECK (
                ABS(
                    weight_unit_price + weight_shipping + weight_lead_time
                    + weight_quality + weight_payment_terms + weight_supplier_rating
                    - 1.0
                ) < 0.001
            )
        );
    """)
    op.execute(
        "CREATE INDEX ix_tco_configurations_organization_id ON tco_configurations (organization_id);"
    )
    op.execute(
        "CREATE INDEX ix_tco_configurations_is_default ON tco_configurations (is_default);"
    )

    # ── 3. Create tco_calculations table ──────────────────────────────────
    op.execute("""
        CREATE TABLE tco_calculations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            rfq_id UUID NOT NULL REFERENCES rfqs(id) ON DELETE CASCADE,
            configuration_id UUID REFERENCES tco_configurations(id) ON DELETE SET NULL,
            weights_snapshot JSONB NOT NULL,
            status tcocalculationstatus NOT NULL DEFAULT 'PENDING',
            results JSONB,
            split_order_result JSONB,
            base_currency VARCHAR(3) NOT NULL DEFAULT 'USD',
            exchange_rates JSONB,
            missing_data_strategy VARCHAR(20),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute(
        "CREATE INDEX ix_tco_calculations_rfq_id ON tco_calculations (rfq_id);"
    )
    op.execute(
        "CREATE INDEX ix_tco_calculations_configuration_id ON tco_calculations (configuration_id);"
    )
    op.execute(
        "CREATE INDEX ix_tco_calculations_status ON tco_calculations (status);"
    )

    # ── 4. Create tco_audit_trail table ───────────────────────────────────
    op.execute("""
        CREATE TABLE tco_audit_trail (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            calculation_id UUID NOT NULL REFERENCES tco_calculations(id) ON DELETE CASCADE,
            rfq_id UUID NOT NULL REFERENCES rfqs(id) ON DELETE CASCADE,
            action VARCHAR(50) NOT NULL,
            actor_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            actor_organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            details JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute(
        "CREATE INDEX ix_tco_audit_trail_calculation_id ON tco_audit_trail (calculation_id);"
    )
    op.execute(
        "CREATE INDEX ix_tco_audit_trail_rfq_id ON tco_audit_trail (rfq_id);"
    )
    op.execute(
        "CREATE INDEX ix_tco_audit_trail_actor_id ON tco_audit_trail (actor_id);"
    )
    op.execute(
        "CREATE INDEX ix_tco_audit_trail_created_at ON tco_audit_trail (created_at);"
    )

    # ── 5. RLS policies ──────────────────────────────────────────────────

    # 5a. tco_configurations: org-scoped via organization_id
    op.execute("ALTER TABLE tco_configurations ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tco_configurations FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY tco_configurations_select_policy ON tco_configurations FOR SELECT
          USING (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY tco_configurations_insert_policy ON tco_configurations FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY tco_configurations_update_policy ON tco_configurations FOR UPDATE
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
        CREATE POLICY tco_configurations_delete_policy ON tco_configurations FOR DELETE
          USING (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)

    # 5b. tco_calculations: scoped via rfqs.buyer_organization_id
    op.execute("ALTER TABLE tco_calculations ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tco_calculations FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY tco_calculations_select_policy ON tco_calculations FOR SELECT
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM rfqs r
              WHERE r.id = tco_calculations.rfq_id
                AND r.buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY tco_calculations_insert_policy ON tco_calculations FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM rfqs r
              WHERE r.id = tco_calculations.rfq_id
                AND r.buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY tco_calculations_update_policy ON tco_calculations FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM rfqs r
              WHERE r.id = tco_calculations.rfq_id
                AND r.buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM rfqs r
              WHERE r.id = tco_calculations.rfq_id
                AND r.buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY tco_calculations_delete_policy ON tco_calculations FOR DELETE
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM rfqs r
              WHERE r.id = tco_calculations.rfq_id
                AND r.buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)

    # 5c. tco_audit_trail: scoped by actor_organization_id or via calc→rfq join
    op.execute("ALTER TABLE tco_audit_trail ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tco_audit_trail FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY tco_audit_trail_select_policy ON tco_audit_trail FOR SELECT
          USING (
            is_admin_bypass_active()
            OR actor_organization_id::text = get_tenant_setting('app.current_organization_id')
            OR EXISTS (
              SELECT 1 FROM tco_calculations tc
              JOIN rfqs r ON r.id = tc.rfq_id
              WHERE tc.id = tco_audit_trail.calculation_id
                AND r.buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY tco_audit_trail_insert_policy ON tco_audit_trail FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR actor_organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY tco_audit_trail_update_policy ON tco_audit_trail FOR UPDATE
          USING (
            is_admin_bypass_active()
          )
          WITH CHECK (
            is_admin_bypass_active()
          );
    """)
    op.execute("""
        CREATE POLICY tco_audit_trail_delete_policy ON tco_audit_trail FOR DELETE
          USING (
            is_admin_bypass_active()
          );
    """)


def downgrade() -> None:
    # ── Reverse 5c: Drop tco_audit_trail RLS ──────────────────────────────
    op.execute("DROP POLICY IF EXISTS tco_audit_trail_delete_policy ON tco_audit_trail;")
    op.execute("DROP POLICY IF EXISTS tco_audit_trail_update_policy ON tco_audit_trail;")
    op.execute("DROP POLICY IF EXISTS tco_audit_trail_insert_policy ON tco_audit_trail;")
    op.execute("DROP POLICY IF EXISTS tco_audit_trail_select_policy ON tco_audit_trail;")
    op.execute("ALTER TABLE tco_audit_trail DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 5b: Drop tco_calculations RLS ─────────────────────────────
    op.execute("DROP POLICY IF EXISTS tco_calculations_delete_policy ON tco_calculations;")
    op.execute("DROP POLICY IF EXISTS tco_calculations_update_policy ON tco_calculations;")
    op.execute("DROP POLICY IF EXISTS tco_calculations_insert_policy ON tco_calculations;")
    op.execute("DROP POLICY IF EXISTS tco_calculations_select_policy ON tco_calculations;")
    op.execute("ALTER TABLE tco_calculations DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 5a: Drop tco_configurations RLS ──────────────────────────
    op.execute("DROP POLICY IF EXISTS tco_configurations_delete_policy ON tco_configurations;")
    op.execute("DROP POLICY IF EXISTS tco_configurations_update_policy ON tco_configurations;")
    op.execute("DROP POLICY IF EXISTS tco_configurations_insert_policy ON tco_configurations;")
    op.execute("DROP POLICY IF EXISTS tco_configurations_select_policy ON tco_configurations;")
    op.execute("ALTER TABLE tco_configurations DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 4: Drop tco_audit_trail ───────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_tco_audit_trail_created_at;")
    op.execute("DROP INDEX IF EXISTS ix_tco_audit_trail_actor_id;")
    op.execute("DROP INDEX IF EXISTS ix_tco_audit_trail_rfq_id;")
    op.execute("DROP INDEX IF EXISTS ix_tco_audit_trail_calculation_id;")
    op.execute("DROP TABLE IF EXISTS tco_audit_trail;")

    # ── Reverse 3: Drop tco_calculations ──────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_tco_calculations_status;")
    op.execute("DROP INDEX IF EXISTS ix_tco_calculations_configuration_id;")
    op.execute("DROP INDEX IF EXISTS ix_tco_calculations_rfq_id;")
    op.execute("DROP TABLE IF EXISTS tco_calculations;")

    # ── Reverse 2: Drop tco_configurations ────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_tco_configurations_is_default;")
    op.execute("DROP INDEX IF EXISTS ix_tco_configurations_organization_id;")
    op.execute("DROP TABLE IF EXISTS tco_configurations;")

    # ── Reverse 1: Drop enum types ────────────────────────────────────────
    op.execute("DROP TYPE IF EXISTS tcotemplatetype;")
    op.execute("DROP TYPE IF EXISTS tcocalculationstatus;")
