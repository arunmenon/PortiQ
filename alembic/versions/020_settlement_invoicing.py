"""Settlement and invoicing tables

Revision ID: 020
Revises: 019
Create Date: 2026-02-14

Creates: settlement_periods, invoices, invoice_line_items
Enums: invoicestatus, settlementperiodtype, settlementperiodstatus
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "020"
down_revision: str | None = "019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Create enum types ──────────────────────────────────────────────
    op.execute("""
        CREATE TYPE invoicestatus AS ENUM (
            'DRAFT', 'READY', 'SENT', 'ACKNOWLEDGED',
            'DISPUTED', 'PAID', 'CANCELLED', 'CREDIT_NOTE'
        );
    """)
    op.execute("""
        CREATE TYPE settlementperiodtype AS ENUM (
            'PORT_CALL', 'WEEKLY', 'MONTHLY'
        );
    """)
    op.execute("""
        CREATE TYPE settlementperiodstatus AS ENUM (
            'OPEN', 'CLOSED', 'RECONCILED'
        );
    """)

    # ── 2. Create settlement_periods table ────────────────────────────────
    op.execute("""
        CREATE TABLE settlement_periods (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            period_type settlementperiodtype NOT NULL,
            period_start DATE NOT NULL,
            period_end DATE NOT NULL,
            period_label VARCHAR(100),
            total_invoices INTEGER NOT NULL DEFAULT 0,
            total_amount NUMERIC(15, 2) NOT NULL DEFAULT 0,
            total_credits NUMERIC(15, 2) NOT NULL DEFAULT 0,
            net_amount NUMERIC(15, 2) NOT NULL DEFAULT 0,
            status settlementperiodstatus NOT NULL DEFAULT 'OPEN',
            closed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX ix_settlement_periods_organization_id ON settlement_periods (organization_id);")
    op.execute("CREATE INDEX ix_settlement_periods_status ON settlement_periods (status);")

    # ── 3. Create invoices table ──────────────────────────────────────────
    op.execute("""
        CREATE TABLE invoices (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            invoice_number VARCHAR(50) NOT NULL,
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            vendor_order_id UUID NOT NULL REFERENCES vendor_orders(id) ON DELETE CASCADE,
            delivery_id UUID REFERENCES deliveries(id) ON DELETE SET NULL,
            settlement_period_id UUID REFERENCES settlement_periods(id) ON DELETE SET NULL,
            buyer_org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            supplier_org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            status invoicestatus NOT NULL DEFAULT 'DRAFT',
            subtotal NUMERIC(15, 2) NOT NULL,
            tax_rate NUMERIC(5, 2) NOT NULL DEFAULT 0,
            tax_amount NUMERIC(15, 2) NOT NULL DEFAULT 0,
            discount_amount NUMERIC(15, 2) NOT NULL DEFAULT 0,
            credit_adjustment NUMERIC(15, 2) NOT NULL DEFAULT 0,
            total_amount NUMERIC(15, 2) NOT NULL,
            currency VARCHAR(3) NOT NULL DEFAULT 'USD',
            buyer_po_number VARCHAR(100),
            supplier_invoice_ref VARCHAR(100),
            invoice_date DATE NOT NULL,
            due_date DATE,
            sent_at TIMESTAMPTZ,
            acknowledged_at TIMESTAMPTZ,
            paid_at TIMESTAMPTZ,
            paid_reference VARCHAR(200),
            notes TEXT,
            internal_notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_invoices_invoice_number UNIQUE (invoice_number)
        );
    """)
    op.execute("CREATE INDEX ix_invoices_organization_id ON invoices (organization_id);")
    op.execute("CREATE INDEX ix_invoices_order_id ON invoices (order_id);")
    op.execute("CREATE INDEX ix_invoices_buyer_org_id ON invoices (buyer_org_id);")
    op.execute("CREATE INDEX ix_invoices_supplier_org_id ON invoices (supplier_org_id);")
    op.execute("CREATE INDEX ix_invoices_status ON invoices (status);")
    op.execute(
        "CREATE INDEX ix_invoices_settlement_period_id ON invoices (settlement_period_id)"
        " WHERE settlement_period_id IS NOT NULL;"
    )

    # ── 4. Create invoice_line_items table ────────────────────────────────
    op.execute("""
        CREATE TABLE invoice_line_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
            order_line_item_id UUID NOT NULL REFERENCES order_line_items(id) ON DELETE CASCADE,
            delivery_item_id UUID REFERENCES delivery_items(id) ON DELETE SET NULL,
            dispute_id UUID REFERENCES disputes(id) ON DELETE SET NULL,
            impa_code VARCHAR(6),
            product_name VARCHAR(255) NOT NULL,
            description TEXT,
            quantity_ordered INTEGER NOT NULL,
            quantity_delivered INTEGER NOT NULL,
            quantity_accepted INTEGER NOT NULL,
            quantity_rejected INTEGER NOT NULL DEFAULT 0,
            unit_price NUMERIC(12, 2) NOT NULL,
            line_subtotal NUMERIC(15, 2) NOT NULL,
            credit_amount NUMERIC(15, 2) NOT NULL DEFAULT 0,
            line_total NUMERIC(15, 2) NOT NULL,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX ix_invoice_line_items_invoice_id ON invoice_line_items (invoice_id);")
    op.execute("CREATE INDEX ix_invoice_line_items_order_line_item_id ON invoice_line_items (order_line_item_id);")

    # ── 5. RLS policies ──────────────────────────────────────────────────
    # settlement_periods: admin OR organization_id matches tenant
    op.execute("ALTER TABLE settlement_periods ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE settlement_periods FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY settlement_periods_select_policy ON settlement_periods FOR SELECT
          USING (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY settlement_periods_insert_policy ON settlement_periods FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY settlement_periods_update_policy ON settlement_periods FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)

    # invoices: admin OR buyer_org OR supplier_org can access
    op.execute("ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE invoices FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY invoices_select_policy ON invoices FOR SELECT
          USING (
            is_admin_bypass_active()
            OR buyer_org_id::text = get_tenant_setting('app.current_organization_id')
            OR supplier_org_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY invoices_insert_policy ON invoices FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY invoices_update_policy ON invoices FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR buyer_org_id::text = get_tenant_setting('app.current_organization_id')
            OR supplier_org_id::text = get_tenant_setting('app.current_organization_id')
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR buyer_org_id::text = get_tenant_setting('app.current_organization_id')
            OR supplier_org_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)

    # invoice_line_items: via invoices ownership
    op.execute("ALTER TABLE invoice_line_items ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE invoice_line_items FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY invoice_line_items_select_policy ON invoice_line_items FOR SELECT
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM invoices inv
              WHERE inv.id = invoice_line_items.invoice_id
                AND (
                  inv.buyer_org_id::text = get_tenant_setting('app.current_organization_id')
                  OR inv.supplier_org_id::text = get_tenant_setting('app.current_organization_id')
                )
            )
          );
    """)
    op.execute("""
        CREATE POLICY invoice_line_items_insert_policy ON invoice_line_items FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM invoices inv
              WHERE inv.id = invoice_line_items.invoice_id
                AND inv.organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY invoice_line_items_update_policy ON invoice_line_items FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM invoices inv
              WHERE inv.id = invoice_line_items.invoice_id
                AND (
                  inv.buyer_org_id::text = get_tenant_setting('app.current_organization_id')
                  OR inv.supplier_org_id::text = get_tenant_setting('app.current_organization_id')
                )
            )
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM invoices inv
              WHERE inv.id = invoice_line_items.invoice_id
                AND (
                  inv.buyer_org_id::text = get_tenant_setting('app.current_organization_id')
                  OR inv.supplier_org_id::text = get_tenant_setting('app.current_organization_id')
                )
            )
          );
    """)


def downgrade() -> None:
    # ── Reverse RLS ────────────────────────────────────────────────────────
    op.execute("DROP POLICY IF EXISTS invoice_line_items_update_policy ON invoice_line_items;")
    op.execute("DROP POLICY IF EXISTS invoice_line_items_insert_policy ON invoice_line_items;")
    op.execute("DROP POLICY IF EXISTS invoice_line_items_select_policy ON invoice_line_items;")
    op.execute("ALTER TABLE invoice_line_items DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS invoices_update_policy ON invoices;")
    op.execute("DROP POLICY IF EXISTS invoices_insert_policy ON invoices;")
    op.execute("DROP POLICY IF EXISTS invoices_select_policy ON invoices;")
    op.execute("ALTER TABLE invoices DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS settlement_periods_update_policy ON settlement_periods;")
    op.execute("DROP POLICY IF EXISTS settlement_periods_insert_policy ON settlement_periods;")
    op.execute("DROP POLICY IF EXISTS settlement_periods_select_policy ON settlement_periods;")
    op.execute("ALTER TABLE settlement_periods DISABLE ROW LEVEL SECURITY;")

    # ── Drop tables in reverse order ───────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_invoice_line_items_order_line_item_id;")
    op.execute("DROP INDEX IF EXISTS ix_invoice_line_items_invoice_id;")
    op.execute("DROP TABLE IF EXISTS invoice_line_items;")

    op.execute("DROP INDEX IF EXISTS ix_invoices_settlement_period_id;")
    op.execute("DROP INDEX IF EXISTS ix_invoices_status;")
    op.execute("DROP INDEX IF EXISTS ix_invoices_supplier_org_id;")
    op.execute("DROP INDEX IF EXISTS ix_invoices_buyer_org_id;")
    op.execute("DROP INDEX IF EXISTS ix_invoices_order_id;")
    op.execute("DROP INDEX IF EXISTS ix_invoices_organization_id;")
    op.execute("DROP TABLE IF EXISTS invoices;")

    op.execute("DROP INDEX IF EXISTS ix_settlement_periods_status;")
    op.execute("DROP INDEX IF EXISTS ix_settlement_periods_organization_id;")
    op.execute("DROP TABLE IF EXISTS settlement_periods;")

    # ── Drop enum types ────────────────────────────────────────────────────
    op.execute("DROP TYPE IF EXISTS settlementperiodstatus;")
    op.execute("DROP TYPE IF EXISTS settlementperiodtype;")
    op.execute("DROP TYPE IF EXISTS invoicestatus;")
