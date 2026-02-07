"""Add tsvector generated column and search indexes

Revision ID: 005
Revises: 004
Create Date: 2026-02-06

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Generated tsvector column — PostgreSQL maintains it automatically on
    # INSERT/UPDATE, so no trigger or sync logic is needed.
    op.execute("""
        ALTER TABLE products ADD COLUMN IF NOT EXISTS search_vector tsvector
          GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(impa_code, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(issa_code, '')), 'C')
          ) STORED;
    """)

    # GIN index on the generated tsvector for fast full-text search
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_search_vector
          ON products USING gin (search_vector);
    """)

    # Trigram index on description (name already has idx_products_name_trgm
    # from migration 003)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_description_trgm
          ON products USING gin (description gin_trgm_ops);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_products_description_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_products_search_vector;")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS search_vector;")
