"""Document AI extraction models — extraction tracking and extracted line items."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import DocumentType, ExtractionConfidenceTier, ExtractionStatus

if TYPE_CHECKING:
    from src.models.product import Product
    from src.models.rfq import Rfq
    from src.models.user import User


class DocumentExtraction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_extractions"

    rfq_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="SET NULL"),
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    document_type: Mapped[DocumentType | None] = mapped_column(nullable=True)
    status: Mapped[ExtractionStatus] = mapped_column(
        nullable=False, server_default="PENDING"
    )
    azure_result_url: Mapped[str | None] = mapped_column(Text)
    raw_extraction: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    total_items_found: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    items_auto: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    items_quick_review: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    items_full_review: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    processing_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    # Relationships
    rfq: Mapped[Rfq | None] = relationship("Rfq", lazy="noload")
    uploader: Mapped[User | None] = relationship("User", lazy="noload")
    line_items: Mapped[list[ExtractedLineItem]] = relationship(
        "ExtractedLineItem",
        back_populates="extraction",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_document_extractions_rfq_id", "rfq_id"),
        Index("ix_document_extractions_uploaded_by", "uploaded_by"),
        Index("ix_document_extractions_status", "status"),
    )


class ExtractedLineItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "extracted_line_items"

    extraction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_extractions.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_description: Mapped[str | None] = mapped_column(String(500))
    detected_quantity: Mapped[float | None] = mapped_column(Numeric(12, 3))
    detected_unit: Mapped[str | None] = mapped_column(String(20))
    detected_impa_code: Mapped[str | None] = mapped_column(String(10))
    matched_impa_code: Mapped[str | None] = mapped_column(String(10))
    matched_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
    )
    match_confidence: Mapped[float | None] = mapped_column(Float)
    match_method: Mapped[str | None] = mapped_column(String(20))
    confidence_tier: Mapped[ExtractionConfidenceTier | None] = mapped_column(
        nullable=True
    )
    specifications: Mapped[dict | None] = mapped_column(JSONB)
    is_duplicate: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extracted_line_items.id", ondelete="SET NULL"),
    )
    user_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    user_corrected_impa: Mapped[str | None] = mapped_column(String(10))

    # Relationships
    extraction: Mapped[DocumentExtraction] = relationship(
        "DocumentExtraction", back_populates="line_items", lazy="noload"
    )
    matched_product: Mapped[Product | None] = relationship("Product", lazy="noload")
    duplicate_of: Mapped[ExtractedLineItem | None] = relationship(
        "ExtractedLineItem", remote_side="ExtractedLineItem.id", lazy="noload"
    )

    __table_args__ = (
        UniqueConstraint(
            "extraction_id", "line_number", name="uq_extracted_line_items_extraction_line"
        ),
        Index("ix_extracted_line_items_extraction_id", "extraction_id"),
        Index("ix_extracted_line_items_matched_product_id", "matched_product_id"),
        Index("ix_extracted_line_items_confidence_tier", "confidence_tier"),
    )
