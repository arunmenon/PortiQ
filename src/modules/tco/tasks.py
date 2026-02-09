"""Celery tasks for TCO Engine — recalculation triggers and cleanup."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from celery_app import celery
from src.database.engine import async_session
from src.models.enums import QuoteStatus, TcoCalculationStatus
from src.models.quote import Quote
from src.models.tco_calculation import TcoCalculation

logger = logging.getLogger(__name__)


# ── Async implementations ────────────────────────────────────────────────────


async def _recalculate_tco_async(rfq_id_str: str) -> str | None:
    """Re-run TCO calculation for an RFQ using its latest configuration."""
    from src.modules.tco.engine import TcoEngineService

    rfq_uuid = uuid.UUID(rfq_id_str)

    async with async_session() as session:
        # Find the latest completed calculation for this RFQ
        result = await session.execute(
            select(TcoCalculation)
            .where(
                TcoCalculation.rfq_id == rfq_uuid,
                TcoCalculation.status.in_([
                    TcoCalculationStatus.COMPLETED,
                    TcoCalculationStatus.STALE,
                ]),
            )
            .order_by(TcoCalculation.created_at.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()

        if latest is None:
            logger.info("No existing calculation for RFQ %s to recalculate", rfq_id_str)
            return None

        # Check that submitted quotes exist
        quotes_result = await session.execute(
            select(Quote.id).where(
                Quote.rfq_id == rfq_uuid,
                Quote.status == QuoteStatus.SUBMITTED,
            ).limit(1)
        )
        if quotes_result.scalar_one_or_none() is None:
            logger.info("No submitted quotes for RFQ %s, skipping recalculation", rfq_id_str)
            return None

        # Use system user UUID for automated recalculations
        system_user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

        engine = TcoEngineService(session)
        try:
            calculation = await engine.calculate_tco(
                rfq_id=rfq_uuid,
                user_id=system_user_id,
                organization_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                configuration_id=latest.configuration_id,
                base_currency=latest.base_currency,
                missing_data_strategy=latest.missing_data_strategy or "penalize",
            )
            await session.commit()
            logger.info(
                "Recalculated TCO for RFQ %s: calculation %s",
                rfq_id_str,
                calculation.id,
            )
            return str(calculation.id)
        except Exception:
            await session.rollback()
            logger.exception("Failed to recalculate TCO for RFQ %s", rfq_id_str)
            raise


async def _cleanup_stale_calculations_async() -> int:
    """Mark old COMPLETED calculations as STALE if quotes have changed."""
    stale_cutoff = datetime.now(UTC) - timedelta(hours=24)

    async with async_session() as session:
        # Find completed calculations older than 24 hours
        result = await session.execute(
            select(TcoCalculation).where(
                TcoCalculation.status == TcoCalculationStatus.COMPLETED,
                TcoCalculation.created_at < stale_cutoff,
            )
        )
        calculations = list(result.scalars().all())

        stale_count = 0
        for calc in calculations:
            # Check if any quotes were updated after the calculation
            quotes_result = await session.execute(
                select(Quote.id).where(
                    Quote.rfq_id == calc.rfq_id,
                    Quote.status == QuoteStatus.SUBMITTED,
                    Quote.updated_at > calc.created_at,
                ).limit(1)
            )
            if quotes_result.scalar_one_or_none() is not None:
                calc.status = TcoCalculationStatus.STALE
                stale_count += 1

        if stale_count > 0:
            await session.commit()
            logger.info("Marked %d calculations as STALE", stale_count)
        else:
            logger.info("No stale calculations found")

        return stale_count


# ── Celery task definitions ──────────────────────────────────────────────────


@celery.task(
    name="src.modules.tco.tasks.recalculate_tco",
    bind=True,
    max_retries=3,
)
def recalculate_tco(self, rfq_id: str) -> str | None:
    """Recalculate TCO for an RFQ after quote events."""
    try:
        return asyncio.run(_recalculate_tco_async(rfq_id))
    except Exception as exc:
        logger.exception("recalculate_tco failed for RFQ %s", rfq_id)
        raise self.retry(exc=exc, countdown=60)


@celery.task(
    name="src.modules.tco.tasks.cleanup_stale_calculations",
    bind=True,
    max_retries=1,
)
def cleanup_stale_calculations(self) -> int:
    """Daily: mark old calculations as STALE if underlying quotes changed."""
    try:
        return asyncio.run(_cleanup_stale_calculations_async())
    except Exception as exc:
        logger.exception("cleanup_stale_calculations failed")
        raise self.retry(exc=exc, countdown=120)
