"""Multi-tenancy — roles, organization memberships, and enhanced user/org models

Revision ID: 009
Revises: 008
Create Date: 2026-02-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create new enum types ──────────────────────────────────────────
    op.execute("CREATE TYPE membershipstatus AS ENUM ('INVITED', 'ACTIVE');")
    op.execute("CREATE TYPE userstatus AS ENUM ('ACTIVE', 'SUSPENDED', 'PENDING');")
    op.execute("CREATE TYPE organizationstatus AS ENUM ('ACTIVE', 'SUSPENDED');")

    # Add PLATFORM to existing organizationtype enum.
    # ALTER TYPE ... ADD VALUE cannot be used later in the same transaction,
    # so we must commit the current transaction, add the value, then start a new one.
    op.execute("COMMIT;")
    op.execute("ALTER TYPE organizationtype ADD VALUE IF NOT EXISTS 'PLATFORM';")
    op.execute("BEGIN;")

    # ── 2. Create roles table ─────────────────────────────────────────────
    op.execute("""
        CREATE TABLE roles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(50) NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            description VARCHAR(500),
            organization_type organizationtype NOT NULL,
            permissions JSONB NOT NULL DEFAULT '[]',
            is_system BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_roles_name_org_type UNIQUE (name, organization_type)
        );
    """)
    op.execute("CREATE INDEX ix_roles_organization_type ON roles (organization_type);")

    # ── 3. Create organization_memberships table ──────────────────────────
    op.execute("""
        CREATE TABLE organization_memberships (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            role_id UUID NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
            status membershipstatus NOT NULL DEFAULT 'INVITED',
            invited_by UUID REFERENCES users(id) ON DELETE SET NULL,
            invited_at TIMESTAMPTZ,
            joined_at TIMESTAMPTZ,
            job_title VARCHAR(100),
            department VARCHAR(100),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_membership_user_org UNIQUE (user_id, organization_id)
        );
    """)
    op.execute("CREATE INDEX ix_memberships_user_id ON organization_memberships (user_id);")
    op.execute("CREATE INDEX ix_memberships_org_id ON organization_memberships (organization_id);")
    op.execute("CREATE INDEX ix_memberships_status ON organization_memberships (status);")
    op.execute("CREATE INDEX ix_memberships_user_org_status ON organization_memberships (user_id, organization_id, status);")

    # ── 4. Add new columns to users ───────────────────────────────────────
    op.execute("ALTER TABLE users ADD COLUMN phone VARCHAR(20);")
    op.execute("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500);")
    op.execute("ALTER TABLE users ADD COLUMN status userstatus NOT NULL DEFAULT 'ACTIVE';")
    op.execute("ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT false;")
    op.execute("ALTER TABLE users ADD COLUMN email_verified_at TIMESTAMPTZ;")
    op.execute("ALTER TABLE users ADD COLUMN default_organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL;")
    op.execute("ALTER TABLE users ADD COLUMN last_login_at TIMESTAMPTZ;")
    op.execute("ALTER TABLE users ADD COLUMN locale VARCHAR(10) NOT NULL DEFAULT 'en';")
    op.execute("ALTER TABLE users ADD COLUMN timezone VARCHAR(50) NOT NULL DEFAULT 'UTC';")

    # ── 5. Add new columns to organizations ───────────────────────────────
    op.execute("ALTER TABLE organizations ADD COLUMN legal_name VARCHAR(255);")
    op.execute("ALTER TABLE organizations ADD COLUMN slug VARCHAR(100);")
    op.execute("ALTER TABLE organizations ADD COLUMN status organizationstatus NOT NULL DEFAULT 'ACTIVE';")
    op.execute("ALTER TABLE organizations ADD COLUMN primary_email VARCHAR(255);")
    op.execute("ALTER TABLE organizations ADD COLUMN primary_phone VARCHAR(20);")
    op.execute("ALTER TABLE organizations ADD COLUMN website VARCHAR(255);")
    op.execute("ALTER TABLE organizations ADD COLUMN settings JSONB DEFAULT '{}';")

    # Unique partial index on slug where not null
    op.execute("CREATE UNIQUE INDEX ix_organizations_slug ON organizations (slug) WHERE slug IS NOT NULL;")

    # ── 6. Seed 12 system roles ───────────────────────────────────────────
    op.execute("""
        INSERT INTO roles (id, name, display_name, description, organization_type, permissions, is_system) VALUES
        -- BUYER roles
        (gen_random_uuid(), 'buyer_admin', 'Buyer Admin', 'Full access to buyer organization', 'BUYER', '["*"]', true),
        (gen_random_uuid(), 'procurement_manager', 'Procurement Manager', 'Manages procurement operations', 'BUYER',
         '["rfq.create","rfq.manage","orders.create","orders.manage","products.view","products.manage","reports.view","users.view"]', true),
        (gen_random_uuid(), 'procurement_officer', 'Procurement Officer', 'Creates and views procurement items', 'BUYER',
         '["rfq.create","rfq.view","orders.create","orders.view","products.view","reports.view"]', true),
        (gen_random_uuid(), 'buyer_viewer', 'Buyer Viewer', 'Read-only access to buyer organization', 'BUYER',
         '["rfq.view","orders.view","products.view","reports.view"]', true),
        -- SUPPLIER roles
        (gen_random_uuid(), 'supplier_admin', 'Supplier Admin', 'Full access to supplier organization', 'SUPPLIER', '["*"]', true),
        (gen_random_uuid(), 'sales_manager', 'Sales Manager', 'Manages sales and fulfillment', 'SUPPLIER',
         '["quotes.create","quotes.manage","products.view","products.manage","orders.view","orders.manage","reports.view","users.view"]', true),
        (gen_random_uuid(), 'fulfillment_manager', 'Fulfillment Manager', 'Manages order fulfillment', 'SUPPLIER',
         '["orders.view","orders.manage","products.view","reports.view"]', true),
        (gen_random_uuid(), 'sales_rep', 'Sales Representative', 'Creates quotes and views products', 'SUPPLIER',
         '["quotes.create","quotes.view","products.view","orders.view"]', true),
        -- PLATFORM roles
        (gen_random_uuid(), 'super_admin', 'Super Admin', 'Full platform access', 'PLATFORM', '["*"]', true),
        (gen_random_uuid(), 'operations_admin', 'Operations Admin', 'Manages platform operations', 'PLATFORM',
         '["organizations.manage","users.manage","products.manage","reports.view","reports.manage"]', true),
        (gen_random_uuid(), 'support_agent', 'Support Agent', 'Read-only support access', 'PLATFORM',
         '["organizations.view","users.view","products.view","orders.view","reports.view"]', true),
        -- BOTH roles
        (gen_random_uuid(), 'both_viewer', 'Viewer', 'Read-only cross-organization access', 'BOTH',
         '["rfq.view","quotes.view","orders.view","products.view","reports.view"]', true);
    """)

    # ── 7. Data migration: existing users → memberships ───────────────────
    # Note: BOTH-type orgs don't have dedicated admin/manager/officer roles.
    # We map them to the corresponding BUYER roles which have the broadest coverage.
    op.execute("""
        INSERT INTO organization_memberships (id, user_id, organization_id, role_id, status, joined_at, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            u.id,
            u.organization_id,
            CASE
                WHEN u.role = 'OWNER'  AND o.type = 'BUYER'    THEN (SELECT id FROM roles WHERE name = 'buyer_admin'         AND organization_type = 'BUYER' LIMIT 1)
                WHEN u.role = 'OWNER'  AND o.type = 'BOTH'     THEN (SELECT id FROM roles WHERE name = 'buyer_admin'         AND organization_type = 'BUYER' LIMIT 1)
                WHEN u.role = 'OWNER'  AND o.type = 'SUPPLIER'  THEN (SELECT id FROM roles WHERE name = 'supplier_admin'      AND organization_type = 'SUPPLIER' LIMIT 1)
                WHEN u.role = 'ADMIN'  AND o.type = 'BUYER'    THEN (SELECT id FROM roles WHERE name = 'buyer_admin'         AND organization_type = 'BUYER' LIMIT 1)
                WHEN u.role = 'ADMIN'  AND o.type = 'BOTH'     THEN (SELECT id FROM roles WHERE name = 'buyer_admin'         AND organization_type = 'BUYER' LIMIT 1)
                WHEN u.role = 'ADMIN'  AND o.type = 'SUPPLIER'  THEN (SELECT id FROM roles WHERE name = 'supplier_admin'      AND organization_type = 'SUPPLIER' LIMIT 1)
                WHEN u.role = 'MEMBER' AND o.type = 'BUYER'    THEN (SELECT id FROM roles WHERE name = 'procurement_officer'  AND organization_type = 'BUYER' LIMIT 1)
                WHEN u.role = 'MEMBER' AND o.type = 'BOTH'     THEN (SELECT id FROM roles WHERE name = 'procurement_officer'  AND organization_type = 'BUYER' LIMIT 1)
                WHEN u.role = 'MEMBER' AND o.type = 'SUPPLIER'  THEN (SELECT id FROM roles WHERE name = 'sales_rep'           AND organization_type = 'SUPPLIER' LIMIT 1)
                WHEN u.role = 'VIEWER' AND o.type = 'BOTH'     THEN (SELECT id FROM roles WHERE name = 'both_viewer'          AND organization_type = 'BOTH' LIMIT 1)
                WHEN u.role = 'VIEWER' AND o.type = 'BUYER'    THEN (SELECT id FROM roles WHERE name = 'buyer_viewer'         AND organization_type = 'BUYER' LIMIT 1)
                WHEN u.role = 'VIEWER' AND o.type = 'SUPPLIER'  THEN (SELECT id FROM roles WHERE name = 'buyer_viewer'         AND organization_type = 'BUYER' LIMIT 1)
            END,
            'ACTIVE',
            u.created_at,
            NOW(),
            NOW()
        FROM users u
        JOIN organizations o ON o.id = u.organization_id
        WHERE u.organization_id IS NOT NULL;
    """)

    # Set default_organization_id for existing users
    op.execute("UPDATE users SET default_organization_id = organization_id WHERE organization_id IS NOT NULL;")

    # ── 8. Update RLS policies ────────────────────────────────────────────

    # 8a. Drop old users_select_policy and replace with membership-aware version
    op.execute("DROP POLICY IF EXISTS users_select_policy ON users;")
    op.execute("""
        CREATE POLICY users_select_policy ON users FOR SELECT
          USING (
            is_admin_bypass_active()
            OR id::text = get_tenant_setting('app.current_user_id')
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
            OR EXISTS (
              SELECT 1 FROM organization_memberships om
              WHERE om.user_id = users.id
                AND om.organization_id::text = get_tenant_setting('app.current_organization_id')
                AND om.status = 'ACTIVE'
            )
          );
    """)

    # 8b. RLS on organization_memberships
    op.execute("ALTER TABLE organization_memberships ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE organization_memberships FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY memberships_select_policy ON organization_memberships FOR SELECT
          USING (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY memberships_insert_policy ON organization_memberships FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY memberships_update_policy ON organization_memberships FOR UPDATE
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
        CREATE POLICY memberships_delete_policy ON organization_memberships FOR DELETE
          USING (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)

    # 8c. RLS on organizations
    op.execute("ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE organizations FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY organizations_select_policy ON organizations FOR SELECT
          USING (
            is_admin_bypass_active()
            OR id::text = get_tenant_setting('app.current_organization_id')
            OR EXISTS (
              SELECT 1 FROM organization_memberships om
              WHERE om.organization_id = organizations.id
                AND om.user_id::text = get_tenant_setting('app.current_user_id')
                AND om.status = 'ACTIVE'
            )
          );
    """)
    op.execute("""
        CREATE POLICY organizations_update_policy ON organizations FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR id::text = get_tenant_setting('app.current_organization_id')
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR id::text = get_tenant_setting('app.current_organization_id')
          );
    """)


