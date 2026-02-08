from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.quote import Quote
    from src.models.rfq_line_item import RfqLineItem


class QuoteLineItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quote_line_items"

    quote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quotes.id", ondelete="CASCADE"),
        nullable=False,
    )
    rfq_line_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rfq_line_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    lead_time_days: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    quote: Mapped[Quote] = relationship(
        "Quote", back_populates="line_items", lazy="noload"
    )
    rfq_line_item: Mapped[RfqLineItem] = relationship("RfqLineItem", lazy="noload")

    __table_args__ = (
        UniqueConstraint(
            "quote_id", "rfq_line_item_id",
            name="uq_quote_line_items_quote_rfq_line",
        ),
        CheckConstraint("unit_price >= 0", name="ck_quote_line_items_unit_price_non_negative"),
        CheckConstraint("quantity > 0", name="ck_quote_line_items_quantity_positive"),
        CheckConstraint("total_price >= 0", name="ck_quote_line_items_total_price_non_negative"),
        Index("ix_quote_line_items_quote_id", "quote_id"),
    )
