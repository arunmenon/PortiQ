"""Create schema - all 14 tables

Revision ID: 002
Revises: 001
Create Date: 2026-02-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# --- Enum types ---
organization_type_enum = sa.Enum(
    "BUYER", "SUPPLIER", "BOTH", name="organizationtype", create_type=True
)
user_role_enum = sa.Enum(
    "OWNER", "ADMIN", "MEMBER", "VIEWER", name="userrole", create_type=True
)
category_status_enum = sa.Enum(
    "ACTIVE", "DEPRECATED", "PENDING_MIGRATION", "ARCHIVED",
    name="categorystatus", create_type=True,
)
unit_type_enum = sa.Enum(
    "QUANTITY", "VOLUME", "WEIGHT", "LENGTH", name="unittype", create_type=True
)
tag_type_enum = sa.Enum(
    "RELATED", "ALSO_IN", "SUBSTITUTE", "ACCESSORY", name="tagtype", create_type=True
)
tag_source_enum = sa.Enum(
    "MANUAL", "ML_MODEL", "IMPA_MAPPING", name="tagsource", create_type=True
)


def upgrade() -> None:
    # Create enum types first
    organization_type_enum.create(op.get_bind(), checkfirst=True)
    user_role_enum.create(op.get_bind(), checkfirst=True)
    category_status_enum.create(op.get_bind(), checkfirst=True)
    unit_type_enum.create(op.get_bind(), checkfirst=True)
    tag_type_enum.create(op.get_bind(), checkfirst=True)
    tag_source_enum.create(op.get_bind(), checkfirst=True)

    # 1. organizations
    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", organization_type_enum, nullable=False),
        sa.Column("registration_number", sa.String(100), nullable=True),
        sa.Column("address", JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 2. users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", user_role_enum, server_default="MEMBER", nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])

    # 3. categories
    op.create_table(
        "categories",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("impa_prefix", sa.String(2), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String, nullable=True),
        sa.Column("path", sa.String(1024), nullable=False),
        sa.Column("level", sa.SmallInteger, nullable=False),
        sa.Column("attribute_schema", JSONB, nullable=True),
        sa.Column("ihm_category", sa.Boolean, server_default="false", nullable=False),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("display_order", sa.Integer, server_default="0", nullable=False),
        sa.Column("status", category_status_enum, server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_categories_impa_prefix", "categories", ["impa_prefix"])
    op.create_index("ix_categories_level", "categories", ["level"])
    op.create_index("ix_categories_status", "categories", ["status"])

    # 4. category_closures
    op.create_table(
        "category_closures",
        sa.Column("ancestor_id", UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("descendant_id", UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("depth", sa.SmallInteger, nullable=False),
    )
    op.create_index("ix_category_closures_descendant_id", "category_closures", ["descendant_id"])

    # 5. products (embedding column added in migration 003)
    op.create_table(
        "products",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("impa_code", sa.String(6), unique=True, nullable=False),
        sa.Column("issa_code", sa.String(20), nullable=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("description", sa.String, nullable=True),
        sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("unit_of_measure", sa.String(20), nullable=False),
        sa.Column("ihm_relevant", sa.Boolean, server_default="false", nullable=False),
        sa.Column("hazmat_class", sa.String(20), nullable=True),
        sa.Column("specifications", JSONB, server_default="{}", nullable=False),
        sa.Column("version", sa.Integer, server_default="1", nullable=False),
        sa.Column("embedding_model", sa.String(50), server_default="text-embedding-ada-002", nullable=True),
        sa.Column("embedding_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_products_category_id", "products", ["category_id"])
    op.create_index("ix_products_issa_code", "products", ["issa_code"])

    # 6. supplier_products
    op.create_table(
        "supplier_products",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("supplier_sku", sa.String(100), nullable=True),
        sa.Column("manufacturer", sa.String(255), nullable=True),
        sa.Column("brand", sa.String(255), nullable=True),
        sa.Column("part_number", sa.String(100), nullable=True),
        sa.Column("lead_time_days", sa.Integer, nullable=True),
        sa.Column("min_order_quantity", sa.Integer, server_default="1", nullable=False),
        sa.Column("pack_size", sa.Integer, server_default="1", nullable=False),
        sa.Column("specifications", JSONB, server_default="{}", nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("version", sa.Integer, server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("product_id", "supplier_id", "supplier_sku", name="uq_supplier_products"),
    )
    op.create_index("ix_supplier_products_supplier_id", "supplier_products", ["supplier_id"])
    op.create_index("ix_supplier_products_is_active", "supplier_products", ["is_active"])

    # 7. supplier_product_prices
    op.create_table(
        "supplier_product_prices",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("supplier_product_id", UUID(as_uuid=True), sa.ForeignKey("supplier_products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("price", sa.Numeric(12, 4), nullable=False),
        sa.Column("currency", sa.String(3), server_default="USD", nullable=False),
        sa.Column("min_quantity", sa.Integer, server_default="1", nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_supplier_product_prices_supplier_product_id", "supplier_product_prices", ["supplier_product_id"])
    op.create_index("ix_supplier_product_prices_valid_range", "supplier_product_prices", ["valid_from", "valid_to"])

    # 8. units_of_measure
    op.create_table(
        "units_of_measure",
        sa.Column("code", sa.String(10), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("unit_type", unit_type_enum, nullable=False),
        sa.Column("base_unit", sa.String(10), nullable=True),
        sa.Column("display_order", sa.Integer, server_default="0", nullable=False),
    )

    # 9. unit_conversions
    op.create_table(
        "unit_conversions",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("from_unit", sa.String(10), nullable=False),
        sa.Column("to_unit", sa.String(10), nullable=False),
        sa.Column("conversion_factor", sa.Numeric(18, 8), nullable=False),
        sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        sa.UniqueConstraint("from_unit", "to_unit", "category_id", "product_id", name="uq_unit_conversions"),
    )

    # 10. product_translations
    op.create_table(
        "product_translations",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("description", sa.String, nullable=True),
        sa.Column("search_keywords", sa.ARRAY(sa.String), server_default="{}", nullable=False),
        sa.UniqueConstraint("product_id", "locale", name="uq_product_translations"),
    )
    op.create_index("ix_product_translations_locale", "product_translations", ["locale"])

    # 11. product_audit_log
    op.create_table(
        "product_audit_log",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("operation", sa.String(20), nullable=False),
        sa.Column("changed_fields", JSONB, nullable=True),
        sa.Column("changed_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("change_reason", sa.String, nullable=True),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_product_audit_log_entity", "product_audit_log", ["entity_type", "entity_id"])
    op.create_index("ix_product_audit_log_created_at", "product_audit_log", ["created_at"])

    # 12. product_category_tags
    op.create_table(
        "product_category_tags",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("tag_type", tag_type_enum, nullable=False),
        sa.Column("confidence", sa.Numeric(3, 2), server_default="1.0", nullable=False),
        sa.Column("created_by", tag_source_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("product_id", "category_id", "tag_type", name="uq_product_category_tags"),
    )
    op.create_index("ix_product_category_tags_category_id", "product_category_tags", ["category_id"])

    # 13. impa_category_mappings
    op.create_table(
        "impa_category_mappings",
        sa.Column("impa_prefix", sa.String(2), primary_key=True),
        sa.Column("impa_category_name", sa.String(255), nullable=False),
        sa.Column("internal_category_id", UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("mapping_confidence", sa.String(20), server_default="EXACT", nullable=False),
        sa.Column("notes", sa.String, nullable=True),
        sa.Column("last_verified", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )

    # 14. issa_category_mappings
    op.create_table(
        "issa_category_mappings",
        sa.Column("issa_prefix", sa.String(2), primary_key=True),
        sa.Column("issa_category_name", sa.String(255), nullable=False),
        sa.Column("internal_category_id", UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("impa_equivalent", sa.String(2), nullable=True),
        sa.Column("mapping_confidence", sa.String(20), server_default="EXACT", nullable=False),
        sa.Column("notes", sa.String, nullable=True),
        sa.Column("last_verified", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("issa_category_mappings")
    op.drop_table("impa_category_mappings")
    op.drop_table("product_category_tags")
    op.drop_table("product_audit_log")
    op.drop_table("product_translations")
    op.drop_table("unit_conversions")
    op.drop_table("units_of_measure")
    op.drop_table("supplier_product_prices")
    op.drop_table("supplier_products")
    op.drop_table("products")
    op.drop_table("category_closures")
    op.drop_table("categories")
    op.drop_table("users")
    op.drop_table("organizations")

    tag_source_enum.drop(op.get_bind(), checkfirst=True)
    tag_type_enum.drop(op.get_bind(), checkfirst=True)
    unit_type_enum.drop(op.get_bind(), checkfirst=True)
    category_status_enum.drop(op.get_bind(), checkfirst=True)
    user_role_enum.drop(op.get_bind(), checkfirst=True)
    organization_type_enum.drop(op.get_bind(), checkfirst=True)
