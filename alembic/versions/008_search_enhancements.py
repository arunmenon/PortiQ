"""Search enhancements — search_synonyms table and partial indexes

Revision ID: 008
Revises: 007
Create Date: 2026-02-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create search_synonyms table
    op.create_table(
        "search_synonyms",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("term", sa.String(100), nullable=False),
        sa.Column("synonyms", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("domain", sa.String(50), server_default="maritime"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("term", "domain", name="uq_search_synonyms_term_domain"),
    )

    # 2. Add partial indexes for common filter combos on products
    op.create_index(
        "ix_products_ihm_relevant_true",
        "products",
        ["ihm_relevant"],
        postgresql_where=sa.text("ihm_relevant = true"),
    )
    op.create_index(
        "ix_products_hazmat_class_not_null",
        "products",
        ["hazmat_class"],
        postgresql_where=sa.text("hazmat_class IS NOT NULL"),
    )

    # 3. Insert maritime-specific seed synonyms
    op.execute(
        sa.text("""
            INSERT INTO search_synonyms (id, term, synonyms, domain) VALUES
            (gen_random_uuid(), 'bolt', '["fastener"]', 'maritime'),
            (gen_random_uuid(), 'ss', '["stainless steel"]', 'maritime'),
            (gen_random_uuid(), 'ppe', '["safety gear"]', 'maritime'),
            (gen_random_uuid(), 'valve', '["stopcock"]', 'maritime'),
            (gen_random_uuid(), 'rope', '["cordage"]', 'maritime'),
            (gen_random_uuid(), 'paint', '["coating"]', 'maritime'),
            (gen_random_uuid(), 'gasket', '["seal"]', 'maritime'),
            (gen_random_uuid(), 'pipe', '["tubing"]', 'maritime'),
            (gen_random_uuid(), 'pump', '["compressor"]', 'maritime'),
            (gen_random_uuid(), 'filter', '["strainer"]', 'maritime')
        """)
    )


def downgrade() -> None:
    op.drop_index("ix_products_hazmat_class_not_null", table_name="products")
    op.drop_index("ix_products_ihm_relevant_true", table_name="products")
    op.drop_table("search_synonyms")
