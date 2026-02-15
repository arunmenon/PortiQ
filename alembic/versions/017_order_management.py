"""Order management tables

Revision ID: 017
Revises: 016
Create Date: 2026-02-14

Creates: orders, vendor_orders, order_line_items, fulfillments, fulfillment_items
Enums: orderstatus, vendororderstatus, fulfillmentstatus, fulfillmentlineitemstatus, deliverytype
Sequences: order_reference_seq
Trigger: fulfillment_status_rollup_trigger
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "017"
down_revision: str | None = "016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Create enum types ──────────────────────────────────────────────
    op.execute("""
        CREATE TYPE orderstatus AS ENUM (
            'PENDING_PAYMENT', 'CONFIRMED', 'PROCESSING',
            'PARTIALLY_FULFILLED', 'FULFILLED', 'COMPLETED',
            'CANCELLED', 'DISPUTED'
        );
    """)
    op.execute("""
        CREATE TYPE vendororderstatus AS ENUM (
            'PENDING_CONFIRMATION', 'CONFIRMED', 'PREPARING',
            'READY_FOR_PICKUP', 'IN_TRANSIT', 'DELIVERED',
            'FULFILLED', 'CANCELLED', 'DISPUTED'
        );
    """)
    op.execute("""
        CREATE TYPE fulfillmentstatus AS ENUM (
            'PENDING', 'PICKING', 'PACKED', 'SHIPPED',
            'IN_TRANSIT', 'OUT_FOR_DELIVERY', 'DELIVERED',
            'ACCEPTED', 'REJECTED', 'PARTIALLY_ACCEPTED'
        );
    """)
    op.execute("""
        CREATE TYPE fulfillmentlineitemstatus AS ENUM (
            'PENDING', 'ALLOCATED', 'PICKED', 'PACKED',
            'SHIPPED', 'DELIVERED', 'ACCEPTED', 'REJECTED',
            'BACKORDERED', 'CANCELLED'
        );
    """)
    op.execute("""
        CREATE TYPE deliverytype AS ENUM (
            'ALONGSIDE', 'WAREHOUSE', 'AGENT', 'ANCHORAGE'
        );
    """)

    # ── 2. Create sequence for order reference numbers ─────────────────────
    op.execute("CREATE SEQUENCE order_reference_seq START WITH 1000;")

    # ── 3. Create orders table ─────────────────────────────────────────────
    op.execute("""
        CREATE TABLE orders (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            order_number VARCHAR(50) NOT NULL,
            rfq_id UUID REFERENCES rfqs(id) ON DELETE SET NULL,
            buyer_org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            status orderstatus NOT NULL DEFAULT 'PENDING_PAYMENT',
            total_amount NUMERIC(15, 2) NOT NULL,
            currency VARCHAR(3) NOT NULL DEFAULT 'USD',
            delivery_port VARCHAR(10),
            vessel_imo VARCHAR(10),
            vessel_name VARCHAR(100),
            requested_delivery_date DATE,
            payment_status VARCHAR(20),
            payment_method VARCHAR(30),
            payment_reference VARCHAR(100),
            metadata_extra JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_orders_order_number UNIQUE (order_number)
        );
    """)
    op.execute("CREATE INDEX ix_orders_buyer_org_id ON orders (buyer_org_id);")
    op.execute("CREATE INDEX ix_orders_status ON orders (status);")
    op.execute("CREATE INDEX ix_orders_rfq_id ON orders (rfq_id) WHERE rfq_id IS NOT NULL;")
    op.execute("CREATE INDEX ix_orders_order_number ON orders (order_number);")

    # ── 4. Create vendor_orders table ──────────────────────────────────────
    op.execute("""
        CREATE TABLE vendor_orders (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            vendor_order_number VARCHAR(50) NOT NULL,
            order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            supplier_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            status vendororderstatus NOT NULL DEFAULT 'PENDING_CONFIRMATION',
            amount NUMERIC(15, 2) NOT NULL,
            commission_rate NUMERIC(5, 2),
            commission_amount NUMERIC(15, 2),
            confirmed_at TIMESTAMPTZ,
            estimated_ready_date DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_vendor_orders_number UNIQUE (vendor_order_number)
        );
    """)
    op.execute("CREATE INDEX ix_vendor_orders_order_id ON vendor_orders (order_id);")
    op.execute("CREATE INDEX ix_vendor_orders_supplier_id ON vendor_orders (supplier_id);")
    op.execute("CREATE INDEX ix_vendor_orders_status ON vendor_orders (status);")

    # ── 5. Create order_line_items table ───────────────────────────────────
    op.execute("""
        CREATE TABLE order_line_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            vendor_order_id UUID NOT NULL REFERENCES vendor_orders(id) ON DELETE CASCADE,
            product_id UUID REFERENCES products(id) ON DELETE SET NULL,
            impa_code CHAR(6) NOT NULL,
            product_name VARCHAR(255) NOT NULL,
            quantity_ordered INTEGER NOT NULL,
            quantity_fulfilled INTEGER NOT NULL DEFAULT 0,
            quantity_accepted INTEGER NOT NULL DEFAULT 0,
            unit_price NUMERIC(12, 2) NOT NULL,
            line_total NUMERIC(15, 2) NOT NULL,
            status fulfillmentlineitemstatus NOT NULL DEFAULT 'PENDING',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_order_line_items_quantity_positive CHECK (quantity_ordered > 0),
            CONSTRAINT ck_order_line_items_unit_price_non_negative CHECK (unit_price >= 0)
        );
    """)
    op.execute("CREATE INDEX ix_order_line_items_vendor_order_id ON order_line_items (vendor_order_id);")
    op.execute(
        "CREATE INDEX ix_order_line_items_product_id ON order_line_items (product_id)"
        " WHERE product_id IS NOT NULL;"
    )

    # ── 6. Create fulfillments table ───────────────────────────────────────
    op.execute("""
        CREATE TABLE fulfillments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            fulfillment_number VARCHAR(50) NOT NULL,
            vendor_order_id UUID NOT NULL REFERENCES vendor_orders(id) ON DELETE CASCADE,
            status fulfillmentstatus NOT NULL DEFAULT 'PENDING',
            carrier VARCHAR(100),
            tracking_number VARCHAR(100),
            shipped_at TIMESTAMPTZ,
            estimated_delivery TIMESTAMPTZ,
            delivered_at TIMESTAMPTZ,
            delivery_type deliverytype,
            delivery_address TEXT,
            delivery_contact VARCHAR(100),
            delivery_phone VARCHAR(20),
            accepted_at TIMESTAMPTZ,
            accepted_by VARCHAR(100),
            acceptance_notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_fulfillments_number UNIQUE (fulfillment_number)
        );
    """)
    op.execute("CREATE INDEX ix_fulfillments_vendor_order_id ON fulfillments (vendor_order_id);")
    op.execute("CREATE INDEX ix_fulfillments_status ON fulfillments (status);")

    # ── 7. Create fulfillment_items table ──────────────────────────────────
    op.execute("""
        CREATE TABLE fulfillment_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            fulfillment_id UUID NOT NULL REFERENCES fulfillments(id) ON DELETE CASCADE,
            order_line_item_id UUID NOT NULL REFERENCES order_line_items(id) ON DELETE CASCADE,
            status fulfillmentlineitemstatus NOT NULL DEFAULT 'PENDING',
            quantity_shipped INTEGER NOT NULL,
            quantity_delivered INTEGER,
            quantity_accepted INTEGER,
            quantity_rejected INTEGER,
            rejection_reason TEXT,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX ix_fulfillment_items_fulfillment_id ON fulfillment_items (fulfillment_id);")
    op.execute("CREATE INDEX ix_fulfillment_items_order_line_item_id ON fulfillment_items (order_line_item_id);")

    # ── 8. Status rollup trigger ───────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION update_order_status_rollup()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Update vendor order status based on fulfillments
            UPDATE vendor_orders vo
            SET status = (
                CASE
                    WHEN NOT EXISTS (
                        SELECT 1 FROM fulfillments f WHERE f.vendor_order_id = vo.id
                    ) THEN vo.status
                    WHEN EXISTS (
                        SELECT 1 FROM fulfillments f
                        WHERE f.vendor_order_id = vo.id AND f.status = 'REJECTED'
                    ) THEN 'DISPUTED'
                    WHEN NOT EXISTS (
                        SELECT 1 FROM fulfillments f
                        WHERE f.vendor_order_id = vo.id AND f.status != 'ACCEPTED'
                    ) THEN 'FULFILLED'
                    WHEN EXISTS (
                        SELECT 1 FROM fulfillments f
                        WHERE f.vendor_order_id = vo.id AND f.status = 'DELIVERED'
                    ) THEN 'DELIVERED'
                    WHEN EXISTS (
                        SELECT 1 FROM fulfillments f
                        WHERE f.vendor_order_id = vo.id AND f.status = 'IN_TRANSIT'
                    ) THEN 'IN_TRANSIT'
                    ELSE vo.status
                END
            )::vendororderstatus
            WHERE vo.id = NEW.vendor_order_id;

            -- Update parent order status
            UPDATE orders o
            SET status = (
                SELECT
                    CASE
                        WHEN bool_and(vo.status = 'FULFILLED') THEN 'FULFILLED'
                        WHEN bool_or(vo.status = 'DISPUTED') THEN 'DISPUTED'
                        WHEN bool_or(vo.status IN ('DELIVERED', 'FULFILLED')) AND
                             bool_or(vo.status NOT IN ('DELIVERED', 'FULFILLED', 'CANCELLED'))
                        THEN 'PARTIALLY_FULFILLED'
                        WHEN bool_or(vo.status = 'IN_TRANSIT') THEN 'PROCESSING'
                        ELSE o.status::text
                    END
                FROM vendor_orders vo
                WHERE vo.order_id = o.id
            )::orderstatus
            WHERE o.id = (SELECT order_id FROM vendor_orders WHERE id = NEW.vendor_order_id);

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER fulfillment_status_rollup_trigger
        AFTER UPDATE OF status ON fulfillments
        FOR EACH ROW
        EXECUTE FUNCTION update_order_status_rollup();
    """)

    # ── 9. RLS policies ───────────────────────────────────────────────────
    # orders: admin OR buyer_org can access
    op.execute("ALTER TABLE orders ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE orders FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY orders_select_policy ON orders FOR SELECT
          USING (
            is_admin_bypass_active()
            OR buyer_org_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY orders_insert_policy ON orders FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR buyer_org_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY orders_update_policy ON orders FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR buyer_org_id::text = get_tenant_setting('app.current_organization_id')
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR buyer_org_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)

    # vendor_orders: admin OR supplier_id OR buyer_org (via orders)
    op.execute("ALTER TABLE vendor_orders ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE vendor_orders FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY vendor_orders_select_policy ON vendor_orders FOR SELECT
          USING (
            is_admin_bypass_active()
            OR supplier_id::text = get_tenant_setting('app.current_organization_id')
            OR EXISTS (
              SELECT 1 FROM orders o
              WHERE o.id = vendor_orders.order_id
                AND o.buyer_org_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY vendor_orders_insert_policy ON vendor_orders FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM orders o
              WHERE o.id = vendor_orders.order_id
                AND o.buyer_org_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY vendor_orders_update_policy ON vendor_orders FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR supplier_id::text = get_tenant_setting('app.current_organization_id')
            OR EXISTS (
              SELECT 1 FROM orders o
              WHERE o.id = vendor_orders.order_id
                AND o.buyer_org_id::text = get_tenant_setting('app.current_organization_id')
            )
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR supplier_id::text = get_tenant_setting('app.current_organization_id')
            OR EXISTS (
              SELECT 1 FROM orders o
              WHERE o.id = vendor_orders.order_id
                AND o.buyer_org_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)

    # order_line_items: via vendor_orders ownership
    op.execute("ALTER TABLE order_line_items ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE order_line_items FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY order_line_items_select_policy ON order_line_items FOR SELECT
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM vendor_orders vo
              JOIN orders o ON o.id = vo.order_id
              WHERE vo.id = order_line_items.vendor_order_id
                AND (
                  vo.supplier_id::text = get_tenant_setting('app.current_organization_id')
                  OR o.buyer_org_id::text = get_tenant_setting('app.current_organization_id')
                )
            )
          );
    """)
    op.execute("""
        CREATE POLICY order_line_items_insert_policy ON order_line_items FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM vendor_orders vo
              JOIN orders o ON o.id = vo.order_id
              WHERE vo.id = order_line_items.vendor_order_id
                AND o.buyer_org_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY order_line_items_update_policy ON order_line_items FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM vendor_orders vo
              JOIN orders o ON o.id = vo.order_id
              WHERE vo.id = order_line_items.vendor_order_id
                AND (
                  vo.supplier_id::text = get_tenant_setting('app.current_organization_id')
                  OR o.buyer_org_id::text = get_tenant_setting('app.current_organization_id')
                )
            )
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM vendor_orders vo
              JOIN orders o ON o.id = vo.order_id
              WHERE vo.id = order_line_items.vendor_order_id
                AND (
                  vo.supplier_id::text = get_tenant_setting('app.current_organization_id')
                  OR o.buyer_org_id::text = get_tenant_setting('app.current_organization_id')
                )
            )
          );
    """)

    # fulfillments: via vendor_orders ownership
    op.execute("ALTER TABLE fulfillments ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE fulfillments FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY fulfillments_select_policy ON fulfillments FOR SELECT
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM vendor_orders vo
              JOIN orders o ON o.id = vo.order_id
              WHERE vo.id = fulfillments.vendor_order_id
                AND (
                  vo.supplier_id::text = get_tenant_setting('app.current_organization_id')
                  OR o.buyer_org_id::text = get_tenant_setting('app.current_organization_id')
                )
            )
          );
    """)
    op.execute("""
        CREATE POLICY fulfillments_insert_policy ON fulfillments FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM vendor_orders vo
              WHERE vo.id = fulfillments.vendor_order_id
                AND vo.supplier_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY fulfillments_update_policy ON fulfillments FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM vendor_orders vo
              WHERE vo.id = fulfillments.vendor_order_id
                AND vo.supplier_id::text = get_tenant_setting('app.current_organization_id')
            )
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM vendor_orders vo
              WHERE vo.id = fulfillments.vendor_order_id
                AND vo.supplier_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)

    # fulfillment_items: via fulfillments → vendor_orders ownership
    op.execute("ALTER TABLE fulfillment_items ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE fulfillment_items FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY fulfillment_items_select_policy ON fulfillment_items FOR SELECT
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM fulfillments f
              JOIN vendor_orders vo ON vo.id = f.vendor_order_id
              JOIN orders o ON o.id = vo.order_id
              WHERE f.id = fulfillment_items.fulfillment_id
                AND (
                  vo.supplier_id::text = get_tenant_setting('app.current_organization_id')
                  OR o.buyer_org_id::text = get_tenant_setting('app.current_organization_id')
                )
            )
          );
    """)
    op.execute("""
        CREATE POLICY fulfillment_items_insert_policy ON fulfillment_items FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM fulfillments f
              JOIN vendor_orders vo ON vo.id = f.vendor_order_id
              WHERE f.id = fulfillment_items.fulfillment_id
                AND vo.supplier_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY fulfillment_items_update_policy ON fulfillment_items FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM fulfillments f
              JOIN vendor_orders vo ON vo.id = f.vendor_order_id
              WHERE f.id = fulfillment_items.fulfillment_id
                AND vo.supplier_id::text = get_tenant_setting('app.current_organization_id')
            )
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM fulfillments f
              JOIN vendor_orders vo ON vo.id = f.vendor_order_id
              WHERE f.id = fulfillment_items.fulfillment_id
                AND vo.supplier_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)


