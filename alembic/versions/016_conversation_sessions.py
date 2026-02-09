"""Conversation sessions for PortiQ AI chat

Revision ID: 016
Revises: 015
Create Date: 2026-02-08

Creates: conversation_sessions
RLS: user can only access own org's sessions
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "016"
down_revision: str | None = "015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Create conversation_sessions table ─────────────────────────────
    op.execute("""
        CREATE TABLE conversation_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            title VARCHAR(255),
            messages JSONB NOT NULL DEFAULT '[]'::jsonb,
            context JSONB,
            metadata_extra JSONB,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)

    # ── 2. Indexes ────────────────────────────────────────────────────────
    op.execute(
        "CREATE INDEX ix_conversation_sessions_user_id ON conversation_sessions (user_id);"
    )
    op.execute(
        "CREATE INDEX ix_conversation_sessions_organization_id ON conversation_sessions (organization_id);"
    )
    op.execute(
        "CREATE INDEX ix_conversation_sessions_is_active ON conversation_sessions (is_active);"
    )

    # ── 3. RLS policies ──────────────────────────────────────────────────
    op.execute("ALTER TABLE conversation_sessions ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE conversation_sessions FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY conversation_sessions_select_policy ON conversation_sessions FOR SELECT
          USING (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY conversation_sessions_insert_policy ON conversation_sessions FOR INSERT
          WITH CHECK (
            is_admin_bypass_active()
            OR organization_id::text = get_tenant_setting('app.current_organization_id')
          );
    """)
    op.execute("""
        CREATE POLICY conversation_sessions_update_policy ON conversation_sessions FOR UPDATE
          USING (
            is_admin_bypass_active()
            OR (
              user_id::text = get_tenant_setting('app.current_user_id')
              AND organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          )
          WITH CHECK (
            is_admin_bypass_active()
            OR (
              user_id::text = get_tenant_setting('app.current_user_id')
              AND organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)
    op.execute("""
        CREATE POLICY conversation_sessions_delete_policy ON conversation_sessions FOR DELETE
          USING (
            is_admin_bypass_active()
            OR (
              user_id::text = get_tenant_setting('app.current_user_id')
              AND organization_id::text = get_tenant_setting('app.current_organization_id')
            )
          );
    """)


def downgrade() -> None:
    # ── Reverse 3: Drop RLS policies ─────────────────────────────────────
    op.execute(
        "DROP POLICY IF EXISTS conversation_sessions_delete_policy ON conversation_sessions;"
    )
    op.execute(
        "DROP POLICY IF EXISTS conversation_sessions_update_policy ON conversation_sessions;"
    )
    op.execute(
        "DROP POLICY IF EXISTS conversation_sessions_insert_policy ON conversation_sessions;"
    )
    op.execute(
        "DROP POLICY IF EXISTS conversation_sessions_select_policy ON conversation_sessions;"
    )
    op.execute("ALTER TABLE conversation_sessions DISABLE ROW LEVEL SECURITY;")

    # ── Reverse 2: Drop indexes ──────────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_conversation_sessions_is_active;")
    op.execute("DROP INDEX IF EXISTS ix_conversation_sessions_organization_id;")
    op.execute("DROP INDEX IF EXISTS ix_conversation_sessions_user_id;")

    # ── Reverse 1: Drop table ────────────────────────────────────────────
    op.execute("DROP TABLE IF EXISTS conversation_sessions;")
