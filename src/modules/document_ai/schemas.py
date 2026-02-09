"""Pydantic v2 schemas for Document AI module."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.models.enums import DocumentType, ExtractionConfidenceTier, ExtractionStatus

# ── Request schemas ──────────────────────────────────────────────────────


class ExtractionCreateRequest(BaseModel):
    """Request to create a new document extraction."""

    filename: str = Field(..., max_length=255, pattern=r'^[\w\-. ]+$')
    file_type: str = Field(..., max_length=50)
    file_size_bytes: int = Field(..., gt=0, le=52_428_800)
    rfq_id: uuid.UUID | None = None
    document_type: DocumentType | None = None


class ItemVerifyRequest(BaseModel):
    """Request to verify or correct an extracted line item."""

    corrected_impa: str | None = Field(default=None, max_length=10)

    @field_validator("corrected_impa")
    @classmethod
    def validate_impa(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^\d{6}$", v):
            raise ValueError("Corrected IMPA code must be 6 digits")
        return v


class ConvertToLineItemsRequest(BaseModel):
    """Request to convert extraction results to RFQ line items."""

    item_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="If None, use all AUTO + verified items",
    )


# ── Response schemas ─────────────────────────────────────────────────────


class ExtractionResponse(BaseModel):
    """Response for a document extraction record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rfq_id: uuid.UUID | None
    filename: str
    file_type: str
    document_type: DocumentType | None
    status: ExtractionStatus
    total_items_found: int
    items_auto: int
    items_quick_review: int
    items_full_review: int
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
    error_message: str | None
    created_at: datetime


class ExtractedLineItemResponse(BaseModel):
    """Response for a single extracted line item."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    extraction_id: uuid.UUID
    line_number: int
    raw_text: str
    normalized_description: str | None
    detected_quantity: Decimal | None
    detected_unit: str | None
    detected_impa_code: str | None
    matched_impa_code: str | None
    matched_product_id: uuid.UUID | None
    match_confidence: float | None
    match_method: str | None
    confidence_tier: ExtractionConfidenceTier | None
    specifications: dict | None
    is_duplicate: bool
    user_verified: bool
    user_corrected_impa: str | None


class ExtractionDetailResponse(ExtractionResponse):
    """Response for an extraction with its line items."""

    line_items: list[ExtractedLineItemResponse] = []


class ConvertToLineItemsResponse(BaseModel):
    """Response after converting extraction to RFQ line items."""

    rfq_id: uuid.UUID
    line_items_created: int
    items_pending_review: int


# ── Internal data schemas ────────────────────────────────────────────────


class MatchAlternative(BaseModel):
    """A possible match alternative."""

    impa_code: str
    product_name: str | None = None
    confidence: float


class MatchResult(BaseModel):
    """Result from the IMPA matching pipeline."""

    impa_code: str | None = None
    product_id: uuid.UUID | None = None
    product_name: str | None = None
    confidence: float = 0.0
    method: str = "none"  # regex, semantic, llm
    alternatives: list[MatchAlternative] = Field(default_factory=list, max_length=3)


class DuplicateGroupItem(BaseModel):
    """An item within a duplicate group."""

    extraction_id: uuid.UUID
    item_id: uuid.UUID
    quantity: Decimal | None
    source_filename: str


class DuplicateGroup(BaseModel):
    """A group of potentially duplicate line items."""

    impa_code: str
    items: list[DuplicateGroupItem]
    suggested_merge_quantity: Decimal
