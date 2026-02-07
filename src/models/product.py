from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Computed, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.category import Category
    from src.models.supplier_product import SupplierProduct
    from src.models.translation import ProductTranslation
    from src.models.unit import UnitConversion


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "products"

    impa_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    issa_code: Mapped[str | None] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(String)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False
    )
    unit_of_measure: Mapped[str] = mapped_column(String(20), nullable=False)
    ihm_relevant: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    hazmat_class: Mapped[str | None] = mapped_column(String(20))
    specifications: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    embedding = mapped_column(Vector(1536), nullable=True)
    version: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(
        String(50), server_default="text-embedding-ada-002"
    )
    embedding_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('english', coalesce(name, '')), 'A') || "
            "setweight(to_tsvector('english', coalesce(impa_code, '')), 'A') || "
            "setweight(to_tsvector('english', coalesce(description, '')), 'B') || "
            "setweight(to_tsvector('english', coalesce(issa_code, '')), 'C')",
            persisted=True,
        ),
        nullable=True,
    )

    # Relationships
    category: Mapped[Category] = relationship("Category", back_populates="products")
    supplier_products: Mapped[list[SupplierProduct]] = relationship(
        "SupplierProduct", back_populates="product", cascade="all, delete-orphan"
    )
    translations: Mapped[list[ProductTranslation]] = relationship(
        "ProductTranslation", back_populates="product", cascade="all, delete-orphan"
    )
    product_category_tags: Mapped[list] = relationship(
        "ProductCategoryTag", back_populates="product", cascade="all, delete-orphan"
    )
    unit_conversions: Mapped[list[UnitConversion]] = relationship(
        "UnitConversion", back_populates="product", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_products_category_id", "category_id"),
        Index("ix_products_issa_code", "issa_code"),
    )
