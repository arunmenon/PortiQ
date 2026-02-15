"""Delivery and proof-of-delivery tables

Revision ID: 018
Revises: 017
Create Date: 2026-02-14

Creates: deliveries, delivery_items, delivery_photos, delivery_sla_configs
Enums: deliverystatus, deliveryitemstatus, deliveryphototype
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "018"
down_revision: str | None = "017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Create enum types ──────────────────────────────────────────────
    op.execute("""
        CREATE TYPE deliverystatus AS ENUM (
            'PENDING', 'DISPATCHED', 'IN_TRANSIT', 'ARRIVED',
            'DELIVERED', 'ACCEPTED', 'DISPUTED', 'CANCELLED'
        );
    """)
    op.execute("""
        CREATE TYPE deliveryitemstatus AS ENUM (
            'PENDING', 'DELIVERED', 'ACCEPTED',
            'PARTIALLY_ACCEPTED', 'REJECTED', 'DISPUTED'
        );
    """)
    op.execute("""
        CREATE TYPE deliveryphototype AS ENUM (
            'DELIVERY', 'DAMAGE', 'PACKAGING', 'QUANTITY', 'DISPUTE'
        );
    """)

    # ── 2. Create deliveries table ─────────────────────────────────────────
    op.execute("""
        CREATE TABLE deliveries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            delivery_number VARCHAR(50) NOT NULL,
            fulfillment_id UUID NOT NULL REFERENCES fulfillments(id) ON DELETE CASCADE,
            vendor_order_id UUID NOT NULL REFERENCES vendor_orders(id) ON DELETE CASCADE,
            order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

            status deliverystatus NOT NULL DEFAULT 'PENDING',

            -- Dispatch info
            dispatched_at TIMESTAMPTZ,
            dispatched_by UUID REFERENCES users(id) ON DELETE SET NULL,
            estimated_arrival TIMESTAMPTZ,

            -- Delivery info
            delivered_at TIMESTAMPTZ,
            delivered_by UUID REFERENCES users(id) ON DELETE SET NULL,
            delivery_type deliverytype,

            -- GPS coordinates
            delivery_latitude NUMERIC(10, 8),
            delivery_longitude NUMERIC(11, 8),
            gps_accuracy_meters NUMERIC(8, 2),

            -- Receiver info
            receiver_name VARCHAR(200) NOT NULL DEFAULT '',
            receiver_designation VARCHAR(100),
            receiver_contact VARCHAR(50),

            -- Signature
            signature_s3_key VARCHAR(500),
            signature_captured_at TIMESTAMPTZ,

            -- SLA
            sla_target_time TIMESTAMPTZ,
            sla_met BOOLEAN,
            delay_reason TEXT,

            -- Acceptance
            accepted_at TIMESTAMPTZ,
            accepted_by UUID REFERENCES users(id) ON DELETE SET NULL,
            acceptance_notes TEXT,

            -- Dispute
            disputed_at TIMESTAMPTZ,
            dispute_reason TEXT,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_deliveries_delivery_number UNIQUE (delivery_number)
        );
    """)
    op.execute("CREATE INDEX ix_deliveries_fulfillment_id ON deliveries (fulfillment_id);")
    op.execute("CREATE INDEX ix_deliveries_order_id ON deliveries (order_id);")
    op.execute("CREATE INDEX ix_deliveries_organization_id ON deliveries (organization_id);")
    op.execute("CREATE INDEX ix_deliveries_status ON deliveries (status);")
    op.execute("CREATE INDEX ix_deliveries_vendor_order_id ON deliveries (vendor_order_id);")

    # ── 3. Create delivery_items table ─────────────────────────────────────
    op.execute("""
        CREATE TABLE delivery_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            delivery_id UUID NOT NULL REFERENCES deliveries(id) ON DELETE CASCADE,
            fulfillment_item_id UUID NOT NULL REFERENCES fulfillment_items(id) ON DELETE CASCADE,
            order_line_item_id UUID NOT NULL REFERENCES order_line_items(id) ON DELETE CASCADE,

            quantity_expected INTEGER NOT NULL,
            quantity_delivered INTEGER,
            quantity_accepted INTEGER,
            quantity_rejected INTEGER NOT NULL DEFAULT 0,

            status deliveryitemstatus NOT NULL DEFAULT 'PENDING',
            rejection_reason TEXT,
            notes TEXT,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX ix_delivery_items_delivery_id ON delivery_items (delivery_id);")
    op.execute("CREATE INDEX ix_delivery_items_fulfillment_item_id ON delivery_items (fulfillment_item_id);")

    # ── 4. Create delivery_photos table ────────────────────────────────────
    op.execute("""
        CREATE TABLE delivery_photos (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            delivery_id UUID NOT NULL REFERENCES deliveries(id) ON DELETE CASCADE,
            delivery_item_id UUID REFERENCES delivery_items(id) ON DELETE SET NULL,

            s3_key VARCHAR(500) NOT NULL,
            s3_bucket VARCHAR(100) NOT NULL,
            file_name VARCHAR(255),
            content_type VARCHAR(50) NOT NULL DEFAULT 'image/jpeg',
            file_size_bytes INTEGER,

            photo_type deliveryphototype NOT NULL DEFAULT 'DELIVERY',
            caption TEXT,

            taken_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            latitude NUMERIC(10, 8),
            longitude NUMERIC(11, 8),

            uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX ix_delivery_photos_delivery_id ON delivery_photos (delivery_id);")

    # ── 5. Create delivery_sla_configs table ───────────────────────────────
    op.execute("""
        CREATE TABLE delivery_sla_configs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            buyer_org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            supplier_org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            port_code VARCHAR(10),

            delivery_window_hours INTEGER NOT NULL DEFAULT 24,
            max_delay_hours INTEGER NOT NULL DEFAULT 4,

            late_delivery_penalty_percent NUMERIC(5, 2) DEFAULT 0,
            no_show_penalty_percent NUMERIC(5, 2) DEFAULT 0,

            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_delivery_sla_buyer_supplier_port UNIQUE (buyer_org_id, supplier_org_id, port_code)
        );
    """)

    # ── 6. RLS policies ───────────────────────────────────────────────────
    # deliveries: admin OR organization_id OR buyer via order
    op.execute("ALTER TABLE deliveries ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE deliveries FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY deliveries_select_policy ON deliveries FOR SELECT
          USING (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
            OR EXISTS (
              SELECT 1 FROM orders o
              WHERE o.id = deliveries.order_id
                AND o.buyer_org_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY deliveries_insert_policy ON deliveries FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY deliveries_update_policy ON deliveries FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
            OR EXISTS (
              SELECT 1 FROM orders o
              WHERE o.id = deliveries.order_id
                AND o.buyer_org_id::text = get_tenant_setting('app.current_organization_id')
            )
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
            OR EXISTS (
              SELECT 1 FROM orders o
              WHERE o.id = deliveries.order_id
                AND o.buyer_org_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)

    # delivery_items: via deliveries ownership
    op.execute("ALTER TABLE delivery_items ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE delivery_items FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY delivery_items_select_policy ON delivery_items FOR SELECT
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM deliveries d
              WHERE d.id = delivery_items.delivery_id
                AND (
                  d.organization_id::text = get_tenant_setting('app.current_organization_id')
                  OR EXISTS (
                    SELECT 1 FROM orders o
                    WHERE o.id = d.order_id
                      AND o.buyer_org_id::text = get_tenant_setting('app.current_organization_id')
                  )
                )
            )
          );
    """)
    op.execute("""
        CREATE POLICY delivery_items_insert_policy ON delivery_items FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM deliveries d
              WHERE d.id = delivery_items.delivery_id
                AND d.organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY delivery_items_update_policy ON delivery_items FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM deliveries d
              WHERE d.id = delivery_items.delivery_id
                AND (
                  d.organization_id::text = get_tenant_setting('app.current_organization_id')
                  OR EXISTS (
                    SELECT 1 FROM orders o
                    WHERE o.id = d.order_id
                      AND o.buyer_org_id::text = get_tenant_setting('app.current_organization_id')
                  )
                )
            )
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM deliveries d
              WHERE d.id = delivery_items.delivery_id
                AND (
                  d.organization_id::text = get_tenant_setting('app.current_organization_id')
                  OR EXISTS (
                    SELECT 1 FROM orders o
                    WHERE o.id = d.order_id
                      AND o.buyer_org_id::text = get_tenant_setting('app.current_organization_id')
                  )
                )
            )
          );
    """)

    # delivery_photos: via deliveries ownership
    op.execute("ALTER TABLE delivery_photos ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE delivery_photos FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY delivery_photos_select_policy ON delivery_photos FOR SELECT
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM deliveries d
              WHERE d.id = delivery_photos.delivery_id
                AND (
                  d.organization_id::text = get_tenant_setting('app.current_organization_id')
                  OR EXISTS (
                    SELECT 1 FROM orders o
                    WHERE o.id = d.order_id
                      AND o.buyer_org_id::text = get_tenant_setting('app.current_organization_id')
                  )
                )
            )
          );
    """)
    op.execute("""
        CREATE POLICY delivery_photos_insert_policy ON delivery_photos FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM deliveries d
              WHERE d.id = delivery_photos.delivery_id
                AND d.organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)

    # delivery_sla_configs: admin OR buyer_org OR supplier_org
    op.execute("ALTER TABLE delivery_sla_configs ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE delivery_sla_configs FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY delivery_sla_configs_select_policy ON delivery_sla_configs FOR SELECT
          USING (
            is_admin_bypass_active()
            OR buyer_org_id::text = get_tenant_setting('app.current_organization_id')
            OR supplier_org_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY delivery_sla_configs_insert_policy ON delivery_sla_configs FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR buyer_org_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY delivery_sla_configs_update_policy ON delivery_sla_configs FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR buyer_org_id::text = get_tenant_setting('app.current_organization_id')
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR buyer_org_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)


def downgrade() -> None:
    # ── Reverse RLS ────────────────────────────────────────────────────────
    op.execute("DROP POLICY IF EXISTS delivery_sla_configs_update_policy ON delivery_sla_configs;")
    op.execute("DROP POLICY IF EXISTS delivery_sla_configs_insert_policy ON delivery_sla_configs;")
    op.execute("DROP POLICY IF EXISTS delivery_sla_configs_select_policy ON delivery_sla_configs;")
    op.execute("ALTER TABLE delivery_sla_configs DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS delivery_photos_insert_policy ON delivery_photos;")
    op.execute("DROP POLICY IF EXISTS delivery_photos_select_policy ON delivery_photos;")
    op.execute("ALTER TABLE delivery_photos DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS delivery_items_update_policy ON delivery_items;")
    op.execute("DROP POLICY IF EXISTS delivery_items_insert_policy ON delivery_items;")
    op.execute("DROP POLICY IF EXISTS delivery_items_select_policy ON delivery_items;")
    op.execute("ALTER TABLE delivery_items DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS deliveries_update_policy ON deliveries;")
    op.execute("DROP POLICY IF EXISTS deliveries_insert_policy ON deliveries;")
    op.execute("DROP POLICY IF EXISTS deliveries_select_policy ON deliveries;")
    op.execute("ALTER TABLE deliveries DISABLE ROW LEVEL SECURITY;")

    # ── Drop tables ────────────────────────────────────────────────────────
    op.execute("DROP TABLE IF EXISTS delivery_sla_configs;")

    op.execute("DROP INDEX IF EXISTS ix_delivery_photos_delivery_id;")
    op.execute("DROP TABLE IF EXISTS delivery_photos;")

    op.execute("DROP INDEX IF EXISTS ix_delivery_items_fulfillment_item_id;")
    op.execute("DROP INDEX IF EXISTS ix_delivery_items_delivery_id;")
    op.execute("DROP TABLE IF EXISTS delivery_items;")

    op.execute("DROP INDEX IF EXISTS ix_deliveries_vendor_order_id;")
    op.execute("DROP INDEX IF EXISTS ix_deliveries_status;")
    op.execute("DROP INDEX IF EXISTS ix_deliveries_organization_id;")
    op.execute("DROP INDEX IF EXISTS ix_deliveries_order_id;")
    op.execute("DROP INDEX IF EXISTS ix_deliveries_fulfillment_id;")
    op.execute("DROP TABLE IF EXISTS deliveries;")

    # ── Drop enum types ────────────────────────────────────────────────────
    op.execute("DROP TYPE IF EXISTS deliveryphototype;")
    op.execute("DROP TYPE IF EXISTS deliveryitemstatus;")
    op.execute("DROP TYPE IF EXISTS deliverystatus;")
