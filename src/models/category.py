from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, SmallInteger, String, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import CategoryStatus

if TYPE_CHECKING:
    from src.models.product import Product


class Category(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "categories"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    impa_prefix: Mapped[str | None] = mapped_column(String(2))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)  # ltree stored as string, cast via migration
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    attribute_schema: Mapped[dict | None] = mapped_column(JSONB)
    ihm_category: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    icon: Mapped[str | None] = mapped_column(String(100))
    display_order: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    status: Mapped[CategoryStatus] = mapped_column(server_default="ACTIVE", nullable=False)

    # Relationships
    products: Mapped[list[Product]] = relationship("Product", back_populates="category")
    product_category_tags: Mapped[list] = relationship("ProductCategoryTag", back_populates="category")
    unit_conversions: Mapped[list] = relationship("UnitConversion", back_populates="category")
    ancestors: Mapped[list[CategoryClosure]] = relationship(
        "CategoryClosure", foreign_keys="CategoryClosure.descendant_id", back_populates="descendant"
    )
    descendants: Mapped[list[CategoryClosure]] = relationship(
        "CategoryClosure", foreign_keys="CategoryClosure.ancestor_id", back_populates="ancestor"
    )
    impa_mappings: Mapped[list] = relationship("ImpaCategoryMapping", back_populates="internal_category")
    issa_mappings: Mapped[list] = relationship("IssaCategoryMapping", back_populates="internal_category")

    __table_args__ = (
        Index("ix_categories_impa_prefix", "impa_prefix"),
        Index("ix_categories_level", "level"),
        Index("ix_categories_status", "status"),
    )


class CategoryClosure(Base):
    __tablename__ = "category_closures"

    ancestor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )
    descendant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )
    depth: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # Relationships
    ancestor: Mapped[Category] = relationship(
        "Category", foreign_keys=[ancestor_id], back_populates="descendants"
    )
    descendant: Mapped[Category] = relationship(
        "Category", foreign_keys=[descendant_id], back_populates="ancestors"
    )

    __table_args__ = (
        Index("ix_category_closures_descendant_id", "descendant_id"),
    )
