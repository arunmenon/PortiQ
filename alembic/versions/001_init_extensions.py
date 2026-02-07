"""Initialize PostgreSQL extensions

Revision ID: 001
Revises: None
Create Date: 2026-02-06

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "btree_gin";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "ltree";')


def downgrade() -> None:
    op.execute('DROP EXTENSION IF EXISTS "ltree";')
    op.execute('DROP EXTENSION IF EXISTS "vector";')
    op.execute('DROP EXTENSION IF EXISTS "btree_gin";')
    op.execute('DROP EXTENSION IF EXISTS "pg_trgm";')
    op.execute('DROP EXTENSION IF EXISTS "pgcrypto";')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp";')
