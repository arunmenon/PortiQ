"""Document AI API router — extraction management and verification endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.exceptions import BusinessRuleException
from src.models.enums import ExtractionConfidenceTier, ExtractionStatus
from src.modules.document_ai.dedup_service import DedupService
from src.modules.document_ai.extraction_service import ExtractionService
from src.modules.document_ai.schemas import (
    ConvertToLineItemsRequest,
    ConvertToLineItemsResponse,
    DuplicateGroup,
    ExtractedLineItemResponse,
    ExtractionCreateRequest,
    ExtractionDetailResponse,
    ExtractionResponse,
    ItemVerifyRequest,
)
from src.modules.document_ai.tasks import start_extraction_pipeline
from src.modules.tenancy.auth import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/documents", tags=["document-ai"])


# ── POST /api/v1/documents/extract ───────────────────────────────────────


@router.post("/extract", response_model=ExtractionResponse, status_code=201)
async def create_extraction(
    body: ExtractionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ExtractionResponse:
    """Upload and start extraction.

    Creates the tracking record and kicks off the Celery extraction pipeline.
    """
    service = ExtractionService(db)
    extraction = await service.create_extraction(
        filename=body.filename,
        file_type=body.file_type,
        file_size_bytes=body.file_size_bytes,
        uploaded_by=current_user.id,
        rfq_id=body.rfq_id,
        document_type=body.document_type,
    )
    await db.commit()

    # Kick off background pipeline
    start_extraction_pipeline(str(extraction.id))

    return ExtractionResponse.model_validate(extraction)


# ── GET /api/v1/documents/extractions/{extraction_id} ────────────────────


@router.get(
    "/extractions/{extraction_id}",
    response_model=ExtractionDetailResponse,
)
async def get_extraction(
    extraction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ExtractionDetailResponse:
    """Get extraction status with all line items."""
    service = ExtractionService(db)
    extraction = await service.get_extraction(extraction_id)
    return ExtractionDetailResponse.model_validate(extraction)


# ── GET /api/v1/documents/extractions ────────────────────────────────────


@router.get("/extractions", response_model=list[ExtractionResponse])
async def list_extractions(
    rfq_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[ExtractionResponse]:
    """List extractions, optionally filtered by RFQ."""
    service = ExtractionService(db)

    if rfq_id is not None:
        extractions = await service.get_extractions_for_rfq(rfq_id)
    else:
        # For now, return extractions for the current user
        from sqlalchemy import select

        from src.models.document_extraction import DocumentExtraction

        result = await db.execute(
            select(DocumentExtraction)
            .where(DocumentExtraction.uploaded_by == current_user.id)
            .order_by(DocumentExtraction.created_at.desc())
        )
        extractions = list(result.scalars().all())

    return [ExtractionResponse.model_validate(e) for e in extractions]


# ── POST /api/v1/documents/extractions/{extraction_id}/items/{item_id}/verify ──


@router.post(
    "/extractions/{extraction_id}/items/{item_id}/verify",
    response_model=ExtractedLineItemResponse,
)
async def verify_item(
    extraction_id: uuid.UUID,
    item_id: uuid.UUID,
    body: ItemVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ExtractedLineItemResponse:
    """User verifies or corrects an extracted line item."""
    service = ExtractionService(db)

    item = await service.verify_item(
        item_id=item_id,
        extraction_id=extraction_id,
        corrected_impa=body.corrected_impa,
    )
    return ExtractedLineItemResponse.model_validate(item)


# ── POST /api/v1/documents/extractions/{extraction_id}/convert ───────────


@router.post(
    "/extractions/{extraction_id}/convert",
    response_model=ConvertToLineItemsResponse,
)
async def convert_to_line_items(
    extraction_id: uuid.UUID,
    body: ConvertToLineItemsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ConvertToLineItemsResponse:
    """Convert extraction results to RFQ line items."""
    service = ExtractionService(db)
    extraction = await service.get_extraction(extraction_id)

    if extraction.rfq_id is None:
        raise BusinessRuleException(
            "Extraction must be linked to an RFQ before converting to line items"
        )

    if extraction.status != ExtractionStatus.COMPLETED:
        raise BusinessRuleException(
            f"Extraction must be COMPLETED before converting (current: {extraction.status.value})"
        )

    # Determine which items to convert
    all_items = await service.get_items_for_extraction(extraction_id)

    if body.item_ids is not None:
        # Use specified items
        item_id_set = set(body.item_ids)
        selected_items = [item for item in all_items if item.id in item_id_set]
    else:
        # Use all AUTO + user-verified items
        selected_items = [
            item
            for item in all_items
            if item.confidence_tier == ExtractionConfidenceTier.AUTO
            or item.user_verified
        ]

    # Count items still pending review
    pending_review_count = sum(
        1
        for item in all_items
        if item.confidence_tier in (
            ExtractionConfidenceTier.QUICK_REVIEW,
            ExtractionConfidenceTier.FULL_REVIEW,
        )
        and not item.user_verified
    )

    # Create RFQ line items
    from sqlalchemy import func
    from sqlalchemy import select as sa_select

    from src.models.rfq_line_item import RfqLineItem

    # Get max existing line number for this RFQ
    max_line_result = await db.execute(
        sa_select(func.coalesce(func.max(RfqLineItem.line_number), 0)).where(
            RfqLineItem.rfq_id == extraction.rfq_id
        )
    )
    max_line_number = max_line_result.scalar() or 0

    created_count = 0
    for item in selected_items:
        max_line_number += 1
        rfq_line = RfqLineItem(
            rfq_id=extraction.rfq_id,
            line_number=max_line_number,
            product_id=item.matched_product_id,
            impa_code=item.user_corrected_impa or item.matched_impa_code,
            description=item.normalized_description or item.raw_text[:500],
            quantity=item.detected_quantity or 1,
            unit_of_measure=item.detected_unit or "pcs",
            specifications=item.specifications,
        )
        db.add(rfq_line)
        created_count += 1

    await db.flush()

    return ConvertToLineItemsResponse(
        rfq_id=extraction.rfq_id,
        line_items_created=created_count,
        items_pending_review=pending_review_count,
    )


# ── GET /api/v1/documents/extractions/{extraction_id}/duplicates ─────────


@router.get(
    "/extractions/{extraction_id}/duplicates",
    response_model=list[DuplicateGroup],
)
async def check_duplicates(
    extraction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[DuplicateGroup]:
    """Check for duplicate items across documents in the same RFQ."""
    extraction_service = ExtractionService(db)
    extraction = await extraction_service.get_extraction(extraction_id)

    if extraction.rfq_id is None:
        return []

    dedup_service = DedupService(db)
    duplicates = await dedup_service.find_duplicates(
        extraction_id=extraction_id,
        rfq_id=extraction.rfq_id,
    )
    return duplicates
