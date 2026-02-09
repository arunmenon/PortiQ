"""Widen impa_code to VARCHAR(10) for extension codes (EXT-XXXXXX)

Revision ID: 006
Revises: 005
Create Date: 2026-02-06

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Must drop generated column that depends on impa_code before altering its type
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS search_vector;")
    op.execute("ALTER TABLE products ALTER COLUMN impa_code TYPE VARCHAR(10);")
    # Recreate the generated tsvector column with the widened impa_code
    op.execute("""
        ALTER TABLE products ADD COLUMN search_vector tsvector
          GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(impa_code, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(issa_code, '')), 'C')
          ) STORED;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE products ALTER COLUMN impa_code TYPE VARCHAR(6);")
