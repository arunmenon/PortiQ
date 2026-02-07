"""Vessel model — core vessel registry."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, String
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import VesselStatus, VesselType


class Vessel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "vessels"

    imo_number: Mapped[str] = mapped_column(String(7), unique=True, nullable=False)
    mmsi: Mapped[str | None] = mapped_column(String(9))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    vessel_type: Mapped[VesselType] = mapped_column(
        SQLAlchemyEnum(VesselType, name="vesseltype", create_type=False),
        nullable=False,
        server_default="OTHER",
    )
    status: Mapped[VesselStatus] = mapped_column(
        SQLAlchemyEnum(VesselStatus, name="vesselstatus", create_type=False),
        nullable=False,
        server_default="ACTIVE",
    )
    flag_state: Mapped[str | None] = mapped_column(String(3))  # ISO alpha-3
    gross_tonnage: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    deadweight_tonnage: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    length_overall_m: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    beam_m: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    year_built: Mapped[int | None] = mapped_column(Integer)
    crew_size: Mapped[int | None] = mapped_column(Integer)
    owner_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
    )
    manager_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
    )
    last_known_port: Mapped[str | None] = mapped_column(String(10))  # UN/LOCODE
    last_supply_date: Mapped[datetime | None] = mapped_column()
    metadata_extra: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    # Relationships
    positions = relationship("VesselPosition", back_populates="vessel", lazy="noload")
    port_calls = relationship("PortCall", back_populates="vessel", lazy="noload")

    __table_args__ = (
        CheckConstraint("imo_number ~ '^[0-9]{7}$'", name="ck_vessels_imo_format"),
        CheckConstraint("mmsi IS NULL OR mmsi ~ '^[0-9]{9}$'", name="ck_vessels_mmsi_format"),
    )
