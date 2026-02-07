from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, UUIDPrimaryKeyMixin
from src.models.enums import UnitType

if TYPE_CHECKING:
    from src.models.category import Category
    from src.models.product import Product


class UnitOfMeasure(Base):
    __tablename__ = "units_of_measure"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    unit_type: Mapped[UnitType] = mapped_column(nullable=False)
    base_unit: Mapped[str | None] = mapped_column(String(10))
    display_order: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)


class UnitConversion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "unit_conversions"

    from_unit: Mapped[str] = mapped_column(String(10), nullable=False)
    to_unit: Mapped[str] = mapped_column(String(10), nullable=False)
    conversion_factor: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id")
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id")
    )

    # Relationships
    category: Mapped[Category | None] = relationship("Category", back_populates="unit_conversions")
    product: Mapped[Product | None] = relationship("Product", back_populates="unit_conversions")

    __table_args__ = (
        UniqueConstraint("from_unit", "to_unit", "category_id", "product_id", name="uq_unit_conversions"),
    )
