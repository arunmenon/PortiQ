from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import OnboardingStatus, SupplierTier

if TYPE_CHECKING:
    from src.models.organization import Organization
    from src.models.supplier_kyc_document import SupplierKycDocument
    from src.models.supplier_review_log import SupplierReviewLog


class SupplierProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "supplier_profiles"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    tier: Mapped[SupplierTier] = mapped_column(
        nullable=False, server_default="PENDING"
    )
    onboarding_status: Mapped[OnboardingStatus] = mapped_column(
        nullable=False, server_default="STARTED"
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    gst_number: Mapped[str | None] = mapped_column(String(20))
    pan_number: Mapped[str | None] = mapped_column(String(20))
    cin_number: Mapped[str | None] = mapped_column(String(25))
    address_line1: Mapped[str | None] = mapped_column(String(255))
    address_line2: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    pincode: Mapped[str | None] = mapped_column(String(10))
    country: Mapped[str] = mapped_column(String(100), nullable=False, server_default="India")
    categories: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    port_coverage: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    verification_results: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    # Relationships
    organization: Mapped[Organization] = relationship("Organization")
    kyc_documents: Mapped[list[SupplierKycDocument]] = relationship(
        "SupplierKycDocument", back_populates="supplier", cascade="all, delete-orphan"
    )
    review_logs: Mapped[list[SupplierReviewLog]] = relationship(
        "SupplierReviewLog", back_populates="supplier", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_supplier_profiles_org_id", "organization_id"),
        Index("ix_supplier_profiles_tier", "tier"),
        Index("ix_supplier_profiles_status", "onboarding_status"),
    )
