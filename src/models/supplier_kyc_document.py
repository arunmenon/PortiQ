from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import KycDocumentStatus, KycDocumentType

if TYPE_CHECKING:
    from src.models.supplier_profile import SupplierProfile
    from src.models.user import User


class SupplierKycDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "supplier_kyc_documents"

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supplier_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_type: Mapped[KycDocumentType] = mapped_column(nullable=False)
    file_key: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[KycDocumentStatus] = mapped_column(
        nullable=False, server_default="PENDING"
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    supplier: Mapped[SupplierProfile] = relationship(
        "SupplierProfile", back_populates="kyc_documents"
    )
    verifier: Mapped[User | None] = relationship("User", foreign_keys=[verified_by])

    __table_args__ = (
        Index("ix_kyc_docs_supplier_id", "supplier_id"),
        Index("ix_kyc_docs_status", "status"),
    )
