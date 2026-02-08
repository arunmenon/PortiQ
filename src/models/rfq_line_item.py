from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.product import Product
    from src.models.rfq import Rfq


class RfqLineItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rfq_line_items"

    rfq_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
    )
    impa_code: Mapped[str | None] = mapped_column(String(10))
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(20), nullable=False)
    specifications: Mapped[dict | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    rfq: Mapped[Rfq] = relationship("Rfq", back_populates="line_items", lazy="noload")
    product: Mapped[Product | None] = relationship("Product", lazy="noload")

    __table_args__ = (
        UniqueConstraint("rfq_id", "line_number", name="uq_rfq_line_items_rfq_line"),
        CheckConstraint("quantity > 0", name="ck_rfq_line_items_quantity_positive"),
        Index("ix_rfq_line_items_rfq_id", "rfq_id"),
    )