def downgrade() -> None:
    # ── Reverse RLS ────────────────────────────────────────────────────────
    op.execute("DROP POLICY IF EXISTS fulfillment_items_update_policy ON fulfillment_items;")
    op.execute("DROP POLICY IF EXISTS fulfillment_items_insert_policy ON fulfillment_items;")
    op.execute("DROP POLICY IF EXISTS fulfillment_items_select_policy ON fulfillment_items;")
    op.execute("ALTER TABLE fulfillment_items DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS fulfillments_update_policy ON fulfillments;")
    op.execute("DROP POLICY IF EXISTS fulfillments_insert_policy ON fulfillments;")
    op.execute("DROP POLICY IF EXISTS fulfillments_select_policy ON fulfillments;")
    op.execute("ALTER TABLE fulfillments DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS order_line_items_update_policy ON order_line_items;")
    op.execute("DROP POLICY IF EXISTS order_line_items_insert_policy ON order_line_items;")
    op.execute("DROP POLICY IF EXISTS order_line_items_select_policy ON order_line_items;")
    op.execute("ALTER TABLE order_line_items DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS vendor_orders_update_policy ON vendor_orders;")
    op.execute("DROP POLICY IF EXISTS vendor_orders_insert_policy ON vendor_orders;")
    op.execute("DROP POLICY IF EXISTS vendor_orders_select_policy ON vendor_orders;")
    op.execute("ALTER TABLE vendor_orders DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS orders_update_policy ON orders;")
    op.execute("DROP POLICY IF EXISTS orders_insert_policy ON orders;")
    op.execute("DROP POLICY IF EXISTS orders_select_policy ON orders;")
    op.execute("ALTER TABLE orders DISABLE ROW LEVEL SECURITY;")

    # ── Reverse trigger ────────────────────────────────────────────────────
    op.execute("DROP TRIGGER IF EXISTS fulfillment_status_rollup_trigger ON fulfillments;")
    op.execute("DROP FUNCTION IF EXISTS update_order_status_rollup();")

    # ── Drop tables in reverse order ───────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_fulfillment_items_order_line_item_id;")
    op.execute("DROP INDEX IF EXISTS ix_fulfillment_items_fulfillment_id;")
    op.execute("DROP TABLE IF EXISTS fulfillment_items;")

    op.execute("DROP INDEX IF EXISTS ix_fulfillments_status;")
    op.execute("DROP INDEX IF EXISTS ix_fulfillments_vendor_order_id;")
    op.execute("DROP TABLE IF EXISTS fulfillments;")

    op.execute("DROP INDEX IF EXISTS ix_order_line_items_product_id;")
    op.execute("DROP INDEX IF EXISTS ix_order_line_items_vendor_order_id;")
    op.execute("DROP TABLE IF EXISTS order_line_items;")

    op.execute("DROP INDEX IF EXISTS ix_vendor_orders_status;")
    op.execute("DROP INDEX IF EXISTS ix_vendor_orders_supplier_id;")
    op.execute("DROP INDEX IF EXISTS ix_vendor_orders_order_id;")
    op.execute("DROP TABLE IF EXISTS vendor_orders;")

    op.execute("DROP INDEX IF EXISTS ix_orders_order_number;")
    op.execute("DROP INDEX IF EXISTS ix_orders_rfq_id;")
    op.execute("DROP INDEX IF EXISTS ix_orders_status;")
    op.execute("DROP INDEX IF EXISTS ix_orders_buyer_org_id;")
    op.execute("DROP TABLE IF EXISTS orders;")

    # ── Drop sequence ──────────────────────────────────────────────────────
    op.execute("DROP SEQUENCE IF EXISTS order_reference_seq;")

    # ── Drop enum types ────────────────────────────────────────────────────
    op.execute("DROP TYPE IF EXISTS deliverytype;")
    op.execute("DROP TYPE IF EXISTS fulfillmentlineitemstatus;")
    op.execute("DROP TYPE IF EXISTS fulfillmentstatus;")
    op.execute("DROP TYPE IF EXISTS vendororderstatus;")
    op.execute("DROP TYPE IF EXISTS orderstatus;")
