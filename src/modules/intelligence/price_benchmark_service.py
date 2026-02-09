"""Price benchmark service — historical price percentiles from quote data."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.enums import QuoteStatus
from src.models.quote import Quote
from src.models.quote_line_item import QuoteLineItem
from src.models.rfq import Rfq
from src.models.rfq_line_item import RfqLineItem
from src.modules.intelligence.schemas import BudgetEstimate, PriceBenchmark

logger = logging.getLogger(__name__)

# Tier of valid quote statuses for benchmark calculation
_BENCHMARK_STATUSES = (QuoteStatus.SUBMITTED, QuoteStatus.AWARDED)


class PriceBenchmarkService:
    """Computes price benchmarks from historical quote line items."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_price_benchmarks(
        self,
        impa_codes: list[str],
        delivery_port: str | None = None,
        days: int | None = None,
    ) -> list[PriceBenchmark]:
        """Return price percentiles (P25/P50/P75) for each IMPA code.

        Queries quote_line_items joined with quotes and rfq_line_items/rfqs.
        Only considers quotes with status SUBMITTED or AWARDED within the
        look-back window. Optionally filters by delivery port.
        """
        if not impa_codes:
            return []

        if days is None:
            days = settings.intelligence_price_benchmark_days

        cutoff = datetime.now(tz=UTC) - timedelta(days=days)
        min_quotes = settings.intelligence_min_quotes_for_benchmark

        benchmarks: list[PriceBenchmark] = []

        for impa_code in impa_codes:
            benchmark = await self._benchmark_for_impa(
                impa_code=impa_code,
                delivery_port=delivery_port,
                cutoff=cutoff,
                days=days,
                min_quotes=min_quotes,
            )
            benchmarks.append(benchmark)

        return benchmarks

    async def _benchmark_for_impa(
        self,
        impa_code: str,
        delivery_port: str | None,
        cutoff: datetime,
        days: int,
        min_quotes: int,
    ) -> PriceBenchmark:
        """Compute a single IMPA code's price benchmark."""
        # Build the base query joining quote_line_items -> quotes -> rfq_line_items -> rfqs
        stmt = (
            select(QuoteLineItem.unit_price)
            .join(Quote, QuoteLineItem.quote_id == Quote.id)
            .join(RfqLineItem, QuoteLineItem.rfq_line_item_id == RfqLineItem.id)
            .join(Rfq, RfqLineItem.rfq_id == Rfq.id)
            .where(
                Quote.status.in_(_BENCHMARK_STATUSES),
                Quote.submitted_at >= cutoff,
                Quote.submitted_at.isnot(None),
                RfqLineItem.impa_code == impa_code,
            )
        )

        if delivery_port:
            stmt = stmt.where(Rfq.delivery_port == delivery_port)

        result = await self.db.execute(stmt)
        prices = sorted([row[0] for row in result.all()])
        quote_count = len(prices)

        if quote_count < min_quotes:
            return PriceBenchmark(
                impa_code=impa_code,
                quote_count=quote_count,
                has_data=False,
                period_days=days,
            )

        p25 = self._percentile(prices, 0.25)
        p50 = self._percentile(prices, 0.50)
        p75 = self._percentile(prices, 0.75)

        # Determine currency from the most recent quote
        currency_stmt = (
            select(Rfq.currency)
            .join(RfqLineItem, RfqLineItem.rfq_id == Rfq.id)
            .join(QuoteLineItem, QuoteLineItem.rfq_line_item_id == RfqLineItem.id)
            .join(Quote, QuoteLineItem.quote_id == Quote.id)
            .where(
                RfqLineItem.impa_code == impa_code,
                Quote.status.in_(_BENCHMARK_STATUSES),
                Quote.submitted_at >= cutoff,
            )
            .order_by(Quote.submitted_at.desc())
            .limit(1)
        )
        currency_result = await self.db.execute(currency_stmt)
        currency_row = currency_result.first()
        currency = currency_row[0] if currency_row else "USD"

        return PriceBenchmark(
            impa_code=impa_code,
            p25=p25,
            p50=p50,
            p75=p75,
            quote_count=quote_count,
            has_data=True,
            currency=currency,
            period_days=days,
        )

    async def estimate_budget(
        self,
        line_items: list[dict],
        delivery_port: str | None = None,
    ) -> BudgetEstimate:
        """Combine price benchmarks with quantities to produce budget ranges.

        Each dict in line_items should have keys: impa_code, quantity.
        Returns low (P25-based), likely (P50-based), high (P75-based).
        """
        if not line_items:
            return BudgetEstimate()

        impa_codes = [item["impa_code"] for item in line_items if item.get("impa_code")]
        benchmarks = await self.get_price_benchmarks(impa_codes, delivery_port=delivery_port)
        benchmark_map = {b.impa_code: b for b in benchmarks}

        total_low = Decimal("0")
        total_likely = Decimal("0")
        total_high = Decimal("0")
        items_with_data = 0
        items_without_data = 0
        currency = "USD"

        for item in line_items:
            impa_code = item.get("impa_code")
            quantity = Decimal(str(item.get("quantity", 0)))

            if not impa_code:
                items_without_data += 1
                continue

            benchmark = benchmark_map.get(impa_code)
            if benchmark and benchmark.has_data:
                items_with_data += 1
                total_low += quantity * (benchmark.p25 or Decimal("0"))
                total_likely += quantity * (benchmark.p50 or Decimal("0"))
                total_high += quantity * (benchmark.p75 or Decimal("0"))
                currency = benchmark.currency
            else:
                items_without_data += 1

        return BudgetEstimate(
            low=total_low,
            likely=total_likely,
            high=total_high,
            items_with_data=items_with_data,
            items_without_data=items_without_data,
            currency=currency,
        )

    @staticmethod
    def _percentile(sorted_values: list[Decimal], percentile: float) -> Decimal:
        """Compute a percentile from a sorted list using linear interpolation."""
        if not sorted_values:
            return Decimal("0")
        count = len(sorted_values)
        if count == 1:
            return sorted_values[0]

        index = percentile * (count - 1)
        lower = int(index)
        upper = lower + 1
        if upper >= count:
            return sorted_values[-1]

        fraction = Decimal(str(index - lower))
        return sorted_values[lower] + fraction * (sorted_values[upper] - sorted_values[lower])
