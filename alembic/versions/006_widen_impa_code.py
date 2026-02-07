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
    op.execute("ALTER TABLE products ALTER COLUMN impa_code TYPE VARCHAR(10);")


def downgrade() -> None:
    op.execute("ALTER TABLE products ALTER COLUMN impa_code TYPE VARCHAR(6);")
