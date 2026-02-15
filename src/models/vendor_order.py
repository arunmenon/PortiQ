"""VendorOrder model — per-supplier sub-order within an order."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import VendorOrderStatus

if TYPE_CHECKING:
    from src.models.fulfillment import Fulfillment
    from src.models.order import Order
    from src.models.order_line_item import OrderLineItem
    from src.models.organization import Organization


class VendorOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vendor_orders"

    vendor_order_number: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[VendorOrderStatus] = mapped_column(
        nullable=False, server_default="PENDING_CONFIRMATION"
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    commission_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    commission_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))

    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estimated_ready_date: Mapped[date | None] = mapped_column(Date)

    # Relationships
    order: Mapped[Order] = relationship(
        "Order", back_populates="vendor_orders", lazy="noload"
    )
    supplier: Mapped[Organization] = relationship(
        "Organization", foreign_keys=[supplier_id], lazy="noload"
    )
    line_items: Mapped[list[OrderLineItem]] = relationship(
        "OrderLineItem", back_populates="vendor_order", lazy="noload", cascade="all, delete-orphan"
    )
    fulfillments: Mapped[list[Fulfillment]] = relationship(
        "Fulfillment", back_populates="vendor_order", lazy="noload", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_vendor_orders_order_id", "order_id"),
        Index("ix_vendor_orders_supplier_id", "supplier_id"),
        Index("ix_vendor_orders_status", "status"),
    )
