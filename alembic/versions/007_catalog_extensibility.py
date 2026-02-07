"""Catalog extensibility — category_schemas table and GIN index on products.specifications

Revision ID: 007
Revises: 006
Create Date: 2026-02-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "category_schemas",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("schema_json", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(20), server_default="DRAFT", nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category_id", "version", name="uq_category_schemas_category_version"),
    )

    op.create_index(
        "ix_category_schemas_category_id",
        "category_schemas",
        ["category_id"],
    )

    op.create_index(
        "ix_category_schemas_status",
        "category_schemas",
        ["status"],
    )

    op.create_index(
        "ix_products_specifications_gin",
        "products",
        ["specifications"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_products_specifications_gin", table_name="products")
    op.drop_index("ix_category_schemas_status", table_name="category_schemas")
    op.drop_index("ix_category_schemas_category_id", table_name="category_schemas")
    op.drop_table("category_schemas")
