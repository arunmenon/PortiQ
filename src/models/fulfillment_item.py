"""FulfillmentItem model — line items within a fulfillment shipment."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import FulfillmentLineItemStatus

if TYPE_CHECKING:
    from src.models.fulfillment import Fulfillment
    from src.models.order_line_item import OrderLineItem


class FulfillmentItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fulfillment_items"

    fulfillment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fulfillments.id", ondelete="CASCADE"),
        nullable=False,
    )
    order_line_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_line_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[FulfillmentLineItemStatus] = mapped_column(
        nullable=False, server_default="PENDING"
    )
    quantity_shipped: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_delivered: Mapped[int | None] = mapped_column(Integer)
    quantity_accepted: Mapped[int | None] = mapped_column(Integer)
    quantity_rejected: Mapped[int | None] = mapped_column(Integer)

    rejection_reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    fulfillment: Mapped[Fulfillment] = relationship(
        "Fulfillment", back_populates="items", lazy="noload"
    )
    order_line_item: Mapped[OrderLineItem] = relationship(
        "OrderLineItem", lazy="noload"
    )

    __table_args__ = (
        Index("ix_fulfillment_items_fulfillment_id", "fulfillment_id"),
        Index("ix_fulfillment_items_order_line_item_id", "order_line_item_id"),
    )