def downgrade() -> None:
    # ── Reverse 8c: Drop organizations RLS ────────────────────────────────
    op.execute("DROP POLICY IF EXISTS organizations_update_policy ON organizations;")
    op.execute("DROP POLICY IF EXISTS organizations_select_policy ON organizations;")
    op.execute("ALTER TABLE organizations DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 8b: Drop organization_memberships RLS ─────────────────────
    op.execute("DROP POLICY IF EXISTS memberships_delete_policy ON organization_memberships;")
    op.execute("DROP POLICY IF EXISTS memberships_update_policy ON organization_memberships;")
    op.execute("DROP POLICY IF EXISTS memberships_insert_policy ON organization_memberships;")
    op.execute("DROP POLICY IF EXISTS memberships_select_policy ON organization_memberships;")
    op.execute("ALTER TABLE organization_memberships DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 8a: Restore old users_select_policy ───────────────────────
    op.execute("DROP POLICY IF EXISTS users_select_policy ON users;")
    op.execute("""
        CREATE POLICY users_select_policy ON users FOR SELECT
          USING (is_admin_bypass_active() OR organization_id::text = get_tenant_setting('app.current_organization_id'));
    """)

    # ── Reverse 5: Drop new organization columns ──────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_organizations_slug;")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS settings;")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS website;")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS primary_phone;")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS primary_email;")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS status;")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS slug;")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS legal_name;")

    # ── Reverse 4: Drop new user columns ──────────────────────────────────
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS timezone;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS locale;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS last_login_at;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS default_organization_id;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS email_verified_at;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS email_verified;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS status;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS avatar_url;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS phone;")

    # ── Reverse 3: Drop organization_memberships table ────────────────────
    op.execute("DROP INDEX IF EXISTS ix_memberships_user_org_status;")
    op.execute("DROP INDEX IF EXISTS ix_memberships_status;")
    op.execute("DROP INDEX IF EXISTS ix_memberships_org_id;")
    op.execute("DROP INDEX IF EXISTS ix_memberships_user_id;")
    op.execute("DROP TABLE IF EXISTS organization_memberships;")

    # ── Reverse 2: Drop roles table ───────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_roles_organization_type;")
    op.execute("DROP TABLE IF EXISTS roles;")

    # ── Reverse 1: Drop enum types ────────────────────────────────────────
    # Note: Cannot remove 'PLATFORM' from organizationtype enum in PostgreSQL
    # without recreating the type, which is risky. Leaving it in place.
    op.execute("DROP TYPE IF EXISTS organizationstatus;")
    op.execute("DROP TYPE IF EXISTS userstatus;")
    op.execute("DROP TYPE IF EXISTS membershipstatus;")
