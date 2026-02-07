"""CategorySchema model — versioned JSON Schema definitions for category attributes."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import SchemaStatus

if TYPE_CHECKING:
    from src.models.category import Category


class CategorySchema(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "category_schemas"

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[SchemaStatus] = mapped_column(String(20), server_default="DRAFT", nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    category: Mapped[Category] = relationship("Category")

    __table_args__ = (
        UniqueConstraint("category_id", "version", name="uq_category_schemas_category_version"),
    )
