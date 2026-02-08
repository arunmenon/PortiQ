from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import QuoteStatus

if TYPE_CHECKING:
    from src.models.organization import Organization
    from src.models.quote_line_item import QuoteLineItem
    from src.models.rfq import Rfq
    from src.models.user import User


class Quote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quotes"

    rfq_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="CASCADE"),
        nullable=False,
    )
    supplier_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[QuoteStatus] = mapped_column(
        nullable=False, server_default="DRAFT"
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="USD"
    )
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_port: Mapped[str | None] = mapped_column(String(10))
    estimated_delivery_days: Mapped[int | None] = mapped_column(Integer)
    payment_terms: Mapped[str | None] = mapped_column(String(255))
    shipping_terms: Mapped[str | None] = mapped_column(String(255))
    warranty_terms: Mapped[str | None] = mapped_column(String(500))
    price_rank: Mapped[int | None] = mapped_column(Integer)
    is_complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    notes: Mapped[str | None] = mapped_column(Text)
    metadata_extra: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawal_reason: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    rfq: Mapped[Rfq] = relationship(
        "Rfq", back_populates="quotes", foreign_keys=[rfq_id], lazy="noload"
    )
    supplier_organization: Mapped[Organization] = relationship(
        "Organization", lazy="noload"
    )
    submitter: Mapped[User | None] = relationship("User", lazy="noload")
    line_items: Mapped[list[QuoteLineItem]] = relationship(
        "QuoteLineItem", back_populates="quote", lazy="noload", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "rfq_id", "supplier_organization_id", "version",
            name="uq_quotes_rfq_supplier_version",
        ),
        CheckConstraint(
            "total_amount IS NULL OR total_amount >= 0",
            name="ck_quotes_total_amount_non_negative",
        ),
        Index("ix_quotes_rfq_id", "rfq_id"),
        Index("ix_quotes_supplier_org_id", "supplier_organization_id"),
        Index("ix_quotes_status", "status"),
    )
