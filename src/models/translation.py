from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.product import Product


class ProductTranslation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "product_translations"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    locale: Mapped[str] = mapped_column(String(5), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(String)
    search_keywords: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, server_default="{}")

    # Relationships
    product: Mapped[Product] = relationship("Product", back_populates="translations")

    __table_args__ = (
        UniqueConstraint("product_id", "locale", name="uq_product_translations"),
        Index("ix_product_translations_locale", "locale"),
    )
