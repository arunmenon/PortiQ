"""DeliveryItem model — line-item level delivery verification."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import DeliveryItemStatus

if TYPE_CHECKING:
    from src.models.delivery import Delivery
    from src.models.fulfillment_item import FulfillmentItem
    from src.models.order_line_item import OrderLineItem


class DeliveryItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "delivery_items"

    delivery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deliveries.id", ondelete="CASCADE"),
        nullable=False,
    )
    fulfillment_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fulfillment_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    order_line_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_line_items.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Quantities
    quantity_expected: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_delivered: Mapped[int | None] = mapped_column(Integer)
    quantity_accepted: Mapped[int | None] = mapped_column(Integer)
    quantity_rejected: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )

    # Verification
    status: Mapped[DeliveryItemStatus] = mapped_column(
        nullable=False, server_default="PENDING"
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    delivery: Mapped[Delivery] = relationship(
        "Delivery", back_populates="items", lazy="noload"
    )
    fulfillment_item: Mapped[FulfillmentItem] = relationship(
        "FulfillmentItem", lazy="noload"
    )
    order_line_item: Mapped[OrderLineItem] = relationship(
        "OrderLineItem", lazy="noload"
    )

    __table_args__ = (
        Index("ix_delivery_items_delivery_id", "delivery_id"),
        Index("ix_delivery_items_fulfillment_item_id", "fulfillment_item_id"),
    )
