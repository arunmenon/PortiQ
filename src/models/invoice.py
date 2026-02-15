"""Invoice model — auto-generated from accepted deliveries."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import InvoiceStatus

if TYPE_CHECKING:
    from src.models.invoice_line_item import InvoiceLineItem
    from src.models.order import Order
    from src.models.organization import Organization
    from src.models.settlement_period import SettlementPeriod
    from src.models.vendor_order import VendorOrder


class Invoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "invoices"

    invoice_number: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Links
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    vendor_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendor_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    delivery_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deliveries.id", ondelete="SET NULL"),
    )
    settlement_period_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("settlement_periods.id", ondelete="SET NULL"),
    )

    # Parties
    buyer_org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    supplier_org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Status
    status: Mapped[InvoiceStatus] = mapped_column(
        nullable=False, server_default="DRAFT"
    )

    # Amounts
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, server_default="0"
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, server_default="0"
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, server_default="0"
    )
    credit_adjustment: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, server_default="0"
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="USD"
    )

    # References
    buyer_po_number: Mapped[str | None] = mapped_column(String(100))
    supplier_invoice_ref: Mapped[str | None] = mapped_column(String(100))

    # Dates
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_reference: Mapped[str | None] = mapped_column(String(200))

    # Notes
    notes: Mapped[str | None] = mapped_column(Text)
    internal_notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    organization: Mapped[Organization] = relationship(
        "Organization", foreign_keys=[organization_id], lazy="noload"
    )
    order: Mapped[Order] = relationship("Order", lazy="noload")
    vendor_order: Mapped[VendorOrder] = relationship("VendorOrder", lazy="noload")
    buyer_organization: Mapped[Organization] = relationship(
        "Organization", foreign_keys=[buyer_org_id], lazy="noload"
    )
    supplier_organization: Mapped[Organization] = relationship(
        "Organization", foreign_keys=[supplier_org_id], lazy="noload"
    )
    settlement_period: Mapped[SettlementPeriod | None] = relationship(
        "SettlementPeriod", lazy="noload"
    )
    line_items: Mapped[list[InvoiceLineItem]] = relationship(
        "InvoiceLineItem",
        back_populates="invoice",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_invoices_organization_id", "organization_id"),
        Index("ix_invoices_order_id", "order_id"),
        Index("ix_invoices_buyer_org_id", "buyer_org_id"),
        Index("ix_invoices_supplier_org_id", "supplier_org_id"),
        Index("ix_invoices_status", "status"),
        Index(
            "ix_invoices_settlement_period_id",
            "settlement_period_id",
            postgresql_where="settlement_period_id IS NOT NULL",
        ),
    )
