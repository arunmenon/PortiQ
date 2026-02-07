"""PortCall model — vessel port call records."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import AisProvider, PortCallStatus


class PortCall(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "port_calls"

    vessel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vessels.id", ondelete="CASCADE"),
        nullable=False,
    )
    port_code: Mapped[str] = mapped_column(String(10), nullable=False)
    port_name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[PortCallStatus] = mapped_column(
        SQLAlchemyEnum(PortCallStatus, name="portcallstatus", create_type=False),
        nullable=False,
        server_default="APPROACHING",
    )
    eta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ata: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    atd: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    berth: Mapped[str | None] = mapped_column(String(100))
    pilot_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    distance_nm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    eta_confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    source: Mapped[AisProvider] = mapped_column(
        SQLAlchemyEnum(AisProvider, name="aisprovider", create_type=False),
        nullable=False,
        server_default="VESSEL_FINDER",
    )
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    # Relationships
    vessel = relationship("Vessel", back_populates="port_calls")
