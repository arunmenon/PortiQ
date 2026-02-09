"""QuoteComparisonService — read-only queries for TCO calculation results."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundException
from src.models.enums import QuoteStatus, TcoCalculationStatus
from src.models.quote import Quote
from src.models.tco_calculation import TcoCalculation

logger = logging.getLogger(__name__)


class QuoteComparisonService:
    """Service for reading and comparing TCO calculation results."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_calculation(self, calculation_id: uuid.UUID) -> TcoCalculation:
        """Get a single TCO calculation by ID."""
        result = await self.db.execute(
            select(TcoCalculation).where(TcoCalculation.id == calculation_id)
        )
        calculation = result.scalar_one_or_none()
        if calculation is None:
            raise NotFoundException(f"TCO calculation {calculation_id} not found")
        return calculation

    async def list_calculations(self, rfq_id: uuid.UUID) -> list[TcoCalculation]:
        """List all TCO calculations for an RFQ, newest first."""
        result = await self.db.execute(
            select(TcoCalculation)
            .where(TcoCalculation.rfq_id == rfq_id)
            .order_by(TcoCalculation.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_latest_calculation(
        self, rfq_id: uuid.UUID
    ) -> TcoCalculation | None:
        """Get the most recent COMPLETED calculation for an RFQ, or None."""
        result = await self.db.execute(
            select(TcoCalculation)
            .where(
                TcoCalculation.rfq_id == rfq_id,
                TcoCalculation.status == TcoCalculationStatus.COMPLETED,
            )
            .order_by(TcoCalculation.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def check_staleness(self, calculation_id: uuid.UUID) -> bool:
        """Check if any quotes were modified after the calculation was created.

        If stale, marks the calculation as STALE and returns True.
        """
        calculation = await self.get_calculation(calculation_id)

        if calculation.status != TcoCalculationStatus.COMPLETED:
            return False

        # Check if any submitted quotes for this RFQ were updated after calculation
        result = await self.db.execute(
            select(func.count(Quote.id)).where(
                Quote.rfq_id == calculation.rfq_id,
                Quote.status == QuoteStatus.SUBMITTED,
                Quote.updated_at > calculation.created_at,
            )
        )
        changed_count = result.scalar() or 0

        if changed_count > 0:
            calculation.status = TcoCalculationStatus.STALE
            await self.db.flush()
            logger.info(
                "Calculation %s marked STALE: %d quotes changed since creation",
                calculation_id,
                changed_count,
            )
            return True

        return False
