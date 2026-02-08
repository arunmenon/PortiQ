"""RFQ and bidding tables

Revision ID: 012
Revises: 011
Create Date: 2026-02-07

Creates: rfqs, rfq_line_items, rfq_invitations, quotes, quote_line_items, rfq_transitions
Enums: rfqstatus, rfqtransitiontype, auctiontype, quotestatus, invitationstatus
Sequence: rfq_reference_seq
RLS: buyer/supplier/admin policies per table
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Create enum types ──────────────────────────────────────────────
    op.execute("""
        CREATE TYPE rfqstatus AS ENUM (
            'DRAFT', 'PUBLISHED', 'BIDDING_OPEN', 'BIDDING_CLOSED',
            'EVALUATION', 'AWARDED', 'COMPLETED', 'CANCELLED'
        );
    """)
    op.execute("""
        CREATE TYPE rfqtransitiontype AS ENUM (
            'PUBLISH', 'OPEN_BIDDING', 'CLOSE_BIDDING',
            'START_EVALUATION', 'AWARD', 'COMPLETE', 'CANCEL'
        );
    """)
    op.execute("""
        CREATE TYPE auctiontype AS ENUM (
            'SEALED_BID'
        );
    """)
    op.execute("""
        CREATE TYPE quotestatus AS ENUM (
            'DRAFT', 'SUBMITTED', 'REVISED', 'WITHDRAWN',
            'AWARDED', 'REJECTED', 'EXPIRED'
        );
    """)
    op.execute("""
        CREATE TYPE invitationstatus AS ENUM (
            'PENDING', 'ACCEPTED', 'DECLINED', 'EXPIRED'
        );
    """)

    # ── 2. Create sequence for RFQ reference numbers ──────────────────────
    op.execute("CREATE SEQUENCE rfq_reference_seq START WITH 1000;")

    # ── 3. Create rfqs table ─────────────────────────────────────────────
    op.execute("""
        CREATE TABLE rfqs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            reference_number VARCHAR(20) NOT NULL,
            buyer_organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            status rfqstatus NOT NULL DEFAULT 'DRAFT',
            auction_type auctiontype NOT NULL DEFAULT 'SEALED_BID',
            currency VARCHAR(3) NOT NULL DEFAULT 'USD',
            vessel_id UUID REFERENCES vessels(id) ON DELETE SET NULL,
            delivery_port VARCHAR(10),
            delivery_date TIMESTAMPTZ,
            bidding_start TIMESTAMPTZ,
            bidding_deadline TIMESTAMPTZ,
            allow_partial_quotes BOOLEAN NOT NULL DEFAULT false,
            allow_quote_revision BOOLEAN NOT NULL DEFAULT true,
            require_all_line_items BOOLEAN NOT NULL DEFAULT false,
            awarded_supplier_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
            awarded_at TIMESTAMPTZ,
            cancelled_at TIMESTAMPTZ,
            cancellation_reason TEXT,
            notes TEXT,
            metadata_extra JSONB NOT NULL DEFAULT '{}',
            created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_rfqs_reference_number UNIQUE (reference_number)
        );
    """)
    op.execute("CREATE INDEX ix_rfqs_buyer_org_id ON rfqs (buyer_organization_id);")
    op.execute("CREATE INDEX ix_rfqs_status ON rfqs (status);")
    op.execute("CREATE INDEX ix_rfqs_created_by ON rfqs (created_by);")
    op.execute("CREATE INDEX ix_rfqs_vessel_id ON rfqs (vessel_id) WHERE vessel_id IS NOT NULL;")
    op.execute(
        "CREATE INDEX ix_rfqs_bidding_deadline ON rfqs (bidding_deadline)"
        " WHERE status IN ('PUBLISHED', 'BIDDING_OPEN');"
    )
    op.execute("CREATE INDEX ix_rfqs_reference_number ON rfqs (reference_number);")

    # ── 4. Create rfq_line_items table ───────────────────────────────────
    op.execute("""
        CREATE TABLE rfq_line_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            rfq_id UUID NOT NULL REFERENCES rfqs(id) ON DELETE CASCADE,
            line_number INTEGER NOT NULL,
            product_id UUID REFERENCES products(id) ON DELETE SET NULL,
            impa_code VARCHAR(10),
            description VARCHAR(500) NOT NULL,
            quantity NUMERIC(12,3) NOT NULL,
            unit_of_measure VARCHAR(20) NOT NULL,
            specifications JSONB,
            notes VARCHAR(500),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_rfq_line_items_rfq_line UNIQUE (rfq_id, line_number),
            CONSTRAINT ck_rfq_line_items_quantity_positive CHECK (quantity > 0)
        );
    """)
    op.execute("CREATE INDEX ix_rfq_line_items_rfq_id ON rfq_line_items (rfq_id);")

    # ── 5. Create rfq_invitations table ──────────────────────────────────
    op.execute("""
        CREATE TABLE rfq_invitations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            rfq_id UUID NOT NULL REFERENCES rfqs(id) ON DELETE CASCADE,
            supplier_organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            status invitationstatus NOT NULL DEFAULT 'PENDING',
            invited_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            invited_at TIMESTAMPTZ NOT NULL,
            responded_at TIMESTAMPTZ,
            decline_reason VARCHAR(500),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_rfq_invitations_rfq_supplier UNIQUE (rfq_id, supplier_organization_id)
        );
    """)
    op.execute("CREATE INDEX ix_rfq_invitations_rfq_id ON rfq_invitations (rfq_id);")
    op.execute("CREATE INDEX ix_rfq_invitations_supplier_org_id ON rfq_invitations (supplier_organization_id);")

    # ── 6. Create quotes table ───────────────────────────────────────────
    op.execute("""
        CREATE TABLE quotes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            rfq_id UUID NOT NULL REFERENCES rfqs(id) ON DELETE CASCADE,
            supplier_organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            status quotestatus NOT NULL DEFAULT 'DRAFT',
            version INTEGER NOT NULL DEFAULT 1,
            total_amount NUMERIC(15,2),
            currency VARCHAR(3) NOT NULL DEFAULT 'USD',
            valid_until TIMESTAMPTZ,
            delivery_port VARCHAR(10),
            estimated_delivery_days INTEGER,
            payment_terms VARCHAR(255),
            shipping_terms VARCHAR(255),
            warranty_terms VARCHAR(500),
            price_rank INTEGER,
            is_complete BOOLEAN NOT NULL DEFAULT false,
            notes TEXT,
            metadata_extra JSONB NOT NULL DEFAULT '{}',
            submitted_by UUID REFERENCES users(id) ON DELETE SET NULL,
            submitted_at TIMESTAMPTZ,
            withdrawn_at TIMESTAMPTZ,
            withdrawal_reason VARCHAR(500),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_quotes_rfq_supplier_version UNIQUE (rfq_id, supplier_organization_id, version),
            CONSTRAINT ck_quotes_total_amount_non_negative CHECK (total_amount IS NULL OR total_amount >= 0)
        );
    """)
    op.execute("CREATE INDEX ix_quotes_rfq_id ON quotes (rfq_id);")
    op.execute("CREATE INDEX ix_quotes_supplier_org_id ON quotes (supplier_organization_id);")
    op.execute("CREATE INDEX ix_quotes_status ON quotes (status);")

    # ── 7. Add awarded_quote_id FK to rfqs (quotes table now exists) ─────
    op.execute("""
        ALTER TABLE rfqs
          ADD COLUMN awarded_quote_id UUID REFERENCES quotes(id) ON DELETE SET NULL;
    """)

    # ── 8. Create quote_line_items table ─────────────────────────────────
    op.execute("""
        CREATE TABLE quote_line_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            quote_id UUID NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
            rfq_line_item_id UUID NOT NULL REFERENCES rfq_line_items(id) ON DELETE CASCADE,
            unit_price NUMERIC(15,4) NOT NULL,
            quantity NUMERIC(12,3) NOT NULL,
            total_price NUMERIC(15,2) NOT NULL,
            lead_time_days INTEGER,
            notes VARCHAR(500),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_quote_line_items_quote_rfq_line UNIQUE (quote_id, rfq_line_item_id),
            CONSTRAINT ck_quote_line_items_unit_price_non_negative CHECK (unit_price >= 0),
            CONSTRAINT ck_quote_line_items_quantity_positive CHECK (quantity > 0),
            CONSTRAINT ck_quote_line_items_total_price_non_negative CHECK (total_price >= 0)
        );
    """)
    op.execute("CREATE INDEX ix_quote_line_items_quote_id ON quote_line_items (quote_id);")

    # ── 9. Create rfq_transitions table ──────────────────────────────────
    op.execute("""
        CREATE TABLE rfq_transitions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            rfq_id UUID NOT NULL REFERENCES rfqs(id) ON DELETE CASCADE,
            from_status rfqstatus NOT NULL,
            to_status rfqstatus NOT NULL,
            transition_type rfqtransitiontype NOT NULL,
            triggered_by UUID REFERENCES users(id) ON DELETE SET NULL,
            trigger_source VARCHAR(20) NOT NULL DEFAULT 'user',
            reason TEXT,
            metadata_extra JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX ix_rfq_transitions_rfq_id ON rfq_transitions (rfq_id);")
    op.execute("CREATE INDEX ix_rfq_transitions_to_status ON rfq_transitions (to_status);")

    # ── 10. RLS policies ─────────────────────────────────────────────────

    # 10a. rfqs: admin OR buyer_org OR invited supplier can SELECT;
    #       admin OR buyer_org can INSERT/UPDATE/DELETE
    op.execute("ALTER TABLE rfqs ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE rfqs FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY rfqs_select_policy ON rfqs FOR SELECT
          USING (
            is_admin_bypass_active()
            OR buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
            OR EXISTS (
              SELECT 1 FROM rfq_invitations ri
              WHERE ri.rfq_id = rfqs.id
                AND ri.supplier_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY rfqs_insert_policy ON rfqs FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY rfqs_update_policy ON rfqs FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY rfqs_delete_policy ON rfqs FOR DELETE
          USING (
            is_admin_bypass_active()
            OR buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)

    # 10b. rfq_line_items: via rfqs ownership
    op.execute("ALTER TABLE rfq_line_items ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE rfq_line_items FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY rfq_line_items_select_policy ON rfq_line_items FOR SELECT
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM rfqs r
              WHERE r.id = rfq_line_items.rfq_id
                AND (
                  r.buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
                  OR EXISTS (
                    SELECT 1 FROM rfq_invitations ri
                    WHERE ri.rfq_id = r.id
                      AND ri.supplier_organization_id::text = get_tenant_setting('app.current_organization_id')
                  )
                )
            )
          );
    """)
    op.execute("""
        CREATE POLICY rfq_line_items_insert_policy ON rfq_line_items FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM rfqs r
              WHERE r.id = rfq_line_items.rfq_id
                AND r.buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY rfq_line_items_update_policy ON rfq_line_items FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM rfqs r
              WHERE r.id = rfq_line_items.rfq_id
                AND r.buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM rfqs r
              WHERE r.id = rfq_line_items.rfq_id
                AND r.buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY rfq_line_items_delete_policy ON rfq_line_items FOR DELETE
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM rfqs r
              WHERE r.id = rfq_line_items.rfq_id
                AND r.buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)

    # 10c. rfq_invitations: admin OR supplier_org OR buyer_org can SELECT;
    #       buyer_org can insert; supplier can update own
    op.execute("ALTER TABLE rfq_invitations ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE rfq_invitations FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY rfq_invitations_select_policy ON rfq_invitations FOR SELECT
          USING (
            is_admin_bypass_active()
            OR supplier_organization_id::text = get_tenant_setting('app.current_organization_id')
            OR EXISTS (
              SELECT 1 FROM rfqs r
              WHERE r.id = rfq_invitations.rfq_id
                AND r.buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY rfq_invitations_insert_policy ON rfq_invitations FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM rfqs r
              WHERE r.id = rfq_invitations.rfq_id
                AND r.buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY rfq_invitations_update_policy ON rfq_invitations FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR supplier_organization_id::text = get_tenant_setting('app.current_organization_id')
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR supplier_organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)

    # 10d. quotes: admin OR supplier_org (own) OR buyer_org (after BIDDING_CLOSED) can SELECT;
    #       admin OR supplier_org can INSERT/UPDATE/DELETE
    op.execute("ALTER TABLE quotes ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE quotes FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY quotes_select_policy ON quotes FOR SELECT
          USING (
            is_admin_bypass_active()
            OR supplier_organization_id::text = get_tenant_setting('app.current_organization_id')
            OR EXISTS (
              SELECT 1 FROM rfqs r
              WHERE r.id = quotes.rfq_id
                AND r.buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
                AND r.status IN ('BIDDING_CLOSED', 'EVALUATION', 'AWARDED', 'COMPLETED')
            )
          );
    """)
    op.execute("""
        CREATE POLICY quotes_insert_policy ON quotes FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR supplier_organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY quotes_update_policy ON quotes FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR supplier_organization_id::text = get_tenant_setting('app.current_organization_id')
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR supplier_organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY quotes_delete_policy ON quotes FOR DELETE
          USING (
            is_admin_bypass_active()
            OR supplier_organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)

    # 10e. quote_line_items: via quotes ownership
    op.execute("ALTER TABLE quote_line_items ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE quote_line_items FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY quote_line_items_select_policy ON quote_line_items FOR SELECT
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM quotes q
              WHERE q.id = quote_line_items.quote_id
                AND (
                  q.supplier_organization_id::text = get_tenant_setting('app.current_organization_id')
                  OR EXISTS (
                    SELECT 1 FROM rfqs r
                    WHERE r.id = q.rfq_id
                      AND r.buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
                      AND r.status IN ('BIDDING_CLOSED', 'EVALUATION', 'AWARDED', 'COMPLETED')
                  )
                )
            )
          );
    """)
    op.execute("""
        CREATE POLICY quote_line_items_insert_policy ON quote_line_items FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM quotes q
              WHERE q.id = quote_line_items.quote_id
                AND q.supplier_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY quote_line_items_update_policy ON quote_line_items FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM quotes q
              WHERE q.id = quote_line_items.quote_id
                AND q.supplier_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM quotes q
              WHERE q.id = quote_line_items.quote_id
                AND q.supplier_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY quote_line_items_delete_policy ON quote_line_items FOR DELETE
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM quotes q
              WHERE q.id = quote_line_items.quote_id
                AND q.supplier_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)

    # 10f. rfq_transitions: via rfqs ownership (read); buyer_org can insert
    op.execute("ALTER TABLE rfq_transitions ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE rfq_transitions FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY rfq_transitions_select_policy ON rfq_transitions FOR SELECT
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM rfqs r
              WHERE r.id = rfq_transitions.rfq_id
                AND (
                  r.buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
                  OR EXISTS (
                    SELECT 1 FROM rfq_invitations ri
                    WHERE ri.rfq_id = r.id
                      AND ri.supplier_organization_id::text = get_tenant_setting('app.current_organization_id')
                  )
                )
            )
          );
    """)
    op.execute("""
        CREATE POLICY rfq_transitions_insert_policy ON rfq_transitions FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM rfqs r
              WHERE r.id = rfq_transitions.rfq_id
                AND r.buyer_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)


