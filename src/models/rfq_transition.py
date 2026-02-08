from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, UUIDPrimaryKeyMixin
from src.models.enums import RfqStatus, RfqTransitionType

if TYPE_CHECKING:
    from src.models.rfq import Rfq
    from src.models.user import User


class RfqTransition(UUIDPrimaryKeyMixin, Base):
    """Immutable audit log for RFQ state transitions. No updated_at column."""

    __tablename__ = "rfq_transitions"

    rfq_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[RfqStatus] = mapped_column(nullable=False)
    to_status: Mapped[RfqStatus] = mapped_column(nullable=False)
    transition_type: Mapped[RfqTransitionType] = mapped_column(nullable=False)
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    trigger_source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="user"
    )
    reason: Mapped[str | None] = mapped_column(Text)
    metadata_extra: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    rfq: Mapped[Rfq] = relationship("Rfq", back_populates="transitions", lazy="noload")
    triggered_by_user: Mapped[User | None] = relationship("User", lazy="noload")

    __table_args__ = (
        Index("ix_rfq_transitions_rfq_id", "rfq_id"),
        Index("ix_rfq_transitions_to_status", "to_status"),
    )
