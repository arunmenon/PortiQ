from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import OnboardingStatus, ReviewAction

if TYPE_CHECKING:
    from src.models.supplier_profile import SupplierProfile
    from src.models.user import User


class SupplierReviewLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "supplier_review_logs"

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supplier_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[ReviewAction] = mapped_column(nullable=False)
    from_status: Mapped[OnboardingStatus] = mapped_column(nullable=False)
    to_status: Mapped[OnboardingStatus] = mapped_column(nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    supplier: Mapped[SupplierProfile] = relationship(
        "SupplierProfile", back_populates="review_logs"
    )
    reviewer: Mapped[User | None] = relationship("User", foreign_keys=[reviewer_id])

    __table_args__ = (
        Index("ix_review_logs_supplier_id", "supplier_id"),
        Index("ix_review_logs_action", "action"),
    )