def downgrade() -> None:
    # ── Reverse 10f: Drop rfq_transitions RLS ────────────────────────────
    op.execute("DROP POLICY IF EXISTS rfq_transitions_insert_policy ON rfq_transitions;")
    op.execute("DROP POLICY IF EXISTS rfq_transitions_select_policy ON rfq_transitions;")
    op.execute("ALTER TABLE rfq_transitions DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 10e: Drop quote_line_items RLS ───────────────────────────
    op.execute("DROP POLICY IF EXISTS quote_line_items_delete_policy ON quote_line_items;")
    op.execute("DROP POLICY IF EXISTS quote_line_items_update_policy ON quote_line_items;")
    op.execute("DROP POLICY IF EXISTS quote_line_items_insert_policy ON quote_line_items;")
    op.execute("DROP POLICY IF EXISTS quote_line_items_select_policy ON quote_line_items;")
    op.execute("ALTER TABLE quote_line_items DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 10d: Drop quotes RLS ─────────────────────────────────────
    op.execute("DROP POLICY IF EXISTS quotes_delete_policy ON quotes;")
    op.execute("DROP POLICY IF EXISTS quotes_update_policy ON quotes;")
    op.execute("DROP POLICY IF EXISTS quotes_insert_policy ON quotes;")
    op.execute("DROP POLICY IF EXISTS quotes_select_policy ON quotes;")
    op.execute("ALTER TABLE quotes DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 10c: Drop rfq_invitations RLS ────────────────────────────
    op.execute("DROP POLICY IF EXISTS rfq_invitations_update_policy ON rfq_invitations;")
    op.execute("DROP POLICY IF EXISTS rfq_invitations_insert_policy ON rfq_invitations;")
    op.execute("DROP POLICY IF EXISTS rfq_invitations_select_policy ON rfq_invitations;")
    op.execute("ALTER TABLE rfq_invitations DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 10b: Drop rfq_line_items RLS ─────────────────────────────
    op.execute("DROP POLICY IF EXISTS rfq_line_items_delete_policy ON rfq_line_items;")
    op.execute("DROP POLICY IF EXISTS rfq_line_items_update_policy ON rfq_line_items;")
    op.execute("DROP POLICY IF EXISTS rfq_line_items_insert_policy ON rfq_line_items;")
    op.execute("DROP POLICY IF EXISTS rfq_line_items_select_policy ON rfq_line_items;")
    op.execute("ALTER TABLE rfq_line_items DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 10a: Drop rfqs RLS ───────────────────────────────────────
    op.execute("DROP POLICY IF EXISTS rfqs_delete_policy ON rfqs;")
    op.execute("DROP POLICY IF EXISTS rfqs_update_policy ON rfqs;")
    op.execute("DROP POLICY IF EXISTS rfqs_insert_policy ON rfqs;")
    op.execute("DROP POLICY IF EXISTS rfqs_select_policy ON rfqs;")
    op.execute("ALTER TABLE rfqs DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 9: Drop rfq_transitions ──────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_rfq_transitions_to_status;")
    op.execute("DROP INDEX IF EXISTS ix_rfq_transitions_rfq_id;")
    op.execute("DROP TABLE IF EXISTS rfq_transitions;")

    # ── Reverse 8: Drop quote_line_items ─────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_quote_line_items_quote_id;")
    op.execute("DROP TABLE IF EXISTS quote_line_items;")

    # ── Reverse 7: Drop awarded_quote_id from rfqs ──────────────────────
    op.execute("ALTER TABLE rfqs DROP COLUMN IF EXISTS awarded_quote_id;")

    # ── Reverse 6: Drop quotes ───────────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_quotes_status;")
    op.execute("DROP INDEX IF EXISTS ix_quotes_supplier_org_id;")
    op.execute("DROP INDEX IF EXISTS ix_quotes_rfq_id;")
    op.execute("DROP TABLE IF EXISTS quotes;")

    # ── Reverse 5: Drop rfq_invitations ──────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_rfq_invitations_supplier_org_id;")
    op.execute("DROP INDEX IF EXISTS ix_rfq_invitations_rfq_id;")
    op.execute("DROP TABLE IF EXISTS rfq_invitations;")

    # ── Reverse 4: Drop rfq_line_items ───────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_rfq_line_items_rfq_id;")
    op.execute("DROP TABLE IF EXISTS rfq_line_items;")

    # ── Reverse 3: Drop rfqs ────────────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_rfqs_reference_number;")
    op.execute("DROP INDEX IF EXISTS ix_rfqs_bidding_deadline;")
    op.execute("DROP INDEX IF EXISTS ix_rfqs_vessel_id;")
    op.execute("DROP INDEX IF EXISTS ix_rfqs_created_by;")
    op.execute("DROP INDEX IF EXISTS ix_rfqs_status;")
    op.execute("DROP INDEX IF EXISTS ix_rfqs_buyer_org_id;")
    op.execute("DROP TABLE IF EXISTS rfqs;")

    # ── Reverse 2: Drop sequence ─────────────────────────────────────────
    op.execute("DROP SEQUENCE IF EXISTS rfq_reference_seq;")

    # ── Reverse 1: Drop enum types ───────────────────────────────────────
    op.execute("DROP TYPE IF EXISTS invitationstatus;")
    op.execute("DROP TYPE IF EXISTS quotestatus;")
    op.execute("DROP TYPE IF EXISTS auctiontype;")
    op.execute("DROP TYPE IF EXISTS rfqtransitiontype;")
    op.execute("DROP TYPE IF EXISTS rfqstatus;")
