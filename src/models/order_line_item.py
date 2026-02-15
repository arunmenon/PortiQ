"""OrderLineItem model — product line items within a vendor order."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import FulfillmentLineItemStatus

if TYPE_CHECKING:
    from src.models.vendor_order import VendorOrder


class OrderLineItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "order_line_items"

    vendor_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendor_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
    )
    impa_code: Mapped[str] = mapped_column(String(6), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_fulfilled: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    quantity_accepted: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    status: Mapped[FulfillmentLineItemStatus] = mapped_column(
        nullable=False, server_default="PENDING"
    )

    # Relationships
    vendor_order: Mapped[VendorOrder] = relationship(
        "VendorOrder", back_populates="line_items", lazy="noload"
    )

    __table_args__ = (
        Index("ix_order_line_items_vendor_order_id", "vendor_order_id"),
        Index("ix_order_line_items_product_id", "product_id", postgresql_where="product_id IS NOT NULL"),
    )
