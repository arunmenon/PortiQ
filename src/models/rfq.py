from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import AuctionType, RfqStatus

if TYPE_CHECKING:
    from src.models.organization import Organization
    from src.models.quote import Quote
    from src.models.rfq_invitation import RfqInvitation
    from src.models.rfq_line_item import RfqLineItem
    from src.models.rfq_transition import RfqTransition
    from src.models.user import User
    from src.models.vessel import Vessel


class Rfq(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rfqs"

    reference_number: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True
    )
    buyer_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RfqStatus] = mapped_column(
        nullable=False, server_default="DRAFT"
    )
    auction_type: Mapped[AuctionType] = mapped_column(
        nullable=False, server_default="SEALED_BID"
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="USD"
    )
    vessel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vessels.id", ondelete="SET NULL"),
    )
    delivery_port: Mapped[str | None] = mapped_column(String(10))
    delivery_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    bidding_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    bidding_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    allow_partial_quotes: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    allow_quote_revision: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    require_all_line_items: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    awarded_quote_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quotes.id", ondelete="SET NULL"),
    )
    awarded_supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
    )
    awarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    metadata_extra: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Relationships (lazy="noload" for performance)
    buyer_organization: Mapped[Organization] = relationship(
        "Organization", foreign_keys=[buyer_organization_id], lazy="noload"
    )
    awarded_supplier: Mapped[Organization | None] = relationship(
        "Organization", foreign_keys=[awarded_supplier_id], lazy="noload"
    )
    vessel: Mapped[Vessel | None] = relationship("Vessel", lazy="noload")
    creator: Mapped[User] = relationship("User", lazy="noload")
    awarded_quote: Mapped[Quote | None] = relationship(
        "Quote", foreign_keys=[awarded_quote_id], lazy="noload"
    )
    line_items: Mapped[list[RfqLineItem]] = relationship(
        "RfqLineItem", back_populates="rfq", lazy="noload", cascade="all, delete-orphan"
    )
    invitations: Mapped[list[RfqInvitation]] = relationship(
        "RfqInvitation", back_populates="rfq", lazy="noload", cascade="all, delete-orphan"
    )
    quotes: Mapped[list[Quote]] = relationship(
        "Quote", back_populates="rfq", foreign_keys="Quote.rfq_id", lazy="noload"
    )
    transitions: Mapped[list[RfqTransition]] = relationship(
        "RfqTransition", back_populates="rfq", lazy="noload", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_rfqs_buyer_org_id", "buyer_organization_id"),
        Index("ix_rfqs_status", "status"),
        Index("ix_rfqs_created_by", "created_by"),
        Index(
            "ix_rfqs_vessel_id",
            "vessel_id",
            postgresql_where="vessel_id IS NOT NULL",
        ),
        Index(
            "ix_rfqs_bidding_deadline",
            "bidding_deadline",
            postgresql_where="status IN ('PUBLISHED', 'BIDDING_OPEN')",
        ),
        Index("ix_rfqs_reference_number", "reference_number"),
    )
