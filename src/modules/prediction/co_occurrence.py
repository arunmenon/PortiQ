"""Co-occurrence service — association rule mining on past RFQ line items.

Computes lift scores for item pairs that appear together in historical RFQs,
allowing "frequently bought together" recommendations.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.product import Product
from src.models.rfq_line_item import RfqLineItem
from src.modules.prediction.schemas import CoOccurrenceSuggestion

logger = logging.getLogger(__name__)


class CoOccurrenceService:
    """Find items that frequently co-occur with the current requisition items."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_suggestions(
        self,
        current_impa_codes: list[str],
        min_lift: float = 2.0,
        min_support: int = 5,
    ) -> list[CoOccurrenceSuggestion]:
        """Find items that frequently co-occur with the given IMPA codes.

        Algorithm:
        1. Count total distinct RFQs (the population).
        2. For each given IMPA code, count how many RFQs contain it: P(A).
        3. Find all other IMPA codes that appear in the same RFQs.
        4. For each candidate, count co-occurrences: P(A and B).
        5. Also count the candidate's overall frequency: P(B).
        6. Compute lift = P(A and B) / (P(A) * P(B)).
        7. Filter by min_lift and min_support, exclude items already in the input.
        """
        if not current_impa_codes:
            return []

        # Total distinct RFQ count
        total_rfqs = await self._count_total_rfqs()
        if total_rfqs == 0:
            return []

        # Find candidate items that co-occur with any of the input IMPA codes
        candidates = await self._find_co_occurring_items(
            current_impa_codes, min_support
        )

        # Batch-fetch all frequency counts and product details to avoid N+1
        input_code_set = set(current_impa_codes)

        # Collect all IMPA codes we need frequencies for
        all_codes_needed: set[str] = set()
        for candidate_impa, _support_count, co_occurs_with_codes in candidates:
            if candidate_impa not in input_code_set:
                all_codes_needed.add(candidate_impa)
                all_codes_needed.update(co_occurs_with_codes)

        # Single batch query for all frequency counts
        frequency_map = await self._batch_count_rfqs_with_items(list(all_codes_needed))

        # Single batch query for all candidate product details
        candidate_codes = [
            c[0] for c in candidates if c[0] not in input_code_set
        ]
        product_map = await self._batch_find_products(candidate_codes)

        # Compute lift for each candidate
        suggestions: list[CoOccurrenceSuggestion] = []

        for candidate_impa, support_count, co_occurs_with_codes in candidates:
            if candidate_impa in input_code_set:
                continue

            # P(B): frequency of the candidate across all RFQs
            candidate_frequency = frequency_map.get(candidate_impa, 0)
            if candidate_frequency == 0:
                continue

            # Average P(A) across the co-occurring input codes
            total_input_frequency = 0.0
            co_occurring_inputs = []
            for input_code in co_occurs_with_codes:
                input_freq = frequency_map.get(input_code, 0)
                if input_freq > 0:
                    total_input_frequency += input_freq / total_rfqs
                    co_occurring_inputs.append(input_code)

            if not co_occurring_inputs or total_input_frequency == 0:
                continue

            avg_input_probability = total_input_frequency / len(co_occurring_inputs)
            joint_probability = support_count / total_rfqs
            candidate_probability = candidate_frequency / total_rfqs

            lift = joint_probability / (avg_input_probability * candidate_probability)

            if lift < min_lift:
                continue

            # Look up product details from batch result
            product = product_map.get(candidate_impa)

            suggestions.append(
                CoOccurrenceSuggestion(
                    impa_code=candidate_impa,
                    product_id=product.id if product else None,
                    description=product.name if product else f"Item {candidate_impa}",
                    lift_score=round(lift, 2),
                    support_count=support_count,
                    co_occurs_with=co_occurring_inputs,
                )
            )

        # Sort by lift score descending
        suggestions.sort(key=lambda s: s.lift_score, reverse=True)

        logger.info(
            "Found %d co-occurrence suggestions for %d input codes (min_lift=%.1f)",
            len(suggestions),
            len(current_impa_codes),
            min_lift,
        )
        return suggestions

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------

    async def _count_total_rfqs(self) -> int:
        """Count total distinct RFQs that have line items."""
        result = await self.db.execute(
            select(func.count(func.distinct(RfqLineItem.rfq_id)))
        )
        return result.scalar() or 0

    async def _batch_count_rfqs_with_items(self, impa_codes: list[str]) -> dict[str, int]:
        """Count distinct RFQs for each IMPA code in a single query."""
        if not impa_codes:
            return {}
        result = await self.db.execute(
            select(
                RfqLineItem.impa_code,
                func.count(func.distinct(RfqLineItem.rfq_id)).label("count"),
            )
            .where(RfqLineItem.impa_code.in_(impa_codes))
            .group_by(RfqLineItem.impa_code)
        )
        return {row[0]: row[1] for row in result.all()}

    async def _batch_find_products(self, impa_codes: list[str]) -> dict[str, Product]:
        """Look up products for multiple IMPA codes in a single query."""
        if not impa_codes:
            return {}
        result = await self.db.execute(
            select(Product).where(Product.impa_code.in_(impa_codes))
        )
        return {p.impa_code: p for p in result.scalars().all()}

    # Deprecated: use _batch_count_rfqs_with_items instead
    async def _count_rfqs_with_item(self, impa_code: str) -> int:
        """Count how many distinct RFQs contain a specific IMPA code.

        Deprecated: Use _batch_count_rfqs_with_items for batch operations.
        """
        result = await self.db.execute(
            select(func.count(func.distinct(RfqLineItem.rfq_id))).where(
                RfqLineItem.impa_code == impa_code
            )
        )
        return result.scalar() or 0

    async def _find_co_occurring_items(
        self,
        impa_codes: list[str],
        min_support: int,
    ) -> list[tuple[str, int, list[str]]]:
        """Find IMPA codes that appear in the same RFQs as the input codes.

        Returns tuples of (candidate_impa, support_count, list_of_co_occurring_input_codes).
        """
        # Subquery: RFQ IDs that contain any of the input IMPA codes
        rfq_ids_with_input = (
            select(RfqLineItem.rfq_id)
            .where(RfqLineItem.impa_code.in_(impa_codes))
            .distinct()
            .scalar_subquery()
        )

        # Find other IMPA codes in those same RFQs, with their counts
        result = await self.db.execute(
            select(
                RfqLineItem.impa_code,
                func.count(func.distinct(RfqLineItem.rfq_id)).label("support_count"),
            )
            .where(
                RfqLineItem.rfq_id.in_(rfq_ids_with_input),
                RfqLineItem.impa_code.isnot(None),
                ~RfqLineItem.impa_code.in_(impa_codes),
            )
            .group_by(RfqLineItem.impa_code)
            .having(func.count(func.distinct(RfqLineItem.rfq_id)) >= min_support)
        )

        candidates: list[tuple[str, int, list[str]]] = []
        for row in result.all():
            candidate_impa = row[0]
            support_count = row[1]

            # Determine which input codes this candidate co-occurs with
            co_occurring_with = await self._find_co_occurring_input_codes(
                candidate_impa, impa_codes
            )
            candidates.append((candidate_impa, support_count, co_occurring_with))

        return candidates

    async def _find_co_occurring_input_codes(
        self,
        candidate_impa: str,
        input_codes: list[str],
    ) -> list[str]:
        """Find which of the input codes the candidate co-occurs with in RFQs."""
        # RFQs containing the candidate
        candidate_rfq_ids = (
            select(RfqLineItem.rfq_id)
            .where(RfqLineItem.impa_code == candidate_impa)
            .distinct()
            .scalar_subquery()
        )

        result = await self.db.execute(
            select(RfqLineItem.impa_code)
            .where(
                RfqLineItem.rfq_id.in_(candidate_rfq_ids),
                RfqLineItem.impa_code.in_(input_codes),
            )
            .distinct()
        )
        return [row[0] for row in result.all()]

    # Deprecated: use _batch_find_products instead
    async def _find_product(self, impa_code: str) -> Product | None:
        """Look up a product by IMPA code.

        Deprecated: Use _batch_find_products for batch operations.
        """
        result = await self.db.execute(
            select(Product).where(Product.impa_code == impa_code)
        )
        return result.scalar_one_or_none()
