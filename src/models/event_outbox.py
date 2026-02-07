"""EventOutbox model — transactional outbox for reliable event delivery."""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import EventStatus


class EventOutbox(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "event_outbox"

    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(255), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    status: Mapped[EventStatus] = mapped_column(
        SQLAlchemyEnum(EventStatus, name="eventstatus", create_type=False),
        nullable=False,
        server_default="PENDING",
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")

    __table_args__ = (
        Index("ix_event_outbox_status", "status"),
        Index("ix_event_outbox_event_type", "event_type"),
        Index("ix_event_outbox_aggregate", "aggregate_type", "aggregate_id"),
        Index(
            "ix_event_outbox_pending",
            "created_at",
            postgresql_where=(status == EventStatus.PENDING),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<EventOutbox id={self.id} type={self.event_type} "
            f"aggregate={self.aggregate_type}/{self.aggregate_id} status={self.status}>"
        )
