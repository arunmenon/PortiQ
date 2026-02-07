from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.user import User


class ProductAuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "product_audit_log"

    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    operation: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_fields: Mapped[dict | None] = mapped_column(JSONB)
    changed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    change_reason: Mapped[str | None] = mapped_column(String)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    changed_by: Mapped[User | None] = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_product_audit_log_entity", "entity_type", "entity_id"),
        Index("ix_product_audit_log_created_at", "created_at"),
    )
