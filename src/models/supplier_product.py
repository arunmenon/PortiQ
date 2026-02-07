from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.organization import Organization
    from src.models.product import Product


class SupplierProduct(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "supplier_products"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    supplier_sku: Mapped[str | None] = mapped_column(String(100))
    manufacturer: Mapped[str | None] = mapped_column(String(255))
    brand: Mapped[str | None] = mapped_column(String(255))
    part_number: Mapped[str | None] = mapped_column(String(100))
    lead_time_days: Mapped[int | None] = mapped_column(Integer)
    min_order_quantity: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    pack_size: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    specifications: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    version: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)

    # Relationships
    product: Mapped[Product] = relationship("Product", back_populates="supplier_products")
    supplier: Mapped[Organization] = relationship("Organization", back_populates="supplier_products")
    prices: Mapped[list[SupplierProductPrice]] = relationship(
        "SupplierProductPrice", back_populates="supplier_product", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("product_id", "supplier_id", "supplier_sku", name="uq_supplier_products"),
        Index("ix_supplier_products_supplier_id", "supplier_id"),
        Index("ix_supplier_products_is_active", "is_active"),
    )


class SupplierProductPrice(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_product_prices"

    supplier_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_products.id", ondelete="CASCADE"), nullable=False
    )
    price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), server_default="USD", nullable=False)
    min_quantity: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        nullable=False,
    )

    # Relationships
    supplier_product: Mapped[SupplierProduct] = relationship("SupplierProduct", back_populates="prices")

    __table_args__ = (
        Index("ix_supplier_product_prices_supplier_product_id", "supplier_product_id"),
        Index("ix_supplier_product_prices_valid_range", "valid_from", "valid_to"),
    )
