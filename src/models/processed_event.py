"""ProcessedEvent model — idempotency tracking for event handlers."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, UUIDPrimaryKeyMixin


class ProcessedEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "processed_events"

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True
    )
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    handler_name: Mapped[str] = mapped_column(String(255), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        Index("ix_processed_events_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ProcessedEvent id={self.id} event_id={self.event_id} "
            f"handler={self.handler_name}>"
        )
