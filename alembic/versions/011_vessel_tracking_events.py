"""Vessel tracking and event outbox tables

Revision ID: 011
Revises: 010
Create Date: 2026-02-07

Creates: vessels, vessel_positions, port_calls, event_outbox, processed_events
Enums: vesseltype, vesselstatus, navigationstatus, portcallstatus, aisprovider, eventstatus
RLS: vessel ownership, admin-only for events
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create enum types ──────────────────────────────────────────────
    op.execute("""
        CREATE TYPE vesseltype AS ENUM (
            'BULK_CARRIER', 'CONTAINER', 'TANKER', 'GENERAL_CARGO',
            'PASSENGER', 'RO_RO', 'OFFSHORE', 'FISHING', 'TUG', 'OTHER'
        );
    """)
    op.execute("""
        CREATE TYPE vesselstatus AS ENUM (
            'ACTIVE', 'INACTIVE', 'DECOMMISSIONED'
        );
    """)
    op.execute("""
        CREATE TYPE navigationstatus AS ENUM (
            'UNDER_WAY', 'AT_ANCHOR', 'NOT_UNDER_COMMAND',
            'RESTRICTED_MANOEUVRABILITY', 'MOORED', 'AGROUND',
            'FISHING', 'UNDER_WAY_SAILING', 'UNKNOWN'
        );
    """)
    op.execute("""
        CREATE TYPE portcallstatus AS ENUM (
            'APPROACHING', 'ARRIVED', 'BERTHED', 'DEPARTED', 'CANCELLED'
        );
    """)
    op.execute("""
        CREATE TYPE aisprovider AS ENUM (
            'VESSEL_FINDER', 'PCS1X', 'MANUAL'
        );
    """)
    op.execute("""
        CREATE TYPE eventstatus AS ENUM (
            'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'
        );
    """)

    # ── 2. Create vessels table ───────────────────────────────────────────
    op.execute("""
        CREATE TABLE vessels (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            imo_number VARCHAR(7) NOT NULL,
            mmsi VARCHAR(9),
            name VARCHAR(255) NOT NULL,
            vessel_type vesseltype NOT NULL DEFAULT 'OTHER',
            status vesselstatus NOT NULL DEFAULT 'ACTIVE',
            flag_state VARCHAR(3),
            gross_tonnage NUMERIC(12,2),
            deadweight_tonnage NUMERIC(12,2),
            length_overall_m NUMERIC(8,2),
            beam_m NUMERIC(8,2),
            year_built INTEGER,
            crew_size INTEGER,
            owner_organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
            manager_organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
            last_known_port VARCHAR(10),
            last_supply_date TIMESTAMPTZ,
            metadata_extra JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_vessels_imo UNIQUE (imo_number),
            CONSTRAINT ck_vessels_imo_format CHECK (imo_number ~ '^[0-9]{7}$'),
            CONSTRAINT ck_vessels_mmsi_format CHECK (mmsi IS NULL OR mmsi ~ '^[0-9]{9}$')
        );
    """)
    op.execute("CREATE INDEX ix_vessels_mmsi ON vessels (mmsi);")
    op.execute("CREATE INDEX ix_vessels_name ON vessels (name);")
    op.execute("CREATE INDEX ix_vessels_vessel_type ON vessels (vessel_type);")
    op.execute("CREATE INDEX ix_vessels_status ON vessels (status);")
    op.execute("CREATE INDEX ix_vessels_owner_org_id ON vessels (owner_organization_id);")

    # ── 3. Create vessel_positions table ──────────────────────────────────
    op.execute("""
        CREATE TABLE vessel_positions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            vessel_id UUID NOT NULL REFERENCES vessels(id) ON DELETE CASCADE,
            latitude NUMERIC(10,7) NOT NULL,
            longitude NUMERIC(10,7) NOT NULL,
            speed_knots NUMERIC(6,2),
            course NUMERIC(6,2),
            heading NUMERIC(6,2),
            navigation_status navigationstatus NOT NULL DEFAULT 'UNKNOWN',
            source aisprovider NOT NULL DEFAULT 'VESSEL_FINDER',
            signal_confidence NUMERIC(4,3),
            recorded_at TIMESTAMPTZ NOT NULL,
            raw_data JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_vessel_positions_latitude CHECK (latitude BETWEEN -90 AND 90),
            CONSTRAINT ck_vessel_positions_longitude CHECK (longitude BETWEEN -180 AND 180)
        );
    """)
    op.execute("CREATE INDEX ix_vessel_positions_vessel_id ON vessel_positions (vessel_id);")
    op.execute("CREATE INDEX ix_vessel_positions_recorded_at ON vessel_positions (recorded_at);")
    op.execute("CREATE INDEX ix_vessel_positions_vessel_recorded ON vessel_positions (vessel_id, recorded_at);")
    op.execute("CREATE INDEX ix_vessel_positions_source ON vessel_positions (source);")

    # ── 4. Create port_calls table ────────────────────────────────────────
    op.execute("""
        CREATE TABLE port_calls (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            vessel_id UUID NOT NULL REFERENCES vessels(id) ON DELETE CASCADE,
            port_code VARCHAR(10) NOT NULL,
            port_name VARCHAR(255),
            status portcallstatus NOT NULL DEFAULT 'APPROACHING',
            eta TIMESTAMPTZ,
            ata TIMESTAMPTZ,
            atd TIMESTAMPTZ,
            berth VARCHAR(100),
            pilot_time TIMESTAMPTZ,
            distance_nm NUMERIC(10,2),
            eta_confidence NUMERIC(4,3),
            source aisprovider NOT NULL DEFAULT 'VESSEL_FINDER',
            raw_data JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX ix_port_calls_vessel_id ON port_calls (vessel_id);")
    op.execute("CREATE INDEX ix_port_calls_port_code ON port_calls (port_code);")
    op.execute("CREATE INDEX ix_port_calls_status ON port_calls (status);")
    op.execute("CREATE INDEX ix_port_calls_eta ON port_calls (eta);")
    op.execute("CREATE INDEX ix_port_calls_vessel_port ON port_calls (vessel_id, port_code);")

    # ── 5. Create event_outbox table ──────────────────────────────────────
    op.execute("""
        CREATE TABLE event_outbox (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_type VARCHAR(255) NOT NULL,
            aggregate_type VARCHAR(255) NOT NULL,
            aggregate_id VARCHAR(255) NOT NULL,
            payload JSONB NOT NULL DEFAULT '{}',
            status eventstatus NOT NULL DEFAULT 'PENDING',
            retry_count INTEGER NOT NULL DEFAULT 0,
            max_retries INTEGER NOT NULL DEFAULT 3,
            last_error TEXT,
            processed_at TIMESTAMPTZ,
            schema_version INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX ix_event_outbox_status ON event_outbox (status);")
    op.execute("CREATE INDEX ix_event_outbox_event_type ON event_outbox (event_type);")
    op.execute("CREATE INDEX ix_event_outbox_aggregate ON event_outbox (aggregate_type, aggregate_id);")
    op.execute("CREATE INDEX ix_event_outbox_pending ON event_outbox (created_at) WHERE status = 'PENDING';")

    # ── 6. Create processed_events table ──────────────────────────────────
    op.execute("""
        CREATE TABLE processed_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_id UUID NOT NULL,
            event_type VARCHAR(255) NOT NULL,
            handler_name VARCHAR(255) NOT NULL,
            processed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT uq_processed_events_event_id UNIQUE (event_id)
        );
    """)
    op.execute("CREATE INDEX ix_processed_events_expires_at ON processed_events (expires_at);")

    # ── 7. RLS policies ──────────────────────────────────────────────────

    # 7a. vessels: admin bypass OR owner_organization match
    op.execute("ALTER TABLE vessels ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE vessels FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY vessels_select_policy ON vessels FOR SELECT
          USING (
            is_admin_bypass_active()
            OR owner_organization_id::text = get_tenant_setting('app.current_organization_id')
            OR manager_organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY vessels_insert_policy ON vessels FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR owner_organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY vessels_update_policy ON vessels FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR owner_organization_id::text = get_tenant_setting('app.current_organization_id')
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR owner_organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY vessels_delete_policy ON vessels FOR DELETE
          USING (
            is_admin_bypass_active()
            OR owner_organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)

    # 7b. vessel_positions: visible via vessel ownership
    op.execute("ALTER TABLE vessel_positions ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE vessel_positions FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY vessel_positions_select_policy ON vessel_positions FOR SELECT
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM vessels v
              WHERE v.id = vessel_positions.vessel_id
                AND (
                  v.owner_organization_id::text = get_tenant_setting('app.current_organization_id')
                  OR v.manager_organization_id::text = get_tenant_setting('app.current_organization_id')
                )
            )
          );
    """)
    op.execute("""
        CREATE POLICY vessel_positions_insert_policy ON vessel_positions FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM vessels v
              WHERE v.id = vessel_positions.vessel_id
                AND v.owner_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)

    # 7c. port_calls: visible via vessel ownership
    op.execute("ALTER TABLE port_calls ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE port_calls FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY port_calls_select_policy ON port_calls FOR SELECT
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM vessels v
              WHERE v.id = port_calls.vessel_id
                AND (
                  v.owner_organization_id::text = get_tenant_setting('app.current_organization_id')
                  OR v.manager_organization_id::text = get_tenant_setting('app.current_organization_id')
                )
            )
          );
    """)
    op.execute("""
        CREATE POLICY port_calls_insert_policy ON port_calls FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM vessels v
              WHERE v.id = port_calls.vessel_id
                AND v.owner_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY port_calls_update_policy ON port_calls FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM vessels v
              WHERE v.id = port_calls.vessel_id
                AND v.owner_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR EXISTS (
              SELECT 1 FROM vessels v
              WHERE v.id = port_calls.vessel_id
                AND v.owner_organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)

    # 7d. event_outbox: admin bypass only (system-internal)
    op.execute("ALTER TABLE event_outbox ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE event_outbox FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY event_outbox_admin_policy ON event_outbox FOR ALL
          USING (is_admin_bypass_active())
          WITH CHECK (is_admin_bypass_active());
    """)

    # 7e. processed_events: admin bypass only (system-internal)
    op.execute("ALTER TABLE processed_events ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE processed_events FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY processed_events_admin_policy ON processed_events FOR ALL
          USING (is_admin_bypass_active())
          WITH CHECK (is_admin_bypass_active());
    """)


def downgrade() -> None:
    # ── Reverse 7e: Drop processed_events RLS ────────────────────────────
    op.execute("DROP POLICY IF EXISTS processed_events_admin_policy ON processed_events;")
    op.execute("ALTER TABLE processed_events DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 7d: Drop event_outbox RLS ────────────────────────────────
    op.execute("DROP POLICY IF EXISTS event_outbox_admin_policy ON event_outbox;")
    op.execute("ALTER TABLE event_outbox DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 7c: Drop port_calls RLS ──────────────────────────────────
    op.execute("DROP POLICY IF EXISTS port_calls_update_policy ON port_calls;")
    op.execute("DROP POLICY IF EXISTS port_calls_insert_policy ON port_calls;")
    op.execute("DROP POLICY IF EXISTS port_calls_select_policy ON port_calls;")
    op.execute("ALTER TABLE port_calls DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 7b: Drop vessel_positions RLS ────────────────────────────
    op.execute("DROP POLICY IF EXISTS vessel_positions_insert_policy ON vessel_positions;")
    op.execute("DROP POLICY IF EXISTS vessel_positions_select_policy ON vessel_positions;")
    op.execute("ALTER TABLE vessel_positions DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 7a: Drop vessels RLS ─────────────────────────────────────
    op.execute("DROP POLICY IF EXISTS vessels_delete_policy ON vessels;")
    op.execute("DROP POLICY IF EXISTS vessels_update_policy ON vessels;")
    op.execute("DROP POLICY IF EXISTS vessels_insert_policy ON vessels;")
    op.execute("DROP POLICY IF EXISTS vessels_select_policy ON vessels;")
    op.execute("ALTER TABLE vessels DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 6: Drop processed_events ─────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_processed_events_expires_at;")
    op.execute("DROP TABLE IF EXISTS processed_events;")

    # ── Reverse 5: Drop event_outbox ─────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_event_outbox_pending;")
    op.execute("DROP INDEX IF EXISTS ix_event_outbox_aggregate;")
    op.execute("DROP INDEX IF EXISTS ix_event_outbox_event_type;")
    op.execute("DROP INDEX IF EXISTS ix_event_outbox_status;")
    op.execute("DROP TABLE IF EXISTS event_outbox;")

    # ── Reverse 4: Drop port_calls ───────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_port_calls_vessel_port;")
    op.execute("DROP INDEX IF EXISTS ix_port_calls_eta;")
    op.execute("DROP INDEX IF EXISTS ix_port_calls_status;")
    op.execute("DROP INDEX IF EXISTS ix_port_calls_port_code;")
    op.execute("DROP INDEX IF EXISTS ix_port_calls_vessel_id;")
    op.execute("DROP TABLE IF EXISTS port_calls;")

    # ── Reverse 3: Drop vessel_positions ─────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_vessel_positions_source;")
    op.execute("DROP INDEX IF EXISTS ix_vessel_positions_vessel_recorded;")
    op.execute("DROP INDEX IF EXISTS ix_vessel_positions_recorded_at;")
    op.execute("DROP INDEX IF EXISTS ix_vessel_positions_vessel_id;")
    op.execute("DROP TABLE IF EXISTS vessel_positions;")

    # ── Reverse 2: Drop vessels ──────────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_vessels_owner_org_id;")
    op.execute("DROP INDEX IF EXISTS ix_vessels_status;")
    op.execute("DROP INDEX IF EXISTS ix_vessels_vessel_type;")
    op.execute("DROP INDEX IF EXISTS ix_vessels_name;")
    op.execute("DROP INDEX IF EXISTS ix_vessels_mmsi;")
    op.execute("DROP TABLE IF EXISTS vessels;")

    # ── Reverse 1: Drop enum types ───────────────────────────────────────
    op.execute("DROP TYPE IF EXISTS eventstatus;")
    op.execute("DROP TYPE IF EXISTS aisprovider;")
    op.execute("DROP TYPE IF EXISTS portcallstatus;")
    op.execute("DROP TYPE IF EXISTS navigationstatus;")
    op.execute("DROP TYPE IF EXISTS vesselstatus;")
    op.execute("DROP TYPE IF EXISTS vesseltype;")
