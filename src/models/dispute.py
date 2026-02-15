"""Dispute model — dispute resolution records."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import (
    DisputePriority,
    DisputeResolutionType,
    DisputeStatus,
    DisputeType,
)

if TYPE_CHECKING:
    from src.models.delivery import Delivery
    from src.models.delivery_item import DeliveryItem
    from src.models.dispute_comment import DisputeComment
    from src.models.dispute_transition import DisputeTransition
    from src.models.order import Order
    from src.models.organization import Organization
    from src.models.user import User
    from src.models.vendor_order import VendorOrder


class Dispute(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "disputes"

    dispute_number: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Links
    delivery_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deliveries.id", ondelete="SET NULL")
    )
    delivery_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("delivery_items.id", ondelete="SET NULL")
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    vendor_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendor_orders.id", ondelete="SET NULL")
    )

    # Parties
    raised_by_org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    raised_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    supplier_org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    # Dispute details
    dispute_type: Mapped[DisputeType] = mapped_column(nullable=False)
    status: Mapped[DisputeStatus] = mapped_column(
        nullable=False, server_default="OPEN"
    )
    priority: Mapped[DisputePriority] = mapped_column(
        nullable=False, server_default="MEDIUM"
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Financial
    disputed_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="USD"
    )
    resolution_type: Mapped[DisputeResolutionType | None] = mapped_column()
    resolution_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    resolution_notes: Mapped[str | None] = mapped_column(Text)

    # SLA
    response_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sla_breached: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    # Timestamps
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    escalated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    organization: Mapped[Organization] = relationship(
        "Organization", foreign_keys=[organization_id], lazy="noload"
    )
    raised_by_org: Mapped[Organization] = relationship(
        "Organization", foreign_keys=[raised_by_org_id], lazy="noload"
    )
    supplier_org: Mapped[Organization] = relationship(
        "Organization", foreign_keys=[supplier_org_id], lazy="noload"
    )
    raised_by_user: Mapped[User] = relationship(
        "User", foreign_keys=[raised_by_user_id], lazy="noload"
    )
    assigned_reviewer: Mapped[User | None] = relationship(
        "User", foreign_keys=[assigned_reviewer_id], lazy="noload"
    )
    order: Mapped[Order] = relationship("Order", lazy="noload")
    vendor_order: Mapped[VendorOrder | None] = relationship("VendorOrder", lazy="noload")
    delivery: Mapped[Delivery | None] = relationship("Delivery", lazy="noload")
    delivery_item: Mapped[DeliveryItem | None] = relationship("DeliveryItem", lazy="noload")
    comments: Mapped[list[DisputeComment]] = relationship(
        "DisputeComment", back_populates="dispute", lazy="noload", cascade="all, delete-orphan"
    )
    transitions: Mapped[list[DisputeTransition]] = relationship(
        "DisputeTransition", back_populates="dispute", lazy="noload", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_disputes_organization_id", "organization_id"),
        Index("ix_disputes_order_id", "order_id"),
        Index("ix_disputes_delivery_id", "delivery_id", postgresql_where="delivery_id IS NOT NULL"),
        Index("ix_disputes_status", "status"),
        Index("ix_disputes_supplier_org_id", "supplier_org_id"),
    )
