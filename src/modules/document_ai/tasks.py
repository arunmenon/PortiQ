"""Celery tasks for Document AI — 4-stage extraction pipeline."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from celery_app import celery
from src.config import settings
from src.database.engine import async_session
from src.models.document_extraction import DocumentExtraction, ExtractedLineItem
from src.models.enums import ExtractionConfidenceTier, ExtractionStatus

logger = logging.getLogger(__name__)


# ── Async helper implementations ─────────────────────────────────────────


async def _parse_document_async(extraction_id_str: str) -> str:
    """Async implementation: parse document via Azure Document Intelligence."""
    extraction_uuid = uuid.UUID(extraction_id_str)

    async with async_session() as session:
        # Update status to PARSING
        result = await session.execute(
            select(DocumentExtraction).where(
                DocumentExtraction.id == extraction_uuid
            )
        )
        extraction = result.scalar_one_or_none()
        if extraction is None:
            raise ValueError(f"Extraction {extraction_id_str} not found")

        extraction.status = ExtractionStatus.PARSING
        extraction.processing_started_at = datetime.now(UTC)
        await session.flush()

        try:
            if settings.azure_di_endpoint and settings.azure_di_api_key:
                # TODO: Call Azure Document Intelligence API
                # For now, store a placeholder until Azure integration is complete
                extraction.raw_extraction = {
                    "status": "placeholder",
                    "message": "Azure DI integration pending",
                    "tables": [],
                    "lines": [],
                }
            else:
                # MVP fallback: store empty extraction result
                # In production, this would be populated by Azure DI
                extraction.raw_extraction = {
                    "status": "no_azure_config",
                    "message": "Azure DI not configured; raw_extraction should be pre-populated",
                    "tables": [],
                    "lines": [],
                }

            await session.commit()
            logger.info("parse_document complete for extraction %s", extraction_id_str)
            return extraction_id_str

        except Exception as exc:
            extraction.status = ExtractionStatus.FAILED
            extraction.error_message = str(exc)
            extraction.processing_completed_at = datetime.now(UTC)
            await session.commit()
            raise


async def _normalize_line_items_async(extraction_id_str: str) -> str:
    """Async implementation: normalize extracted text into structured line items."""
    from src.modules.document_ai.normalizer import Normalizer

    extraction_uuid = uuid.UUID(extraction_id_str)
    normalizer = Normalizer()

    async with async_session() as session:
        result = await session.execute(
            select(DocumentExtraction).where(
                DocumentExtraction.id == extraction_uuid
            )
        )
        extraction = result.scalar_one_or_none()
        if extraction is None:
            raise ValueError(f"Extraction {extraction_id_str} not found")

        extraction.status = ExtractionStatus.NORMALIZING
        await session.flush()

        try:
            raw_data = extraction.raw_extraction or {}
            raw_lines = raw_data.get("lines", [])

            # Process each raw line into a structured ExtractedLineItem
            for line_number, raw_line in enumerate(raw_lines, start=1):
                raw_text = raw_line if isinstance(raw_line, str) else raw_line.get("text", "")
                if not raw_text.strip():
                    continue

                normalized_desc = normalizer.normalize_description(raw_text)
                quantity, unit = normalizer.parse_quantity(raw_text)
                detected_impa = normalizer.detect_impa_in_text(raw_text)

                line_item = ExtractedLineItem(
                    extraction_id=extraction_uuid,
                    line_number=line_number,
                    raw_text=raw_text,
                    normalized_description=normalized_desc,
                    detected_quantity=quantity,
                    detected_unit=unit,
                    detected_impa_code=detected_impa,
                )
                session.add(line_item)

            await session.commit()
            logger.info(
                "normalize_line_items complete for extraction %s", extraction_id_str
            )
            return extraction_id_str

        except Exception as exc:
            extraction.status = ExtractionStatus.FAILED
            extraction.error_message = str(exc)
            extraction.processing_completed_at = datetime.now(UTC)
            await session.commit()
            raise


async def _match_sku_async(extraction_id_str: str) -> str:
    """Async implementation: run IMPA matching pipeline on all line items."""
    from src.modules.document_ai.impa_matcher import ImpaMatcher

    extraction_uuid = uuid.UUID(extraction_id_str)

    async with async_session() as session:
        result = await session.execute(
            select(DocumentExtraction).where(
                DocumentExtraction.id == extraction_uuid
            )
        )
        extraction = result.scalar_one_or_none()
        if extraction is None:
            raise ValueError(f"Extraction {extraction_id_str} not found")

        extraction.status = ExtractionStatus.MATCHING
        await session.flush()

        try:
            matcher = ImpaMatcher(session)

            # Get all line items for this extraction
            items_result = await session.execute(
                select(ExtractedLineItem)
                .where(ExtractedLineItem.extraction_id == extraction_uuid)
                .order_by(ExtractedLineItem.line_number)
            )
            line_items = list(items_result.scalars().all())

            # Process in batches
            batch_size = settings.extraction_batch_size
            for start in range(0, len(line_items), batch_size):
                batch = line_items[start : start + batch_size]
                batch_input = [
                    {
                        "raw_text": item.raw_text,
                        "detected_impa_code": item.detected_impa_code,
                    }
                    for item in batch
                ]
                match_results = await matcher.match_batch(batch_input)

                for item, match_result in zip(batch, match_results):
                    item.matched_impa_code = match_result.impa_code
                    item.matched_product_id = match_result.product_id
                    item.match_confidence = match_result.confidence
                    item.match_method = match_result.method

            await session.commit()
            logger.info("match_sku complete for extraction %s", extraction_id_str)
            return extraction_id_str

        except Exception as exc:
            extraction.status = ExtractionStatus.FAILED
            extraction.error_message = str(exc)
            extraction.processing_completed_at = datetime.now(UTC)
            await session.commit()
            raise


async def _route_by_confidence_async(extraction_id_str: str) -> str:
    """Async implementation: assign confidence tiers and update summary counts."""
    extraction_uuid = uuid.UUID(extraction_id_str)

    async with async_session() as session:
        result = await session.execute(
            select(DocumentExtraction).where(
                DocumentExtraction.id == extraction_uuid
            )
        )
        extraction = result.scalar_one_or_none()
        if extraction is None:
            raise ValueError(f"Extraction {extraction_id_str} not found")

        extraction.status = ExtractionStatus.ROUTING
        await session.flush()

        try:
            items_result = await session.execute(
                select(ExtractedLineItem).where(
                    ExtractedLineItem.extraction_id == extraction_uuid
                )
            )
            line_items = list(items_result.scalars().all())

            auto_threshold = settings.extraction_auto_threshold
            quick_review_threshold = settings.extraction_quick_review_threshold

            count_auto = 0
            count_quick_review = 0
            count_full_review = 0

            for item in line_items:
                confidence = item.match_confidence or 0.0

                if confidence >= auto_threshold:
                    item.confidence_tier = ExtractionConfidenceTier.AUTO
                    count_auto += 1
                elif confidence >= quick_review_threshold:
                    item.confidence_tier = ExtractionConfidenceTier.QUICK_REVIEW
                    count_quick_review += 1
                else:
                    item.confidence_tier = ExtractionConfidenceTier.FULL_REVIEW
                    count_full_review += 1

            # Update extraction summary
            extraction.total_items_found = len(line_items)
            extraction.items_auto = count_auto
            extraction.items_quick_review = count_quick_review
            extraction.items_full_review = count_full_review
            extraction.status = ExtractionStatus.COMPLETED
            extraction.processing_completed_at = datetime.now(UTC)

            await session.commit()
            logger.info(
                "route_by_confidence complete for extraction %s: "
                "auto=%d, quick_review=%d, full_review=%d",
                extraction_id_str,
                count_auto,
                count_quick_review,
                count_full_review,
            )
            return extraction_id_str

        except Exception as exc:
            extraction.status = ExtractionStatus.FAILED
            extraction.error_message = str(exc)
            extraction.processing_completed_at = datetime.now(UTC)
            await session.commit()
            raise


# ── Celery task definitions ──────────────────────────────────────────────


@celery.task(
    name="src.modules.document_ai.tasks.parse_document",
    bind=True,
    max_retries=3,
)
def parse_document(self, extraction_id: str) -> str:
    """Stage 1: Parse document via Azure Document Intelligence."""
    try:
        result = asyncio.run(_parse_document_async(extraction_id))
        return result
    except Exception as exc:
        logger.exception("parse_document failed for %s", extraction_id)
        raise self.retry(exc=exc, countdown=30)


@celery.task(
    name="src.modules.document_ai.tasks.normalize_line_items",
    bind=True,
    max_retries=3,
)
def normalize_line_items(self, extraction_id: str) -> str:
    """Stage 2: Normalize extracted text into structured line items."""
    try:
        result = asyncio.run(_normalize_line_items_async(extraction_id))
        return result
    except Exception as exc:
        logger.exception("normalize_line_items failed for %s", extraction_id)
        raise self.retry(exc=exc, countdown=30)


@celery.task(
    name="src.modules.document_ai.tasks.match_sku",
    bind=True,
    max_retries=3,
)
def match_sku(self, extraction_id: str) -> str:
    """Stage 3: Run IMPA matching pipeline on all line items."""
    try:
        result = asyncio.run(_match_sku_async(extraction_id))
        return result
    except Exception as exc:
        logger.exception("match_sku failed for %s", extraction_id)
        raise self.retry(exc=exc, countdown=30)


@celery.task(
    name="src.modules.document_ai.tasks.route_by_confidence",
    bind=True,
    max_retries=3,
)
def route_by_confidence(self, extraction_id: str) -> str:
    """Stage 4: Assign confidence tiers and update summary counts."""
    try:
        result = asyncio.run(_route_by_confidence_async(extraction_id))
        return result
    except Exception as exc:
        logger.exception("route_by_confidence failed for %s", extraction_id)
        raise self.retry(exc=exc, countdown=30)


def start_extraction_pipeline(extraction_id: str) -> None:
    """Kick off the 4-task Celery chain."""
    from celery import chain

    pipeline = chain(
        parse_document.s(extraction_id),
        normalize_line_items.s(),
        match_sku.s(),
        route_by_confidence.s(),
    )
    pipeline.apply_async()
