"""SettlementPeriod model — aggregation period for invoices."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import SettlementPeriodStatus, SettlementPeriodType

if TYPE_CHECKING:
    from src.models.invoice import Invoice
    from src.models.organization import Organization


class SettlementPeriod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "settlement_periods"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    period_type: Mapped[SettlementPeriodType] = mapped_column(nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    period_label: Mapped[str | None] = mapped_column(String(100))

    # Aggregates
    total_invoices: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, server_default="0"
    )
    total_credits: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, server_default="0"
    )
    net_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, server_default="0"
    )

    status: Mapped[SettlementPeriodStatus] = mapped_column(
        nullable=False, server_default="OPEN"
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    organization: Mapped[Organization] = relationship(
        "Organization", lazy="noload"
    )
    invoices: Mapped[list[Invoice]] = relationship(
        "Invoice",
        back_populates="settlement_period",
        lazy="noload",
    )

    __table_args__ = (
        Index("ix_settlement_periods_organization_id", "organization_id"),
        Index("ix_settlement_periods_status", "status"),
    )
