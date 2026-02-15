"""DeliveryPhoto model — photo evidence for deliveries."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, UUIDPrimaryKeyMixin
from src.models.enums import DeliveryPhotoType

if TYPE_CHECKING:
    from src.models.delivery import Delivery
    from src.models.delivery_item import DeliveryItem
    from src.models.user import User


class DeliveryPhoto(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "delivery_photos"

    delivery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deliveries.id", ondelete="CASCADE"),
        nullable=False,
    )
    delivery_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("delivery_items.id", ondelete="SET NULL"),
    )

    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    s3_bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="image/jpeg"
    )
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)

    photo_type: Mapped[DeliveryPhotoType] = mapped_column(
        nullable=False, server_default="DELIVERY"
    )
    caption: Mapped[str | None] = mapped_column(Text)

    # Photo metadata
    taken_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 8))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(11, 8))

    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    # Relationships
    delivery: Mapped[Delivery] = relationship(
        "Delivery", back_populates="photos", lazy="noload"
    )
    delivery_item: Mapped[DeliveryItem | None] = relationship(
        "DeliveryItem", lazy="noload"
    )

    __table_args__ = (
        Index("ix_delivery_photos_delivery_id", "delivery_id"),
    )
