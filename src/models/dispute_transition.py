"""DisputeTransition model — state transition audit log for disputes."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, UUIDPrimaryKeyMixin
from src.models.enums import DisputeStatus

if TYPE_CHECKING:
    from src.models.dispute import Dispute
    from src.models.user import User


class DisputeTransition(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "dispute_transitions"

    dispute_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("disputes.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[DisputeStatus] = mapped_column(nullable=False)
    to_status: Mapped[DisputeStatus] = mapped_column(nullable=False)
    transitioned_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    # Relationships
    dispute: Mapped[Dispute] = relationship(
        "Dispute", back_populates="transitions", lazy="noload"
    )
    user: Mapped[User] = relationship("User", lazy="noload")

    __table_args__ = (
        Index("ix_dispute_transitions_dispute_id", "dispute_id"),
    )
