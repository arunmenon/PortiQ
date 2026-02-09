"""TCO Calculation model — stores scored results per RFQ."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import TcoCalculationStatus

if TYPE_CHECKING:
    from src.models.rfq import Rfq
    from src.models.tco_configuration import TcoConfiguration


class TcoCalculation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tco_calculations"

    rfq_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="CASCADE"),
        nullable=False,
    )
    configuration_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tco_configurations.id", ondelete="SET NULL"),
    )
    weights_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[TcoCalculationStatus] = mapped_column(
        nullable=False, server_default="PENDING"
    )
    results: Mapped[dict | None] = mapped_column(JSONB)
    split_order_result: Mapped[dict | None] = mapped_column(JSONB)
    base_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="USD"
    )
    exchange_rates: Mapped[dict | None] = mapped_column(JSONB)
    missing_data_strategy: Mapped[str | None] = mapped_column(String(20))

    # Relationships
    rfq: Mapped[Rfq] = relationship("Rfq", lazy="noload")
    configuration: Mapped[TcoConfiguration | None] = relationship(
        "TcoConfiguration", lazy="noload"
    )

    __table_args__ = (
        Index("ix_tco_calculations_rfq_id", "rfq_id"),
        Index("ix_tco_calculations_configuration_id", "configuration_id"),
        Index("ix_tco_calculations_status", "status"),
    )
