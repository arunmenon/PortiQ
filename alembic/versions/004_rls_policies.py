"""Row-level security policies for multi-tenancy

Revision ID: 004
Revises: 003
Create Date: 2026-02-06

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Helper functions ---
    op.execute("""
        CREATE OR REPLACE FUNCTION get_tenant_setting(setting_name TEXT)
        RETURNS TEXT LANGUAGE sql STABLE SECURITY DEFINER AS $$
          SELECT COALESCE(current_setting(setting_name, true), '');
        $$;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION is_admin_bypass_active()
        RETURNS BOOLEAN LANGUAGE sql STABLE SECURITY DEFINER AS $$
          SELECT COALESCE(current_setting('app.admin_bypass', true), 'false') = 'true';
        $$;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION set_organization_id()
        RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
        DECLARE
          current_org_id UUID;
        BEGIN
          current_org_id := NULLIF(get_tenant_setting('app.current_organization_id'), '')::UUID;
          IF current_org_id IS NULL THEN
            RAISE EXCEPTION 'app.current_organization_id must be set for INSERT on tenant-scoped tables';
          END IF;
          IF TG_TABLE_NAME = 'supplier_products' THEN
            IF NEW.supplier_id IS NULL THEN
              NEW.supplier_id := current_org_id;
            ELSIF NEW.supplier_id != current_org_id AND NOT is_admin_bypass_active() THEN
              RAISE EXCEPTION 'Cannot insert supplier_product for a different organization';
            END IF;
          END IF;
          RETURN NEW;
        END;
        $$;
    """)

    # --- SUPPLIER_PRODUCTS RLS ---
    op.execute("ALTER TABLE supplier_products ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE supplier_products FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY supplier_products_select_policy ON supplier_products FOR SELECT
          USING (is_admin_bypass_active() OR supplier_id::text = get_tenant_setting('app.current_organization_id')
            OR (is_active = true AND get_tenant_setting('app.current_organization_id') != ''));
    """)

    op.execute("""
        CREATE POLICY supplier_products_insert_policy ON supplier_products FOR INSERT
          WITH CHECK (is_admin_bypass_active() OR supplier_id::text = get_tenant_setting('app.current_organization_id'));
    """)

    op.execute("""
        CREATE POLICY supplier_products_update_policy ON supplier_products FOR UPDATE
          USING (is_admin_bypass_active() OR supplier_id::text = get_tenant_setting('app.current_organization_id'))
          WITH CHECK (is_admin_bypass_active() OR supplier_id::text = get_tenant_setting('app.current_organization_id'));
    """)

    op.execute("""
        CREATE POLICY supplier_products_delete_policy ON supplier_products FOR DELETE
          USING (is_admin_bypass_active() OR supplier_id::text = get_tenant_setting('app.current_organization_id'));
    """)

    op.execute("""
        CREATE TRIGGER trg_supplier_products_set_org
          BEFORE INSERT ON supplier_products
          FOR EACH ROW EXECUTE FUNCTION set_organization_id();
    """)

    # --- SUPPLIER_PRODUCT_PRICES RLS ---
    op.execute("ALTER TABLE supplier_product_prices ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE supplier_product_prices FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY supplier_product_prices_select_policy ON supplier_product_prices FOR SELECT
          USING (is_admin_bypass_active() OR EXISTS (SELECT 1 FROM supplier_products sp WHERE sp.id = supplier_product_prices.supplier_product_id
            AND (sp.supplier_id::text = get_tenant_setting('app.current_organization_id') OR (sp.is_active = true AND get_tenant_setting('app.current_organization_id') != ''))));
    """)

    op.execute("""
        CREATE POLICY supplier_product_prices_insert_policy ON supplier_product_prices FOR INSERT
          WITH CHECK (is_admin_bypass_active() OR EXISTS (SELECT 1 FROM supplier_products sp WHERE sp.id = supplier_product_prices.supplier_product_id
            AND sp.supplier_id::text = get_tenant_setting('app.current_organization_id')));
    """)

    op.execute("""
        CREATE POLICY supplier_product_prices_update_policy ON supplier_product_prices FOR UPDATE
          USING (is_admin_bypass_active() OR EXISTS (SELECT 1 FROM supplier_products sp WHERE sp.id = supplier_product_prices.supplier_product_id
            AND sp.supplier_id::text = get_tenant_setting('app.current_organization_id')));
    """)

    op.execute("""
        CREATE POLICY supplier_product_prices_delete_policy ON supplier_product_prices FOR DELETE
          USING (is_admin_bypass_active() OR EXISTS (SELECT 1 FROM supplier_products sp WHERE sp.id = supplier_product_prices.supplier_product_id
            AND sp.supplier_id::text = get_tenant_setting('app.current_organization_id')));
    """)

    # --- USERS RLS ---
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE users FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY users_select_policy ON users FOR SELECT
          USING (is_admin_bypass_active() OR organization_id::text = get_tenant_setting('app.current_organization_id'));
    """)

    op.execute("""
        CREATE POLICY users_insert_policy ON users FOR INSERT
          WITH CHECK (is_admin_bypass_active() OR organization_id::text = get_tenant_setting('app.current_organization_id'));
    """)

    op.execute("""
        CREATE POLICY users_update_policy ON users FOR UPDATE
          USING (is_admin_bypass_active() OR organization_id::text = get_tenant_setting('app.current_organization_id'))
          WITH CHECK (is_admin_bypass_active() OR organization_id::text = get_tenant_setting('app.current_organization_id'));
    """)

    op.execute("""
        CREATE POLICY users_delete_policy ON users FOR DELETE
          USING (is_admin_bypass_active() OR organization_id::text = get_tenant_setting('app.current_organization_id'));
    """)

    # --- Additional indexes for RLS performance ---
    op.execute("CREATE INDEX IF NOT EXISTS idx_supplier_products_supplier_id ON supplier_products (supplier_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_supplier_product_prices_supplier_product_id ON supplier_product_prices (supplier_product_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_organization_id ON users (organization_id);")


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_users_organization_id;")
    op.execute("DROP INDEX IF EXISTS idx_supplier_product_prices_supplier_product_id;")
    op.execute("DROP INDEX IF EXISTS idx_supplier_products_supplier_id;")

    # Drop users RLS
    op.execute("DROP POLICY IF EXISTS users_delete_policy ON users;")
    op.execute("DROP POLICY IF EXISTS users_update_policy ON users;")
    op.execute("DROP POLICY IF EXISTS users_insert_policy ON users;")
    op.execute("DROP POLICY IF EXISTS users_select_policy ON users;")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY;")

    # Drop supplier_product_prices RLS
    op.execute("DROP POLICY IF EXISTS supplier_product_prices_delete_policy ON supplier_product_prices;")
    op.execute("DROP POLICY IF EXISTS supplier_product_prices_update_policy ON supplier_product_prices;")
    op.execute("DROP POLICY IF EXISTS supplier_product_prices_insert_policy ON supplier_product_prices;")
    op.execute("DROP POLICY IF EXISTS supplier_product_prices_select_policy ON supplier_product_prices;")
    op.execute("ALTER TABLE supplier_product_prices DISABLE ROW LEVEL SECURITY;")

    # Drop supplier_products RLS
    op.execute("DROP TRIGGER IF EXISTS trg_supplier_products_set_org ON supplier_products;")
    op.execute("DROP POLICY IF EXISTS supplier_products_delete_policy ON supplier_products;")
    op.execute("DROP POLICY IF EXISTS supplier_products_update_policy ON supplier_products;")
    op.execute("DROP POLICY IF EXISTS supplier_products_insert_policy ON supplier_products;")
    op.execute("DROP POLICY IF EXISTS supplier_products_select_policy ON supplier_products;")
    op.execute("ALTER TABLE supplier_products DISABLE ROW LEVEL SECURITY;")

    # Drop helper functions
    op.execute("DROP FUNCTION IF EXISTS set_organization_id();")
    op.execute("DROP FUNCTION IF EXISTS is_admin_bypass_active();")
    op.execute("DROP FUNCTION IF EXISTS get_tenant_setting(TEXT);")
