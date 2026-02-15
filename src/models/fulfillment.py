"""Fulfillment model — shipment records for vendor orders."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import DeliveryType, FulfillmentStatus

if TYPE_CHECKING:
    from src.models.fulfillment_item import FulfillmentItem
    from src.models.vendor_order import VendorOrder


class Fulfillment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fulfillments"

    fulfillment_number: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True
    )
    vendor_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendor_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[FulfillmentStatus] = mapped_column(
        nullable=False, server_default="PENDING"
    )

    # Shipping details
    carrier: Mapped[str | None] = mapped_column(String(100))
    tracking_number: Mapped[str | None] = mapped_column(String(100))
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estimated_delivery: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Delivery location
    delivery_type: Mapped[DeliveryType | None] = mapped_column()
    delivery_address: Mapped[str | None] = mapped_column(Text)
    delivery_contact: Mapped[str | None] = mapped_column(String(100))
    delivery_phone: Mapped[str | None] = mapped_column(String(20))

    # Acceptance
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_by: Mapped[str | None] = mapped_column(String(100))
    acceptance_notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    vendor_order: Mapped[VendorOrder] = relationship(
        "VendorOrder", back_populates="fulfillments", lazy="noload"
    )
    items: Mapped[list[FulfillmentItem]] = relationship(
        "FulfillmentItem", back_populates="fulfillment", lazy="noload", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_fulfillments_vendor_order_id", "vendor_order_id"),
        Index("ix_fulfillments_status", "status"),
    )
