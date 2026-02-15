"""DisputeComment model — comment trail for dispute communication."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.dispute import Dispute
    from src.models.organization import Organization
    from src.models.user import User


class DisputeComment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "dispute_comments"

    dispute_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("disputes.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    author_org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    # Attachment (optional)
    attachment_s3_key: Mapped[str | None] = mapped_column(String(500))
    attachment_filename: Mapped[str | None] = mapped_column(String(255))
    attachment_content_type: Mapped[str | None] = mapped_column(String(50))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    # Relationships
    dispute: Mapped[Dispute] = relationship(
        "Dispute", back_populates="comments", lazy="noload"
    )
    author: Mapped[User] = relationship("User", lazy="noload")
    author_org: Mapped[Organization] = relationship("Organization", lazy="noload")

    __table_args__ = (
        Index("ix_dispute_comments_dispute_id", "dispute_id"),
    )
