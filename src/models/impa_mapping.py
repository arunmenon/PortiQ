from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base

if TYPE_CHECKING:
    from src.models.category import Category
    from src.models.user import User


class ImpaCategoryMapping(Base):
    __tablename__ = "impa_category_mappings"

    impa_prefix: Mapped[str] = mapped_column(String(2), primary_key=True)
    impa_category_name: Mapped[str] = mapped_column(String(255), nullable=False)
    internal_category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False
    )
    mapping_confidence: Mapped[str] = mapped_column(String(20), server_default="EXACT", nullable=False)
    notes: Mapped[str | None] = mapped_column(String)
    last_verified: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )

    # Relationships
    internal_category: Mapped[Category] = relationship("Category", back_populates="impa_mappings")
    verified_by: Mapped[User | None] = relationship("User", back_populates="verified_mappings")


class IssaCategoryMapping(Base):
    __tablename__ = "issa_category_mappings"

    issa_prefix: Mapped[str] = mapped_column(String(2), primary_key=True)
    issa_category_name: Mapped[str] = mapped_column(String(255), nullable=False)
    internal_category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False
    )
    impa_equivalent: Mapped[str | None] = mapped_column(String(2))
    mapping_confidence: Mapped[str] = mapped_column(String(20), server_default="EXACT", nullable=False)
    notes: Mapped[str | None] = mapped_column(String)
    last_verified: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    internal_category: Mapped[Category] = relationship("Category", back_populates="issa_mappings")
