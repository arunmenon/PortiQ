"""DeliverySlaConfig model — SLA configuration per buyer-supplier pair."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.organization import Organization


class DeliverySlaConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "delivery_sla_configs"

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
    port_code: Mapped[str | None] = mapped_column(String(10))

    # SLA windows
    delivery_window_hours: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="24"
    )
    max_delay_hours: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="4"
    )

    # Penalties
    late_delivery_penalty_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), server_default="0"
    )
    no_show_penalty_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), server_default="0"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )

    # Relationships
    buyer_organization: Mapped[Organization] = relationship(
        "Organization", foreign_keys=[buyer_org_id], lazy="noload"
    )
    supplier_organization: Mapped[Organization] = relationship(
        "Organization", foreign_keys=[supplier_org_id], lazy="noload"
    )

    __table_args__ = (
        UniqueConstraint("buyer_org_id", "supplier_org_id", "port_code", name="uq_delivery_sla_buyer_supplier_port"),
    )
