"""Intelligence materialized views

Revision ID: 013
Revises: 012
Create Date: 2026-02-08

Creates: mv_price_benchmarks, mv_supplier_scores (materialized views)
Indexes: unique indexes for CONCURRENTLY refresh support
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Create mv_price_benchmarks ──────────────────────────────────────
    op.execute("""
        CREATE MATERIALIZED VIEW mv_price_benchmarks AS
        SELECT
            rli.impa_code,
            r.delivery_port,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY qli.unit_price) AS p25,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY qli.unit_price) AS p50,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY qli.unit_price) AS p75,
            COUNT(DISTINCT q.id) AS quote_count,
            r.currency,
            DATE_TRUNC('month', q.submitted_at) AS period_month
        FROM quote_line_items qli
        JOIN quotes q ON qli.quote_id = q.id
        JOIN rfq_line_items rli ON qli.rfq_line_item_id = rli.id
        JOIN rfqs r ON rli.rfq_id = r.id
        WHERE q.status IN ('SUBMITTED', 'AWARDED')
          AND q.submitted_at >= NOW() - INTERVAL '365 days'
          AND rli.impa_code IS NOT NULL
        GROUP BY rli.impa_code, r.delivery_port, r.currency,
                 DATE_TRUNC('month', q.submitted_at)
    """)

    # Unique index required for REFRESH MATERIALIZED VIEW CONCURRENTLY
    op.execute("""
        CREATE UNIQUE INDEX uix_mv_price_benchmarks_key
        ON mv_price_benchmarks (impa_code, delivery_port, currency, period_month)
    """)

    # ── 2. Create mv_supplier_scores ───────────────────────────────────────
    op.execute("""
        CREATE MATERIALIZED VIEW mv_supplier_scores AS
        SELECT
            sp.organization_id AS supplier_id,
            sp.tier,
            o.name AS organization_name,
            COUNT(DISTINCT q.id) AS total_quotes,
            COUNT(DISTINCT CASE WHEN q.status = 'AWARDED' THEN q.id END) AS won_quotes,
            AVG(
                EXTRACT(EPOCH FROM (q.submitted_at - ri.invited_at)) / 86400
            ) AS avg_response_days
        FROM supplier_profiles sp
        JOIN organizations o ON sp.organization_id = o.id
        LEFT JOIN rfq_invitations ri
            ON ri.supplier_organization_id = sp.organization_id
        LEFT JOIN quotes q
            ON q.rfq_id = ri.rfq_id
            AND q.supplier_organization_id = sp.organization_id
        WHERE sp.onboarding_status = 'APPROVED'
        GROUP BY sp.organization_id, sp.tier, o.name
    """)

    # Unique index required for REFRESH MATERIALIZED VIEW CONCURRENTLY
    op.execute("""
        CREATE UNIQUE INDEX uix_mv_supplier_scores_supplier_id
        ON mv_supplier_scores (supplier_id)
    """)


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_supplier_scores CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_price_benchmarks CASCADE")
