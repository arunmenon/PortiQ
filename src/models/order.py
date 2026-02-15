"""Order model — aggregate order from awarded RFQ."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import OrderStatus

if TYPE_CHECKING:
    from src.models.organization import Organization
    from src.models.rfq import Rfq
    from src.models.vendor_order import VendorOrder


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "orders"

    order_number: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True
    )
    rfq_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="SET NULL"),
    )
    buyer_org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[OrderStatus] = mapped_column(
        nullable=False, server_default="PENDING_PAYMENT"
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="USD"
    )

    # Delivery details
    delivery_port: Mapped[str | None] = mapped_column(String(10))
    vessel_imo: Mapped[str | None] = mapped_column(String(10))
    vessel_name: Mapped[str | None] = mapped_column(String(100))
    requested_delivery_date: Mapped[date | None] = mapped_column(Date)

    # Payment
    payment_status: Mapped[str | None] = mapped_column(String(20))
    payment_method: Mapped[str | None] = mapped_column(String(30))
    payment_reference: Mapped[str | None] = mapped_column(String(100))

    metadata_extra: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )

    # Relationships
    buyer_organization: Mapped[Organization] = relationship(
        "Organization", foreign_keys=[buyer_org_id], lazy="noload"
    )
    rfq: Mapped[Rfq | None] = relationship("Rfq", lazy="noload")
    vendor_orders: Mapped[list[VendorOrder]] = relationship(
        "VendorOrder", back_populates="order", lazy="noload", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_orders_buyer_org_id", "buyer_org_id"),
        Index("ix_orders_status", "status"),
        Index("ix_orders_rfq_id", "rfq_id", postgresql_where="rfq_id IS NOT NULL"),
        Index("ix_orders_order_number", "order_number"),
    )
