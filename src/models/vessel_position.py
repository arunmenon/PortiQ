"""VesselPosition model — AIS position records."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import AisProvider, NavigationStatus


class VesselPosition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "vessel_positions"

    vessel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vessels.id", ondelete="CASCADE"),
        nullable=False,
    )
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    speed_knots: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    course: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    heading: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    navigation_status: Mapped[NavigationStatus] = mapped_column(
        SQLAlchemyEnum(NavigationStatus, name="navigationstatus", create_type=False),
        nullable=False,
        server_default="UNKNOWN",
    )
    source: Mapped[AisProvider] = mapped_column(
        SQLAlchemyEnum(AisProvider, name="aisprovider", create_type=False),
        nullable=False,
        server_default="VESSEL_FINDER",
    )
    signal_confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    # Relationships
    vessel = relationship("Vessel", back_populates="positions")

    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_vessel_positions_latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_vessel_positions_longitude"),
    )
