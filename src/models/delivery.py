"""Delivery model — proof-of-delivery records linked to fulfillments."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import DeliveryStatus, DeliveryType

if TYPE_CHECKING:
    from src.models.delivery_item import DeliveryItem
    from src.models.delivery_photo import DeliveryPhoto
    from src.models.fulfillment import Fulfillment
    from src.models.order import Order
    from src.models.organization import Organization
    from src.models.user import User
    from src.models.vendor_order import VendorOrder


class Delivery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "deliveries"

    delivery_number: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True
    )
    fulfillment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fulfillments.id", ondelete="CASCADE"),
        nullable=False,
    )
    vendor_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendor_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[DeliveryStatus] = mapped_column(
        nullable=False, server_default="PENDING"
    )

    # Dispatch info
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dispatched_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    estimated_arrival: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Delivery info
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    delivery_type: Mapped[DeliveryType | None] = mapped_column()

    # GPS coordinates
    delivery_latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 8))
    delivery_longitude: Mapped[Decimal | None] = mapped_column(Numeric(11, 8))
    gps_accuracy_meters: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))

    # Receiver info
    receiver_name: Mapped[str] = mapped_column(
        String(200), nullable=False, server_default=""
    )
    receiver_designation: Mapped[str | None] = mapped_column(String(100))
    receiver_contact: Mapped[str | None] = mapped_column(String(50))

    # Signature
    signature_s3_key: Mapped[str | None] = mapped_column(String(500))
    signature_captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # SLA
    sla_target_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sla_met: Mapped[bool | None] = mapped_column(Boolean)
    delay_reason: Mapped[str | None] = mapped_column(Text)

    # Acceptance
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    acceptance_notes: Mapped[str | None] = mapped_column(Text)

    # Dispute
    disputed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dispute_reason: Mapped[str | None] = mapped_column(Text)

    # Relationships
    fulfillment: Mapped[Fulfillment] = relationship("Fulfillment", lazy="noload")
    vendor_order: Mapped[VendorOrder] = relationship("VendorOrder", lazy="noload")
    order: Mapped[Order] = relationship("Order", lazy="noload")
    organization: Mapped[Organization] = relationship("Organization", lazy="noload")
    items: Mapped[list[DeliveryItem]] = relationship(
        "DeliveryItem", back_populates="delivery", lazy="noload", cascade="all, delete-orphan"
    )
    photos: Mapped[list[DeliveryPhoto]] = relationship(
        "DeliveryPhoto", back_populates="delivery", lazy="noload", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_deliveries_fulfillment_id", "fulfillment_id"),
        Index("ix_deliveries_order_id", "order_id"),
        Index("ix_deliveries_organization_id", "organization_id"),
        Index("ix_deliveries_status", "status"),
        Index("ix_deliveries_vendor_order_id", "vendor_order_id"),
    )
