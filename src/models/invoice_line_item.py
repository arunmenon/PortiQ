"""InvoiceLineItem model — line items from accepted delivery items."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, UUIDPrimaryKeyMixin
from sqlalchemy import func

if TYPE_CHECKING:
    from src.models.invoice import Invoice


class InvoiceLineItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "invoice_line_items"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    order_line_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_line_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    delivery_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("delivery_items.id", ondelete="SET NULL"),
    )
    dispute_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("disputes.id", ondelete="SET NULL"),
    )

    # Product info (denormalized for invoice record)
    impa_code: Mapped[str | None] = mapped_column(String(6))
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Quantities
    quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_delivered: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_accepted: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_rejected: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )

    # Pricing
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    credit_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, server_default="0"
    )
    line_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)

    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    invoice: Mapped[Invoice] = relationship(
        "Invoice", back_populates="line_items", lazy="noload"
    )

    __table_args__ = (
        Index("ix_invoice_line_items_invoice_id", "invoice_id"),
        Index(
            "ix_invoice_line_items_order_line_item_id",
            "order_line_item_id",
        ),
    )
