from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, UUIDPrimaryKeyMixin
from src.models.enums import TagSource, TagType


class ProductCategoryTag(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "product_category_tags"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False
    )
    tag_type: Mapped[TagType] = mapped_column(nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2), server_default="1.0", nullable=False)
    created_by: Mapped[TagSource] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    product = relationship("Product", back_populates="product_category_tags")
    category = relationship("Category", back_populates="product_category_tags")

    __table_args__ = (
        UniqueConstraint("product_id", "category_id", "tag_type", name="uq_product_category_tags"),
        Index("ix_product_category_tags_category_id", "category_id"),
    )
