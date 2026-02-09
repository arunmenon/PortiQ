"""Timing advisor — optimal bidding windows and timeline assessments."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.enums import PortCallStatus, QuoteStatus
from src.models.port_call import PortCall
from src.models.quote import Quote
from src.models.rfq import Rfq
from src.models.rfq_invitation import RfqInvitation
from src.modules.intelligence.schemas import TimingAdvice

logger = logging.getLogger(__name__)

# Default optimal bidding window
_DEFAULT_BIDDING_WINDOW_DAYS = 7
# Thresholds for timeline assessment
_SUFFICIENT_DAYS = 14
_TIGHT_DAYS = 7


class TimingAdvisor:
    """Analyzes vessel ETA, response times, and delivery dates for timing guidance."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_timing_advice(
        self,
        delivery_port: str | None = None,
        delivery_date: datetime | None = None,
        bidding_deadline: datetime | None = None,
        vessel_id: uuid.UUID | None = None,
    ) -> TimingAdvice:
        """Produce timing recommendations based on available context.

        Analyzes:
            - Vessel ETA from latest port_calls or vessel_positions
            - Average quote response time at the delivery port
            - Recommended bidding window
            - Overall timeline assessment
        """
        vessel_eta: datetime | None = None
        avg_response_days: float | None = None
        now = datetime.now(tz=UTC)

        # 1. Vessel ETA lookup
        if vessel_id:
            vessel_eta = await self._get_vessel_eta(vessel_id, delivery_port)

        # 2. Average response time at port
        if delivery_port:
            avg_response_days = await self._get_avg_response_days(delivery_port)

        # 3. Determine effective delivery reference date
        reference_date = delivery_date or vessel_eta
        days_available = (
            (reference_date - now).days if reference_date and reference_date > now else None
        )

        # 4. Compute optimal bidding window
        optimal_window = self._compute_optimal_window(avg_response_days, days_available)

        # 5. Determine timeline assessment
        timeline_assessment = self._assess_timeline(
            days_available=days_available,
            bidding_deadline=bidding_deadline,
            avg_response_days=avg_response_days,
        )

        # 6. Build recommendation text
        recommendation = self._build_recommendation(
            vessel_eta=vessel_eta,
            delivery_date=delivery_date,
            days_available=days_available,
            avg_response_days=avg_response_days,
            timeline_assessment=timeline_assessment,
            bidding_deadline=bidding_deadline,
        )

        return TimingAdvice(
            recommendation=recommendation,
            optimal_window_days=optimal_window,
            vessel_eta=vessel_eta,
            timeline_assessment=timeline_assessment,
            avg_response_days=avg_response_days,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_vessel_eta(
        self,
        vessel_id: uuid.UUID,
        delivery_port: str | None,
    ) -> datetime | None:
        """Look up the latest ETA for a vessel, preferring port_calls matching the delivery port."""
        # First try port_calls for the specific port
        if delivery_port:
            port_call_stmt = (
                select(PortCall.eta)
                .where(
                    PortCall.vessel_id == vessel_id,
                    PortCall.port_code == delivery_port,
                    PortCall.status.in_([
                        PortCallStatus.APPROACHING,
                        PortCallStatus.ARRIVED,
                    ]),
                    PortCall.eta.isnot(None),
                )
                .order_by(PortCall.created_at.desc())
                .limit(1)
            )
            result = await self.db.execute(port_call_stmt)
            row = result.first()
            if row and row[0]:
                return row[0]

        # Fallback: latest port_call with any ETA
        fallback_stmt = (
            select(PortCall.eta)
            .where(
                PortCall.vessel_id == vessel_id,
                PortCall.eta.isnot(None),
                PortCall.status.in_([
                    PortCallStatus.APPROACHING,
                    PortCallStatus.ARRIVED,
                ]),
            )
            .order_by(PortCall.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(fallback_stmt)
        row = result.first()
        return row[0] if row else None

    async def _get_avg_response_days(
        self,
        delivery_port: str,
    ) -> float | None:
        """Compute the average time between invitation and quote submission at a port."""
        stmt = (
            select(
                func.avg(
                    func.extract(
                        "epoch",
                        Quote.submitted_at - RfqInvitation.invited_at,
                    )
                    / 86400
                ).label("avg_days")
            )
            .join(Rfq, Quote.rfq_id == Rfq.id)
            .join(
                RfqInvitation,
                (RfqInvitation.rfq_id == Rfq.id)
                & (RfqInvitation.supplier_organization_id == Quote.supplier_organization_id),
            )
            .where(
                Rfq.delivery_port == delivery_port,
                Quote.status.in_((QuoteStatus.SUBMITTED, QuoteStatus.AWARDED)),
                Quote.submitted_at.isnot(None),
                RfqInvitation.invited_at.isnot(None),
            )
        )
        result = await self.db.execute(stmt)
        row = result.first()
        if row and row[0] is not None:
            avg_days = float(row[0])
            return round(avg_days, 1) if avg_days > 0 else None
        return None

    def _compute_optimal_window(
        self,
        avg_response_days: float | None,
        days_available: int | None,
    ) -> int:
        """Calculate the optimal bidding window in days."""
        if avg_response_days:
            # Give 2x average response time, capped at 14 days
            window = min(14, max(3, int(avg_response_days * 2)))
        else:
            window = _DEFAULT_BIDDING_WINDOW_DAYS

        # Shrink window if we don't have enough time
        if days_available is not None and window > days_available - 3:
            window = max(2, days_available - 3)

        return window

    def _assess_timeline(
        self,
        days_available: int | None,
        bidding_deadline: datetime | None,
        avg_response_days: float | None,
    ) -> str:
        """Classify timeline as sufficient, tight, or risky."""
        if days_available is None:
            return "sufficient"

        if days_available < _TIGHT_DAYS:
            return "risky"
        if days_available < _SUFFICIENT_DAYS:
            return "tight"
        return "sufficient"

    def _build_recommendation(
        self,
        vessel_eta: datetime | None,
        delivery_date: datetime | None,
        days_available: int | None,
        avg_response_days: float | None,
        timeline_assessment: str,
        bidding_deadline: datetime | None,
    ) -> str:
        """Build a human-readable recommendation string."""
        parts = []

        if vessel_eta:
            parts.append(f"Vessel ETA is {vessel_eta.strftime('%Y-%m-%d')}.")

        if delivery_date:
            parts.append(f"Delivery date is {delivery_date.strftime('%Y-%m-%d')}.")

        if days_available is not None:
            parts.append(f"{days_available} day(s) available.")

        if avg_response_days:
            parts.append(
                f"Suppliers at this port typically respond in {avg_response_days:.1f} day(s)."
            )

        if timeline_assessment == "risky":
            parts.append(
                "Timeline is very tight. Consider expediting supplier outreach "
                "or extending the delivery window."
            )
        elif timeline_assessment == "tight":
            parts.append(
                "Timeline is tight but manageable. Start supplier outreach promptly."
            )
        else:
            parts.append("Timeline appears sufficient for standard procurement.")

        return " ".join(parts) if parts else "Insufficient data for timing recommendation."
