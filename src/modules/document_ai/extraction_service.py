"""ExtractionService — CRUD operations for document extractions and line items."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.exceptions import NotFoundException
from src.models.document_extraction import DocumentExtraction, ExtractedLineItem
from src.models.enums import (
    DocumentType,
    ExtractionConfidenceTier,
    ExtractionStatus,
)


class ExtractionService:
    """Service layer for document extraction operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_extraction(
        self,
        filename: str,
        file_type: str,
        file_size_bytes: int,
        uploaded_by: uuid.UUID,
        rfq_id: uuid.UUID | None = None,
        document_type: DocumentType | None = None,
    ) -> DocumentExtraction:
        """Create a new extraction record with PENDING status."""
        extraction = DocumentExtraction(
            filename=filename,
            file_type=file_type,
            file_size_bytes=file_size_bytes,
            uploaded_by=uploaded_by,
            rfq_id=rfq_id,
            document_type=document_type,
            status=ExtractionStatus.PENDING,
        )
        self.db.add(extraction)
        await self.db.flush()
        return extraction

    async def get_extraction(self, extraction_id: uuid.UUID) -> DocumentExtraction:
        """Get extraction with line items eagerly loaded."""
        result = await self.db.execute(
            select(DocumentExtraction)
            .options(selectinload(DocumentExtraction.line_items))
            .where(DocumentExtraction.id == extraction_id)
        )
        extraction = result.scalar_one_or_none()
        if extraction is None:
            raise NotFoundException(f"Extraction {extraction_id} not found")
        return extraction

    async def get_extractions_for_rfq(
        self, rfq_id: uuid.UUID
    ) -> list[DocumentExtraction]:
        """List all extractions for an RFQ."""
        result = await self.db.execute(
            select(DocumentExtraction)
            .where(DocumentExtraction.rfq_id == rfq_id)
            .order_by(DocumentExtraction.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        extraction_id: uuid.UUID,
        status: ExtractionStatus,
        error_message: str | None = None,
    ) -> DocumentExtraction:
        """Update extraction status.

        Sets processing_started_at on PARSING,
        processing_completed_at on COMPLETED or FAILED.
        """
        result = await self.db.execute(
            select(DocumentExtraction).where(
                DocumentExtraction.id == extraction_id
            )
        )
        extraction = result.scalar_one_or_none()
        if extraction is None:
            raise NotFoundException(f"Extraction {extraction_id} not found")

        extraction.status = status
        now = datetime.now(UTC)

        if status == ExtractionStatus.PARSING:
            extraction.processing_started_at = now

        if status in (ExtractionStatus.COMPLETED, ExtractionStatus.FAILED):
            extraction.processing_completed_at = now

        if error_message is not None:
            extraction.error_message = error_message

        await self.db.flush()
        return extraction

    async def save_extracted_items(
        self,
        extraction_id: uuid.UUID,
        items: list[dict],
    ) -> list[ExtractedLineItem]:
        """Bulk insert extracted line items.

        Each dict in *items* should contain at minimum:
        - line_number: int
        - raw_text: str
        And optionally: normalized_description, detected_quantity, detected_unit,
        detected_impa_code, specifications.
        """
        line_items = []
        for item_data in items:
            line_item = ExtractedLineItem(
                extraction_id=extraction_id,
                line_number=item_data["line_number"],
                raw_text=item_data["raw_text"],
                normalized_description=item_data.get("normalized_description"),
                detected_quantity=item_data.get("detected_quantity"),
                detected_unit=item_data.get("detected_unit"),
                detected_impa_code=item_data.get("detected_impa_code"),
                specifications=item_data.get("specifications"),
            )
            self.db.add(line_item)
            line_items.append(line_item)

        await self.db.flush()
        return line_items

    async def update_item_match(
        self,
        item_id: uuid.UUID,
        matched_impa_code: str,
        matched_product_id: uuid.UUID | None,
        match_confidence: float,
        match_method: str,
        confidence_tier: ExtractionConfidenceTier,
    ) -> ExtractedLineItem:
        """Update a single item with match results."""
        result = await self.db.execute(
            select(ExtractedLineItem).where(ExtractedLineItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise NotFoundException(f"Extracted line item {item_id} not found")

        item.matched_impa_code = matched_impa_code
        item.matched_product_id = matched_product_id
        item.match_confidence = match_confidence
        item.match_method = match_method
        item.confidence_tier = confidence_tier

        await self.db.flush()
        return item

    async def verify_item(
        self,
        item_id: uuid.UUID,
        extraction_id: uuid.UUID,
        corrected_impa: str | None = None,
    ) -> ExtractedLineItem:
        """Mark item as user-verified, optionally with corrected IMPA code."""
        result = await self.db.execute(
            select(ExtractedLineItem).where(
                ExtractedLineItem.id == item_id,
                ExtractedLineItem.extraction_id == extraction_id,
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise NotFoundException(f"Extracted line item {item_id} not found")

        item.user_verified = True
        if corrected_impa is not None:
            item.user_corrected_impa = corrected_impa

        await self.db.flush()
        return item

    async def get_items_for_extraction(
        self, extraction_id: uuid.UUID
    ) -> list[ExtractedLineItem]:
        """Get all line items for an extraction."""
        result = await self.db.execute(
            select(ExtractedLineItem)
            .where(ExtractedLineItem.extraction_id == extraction_id)
            .order_by(ExtractedLineItem.line_number)
        )
        return list(result.scalars().all())
