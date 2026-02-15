"""ExportJob model — async data export job tracking."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, UUIDPrimaryKeyMixin
from src.models.enums import ExportFormat, ExportJobStatus, ExportType
from sqlalchemy import func

if TYPE_CHECKING:
    from src.models.organization import Organization
    from src.models.user import User


class ExportJob(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "export_jobs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Export specification
    export_type: Mapped[ExportType] = mapped_column(nullable=False)
    export_format: Mapped[ExportFormat] = mapped_column(nullable=False)
    filters: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )

    # Entity reference (for single-entity exports like invoice PDF)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    entity_type: Mapped[str | None] = mapped_column(String(30))

    # Status
    status: Mapped[ExportJobStatus] = mapped_column(
        nullable=False, server_default="PENDING"
    )
    progress_percent: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    error_message: Mapped[str | None] = mapped_column(Text)

    # Output
    s3_key: Mapped[str | None] = mapped_column(String(500))
    s3_bucket: Mapped[str | None] = mapped_column(String(100))
    file_name: Mapped[str | None] = mapped_column(String(255))
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    content_type: Mapped[str | None] = mapped_column(String(50))
    download_url_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    # Row counts
    total_rows: Mapped[int | None] = mapped_column(Integer)
    processed_rows: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    organization: Mapped[Organization] = relationship(
        "Organization", lazy="noload"
    )
    requester: Mapped[User] = relationship("User", lazy="noload")

    __table_args__ = (
        Index("ix_export_jobs_organization_id", "organization_id"),
        Index("ix_export_jobs_requested_by", "requested_by"),
        Index("ix_export_jobs_status", "status"),
    )
