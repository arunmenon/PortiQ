"""Rule-based consumption prediction engine.

Calculates expected consumption quantities per IMPA category using base rates,
vessel-type multipliers, and safety buffers.  When the vessel has sufficient
historical data (>= 5 completed RFQs), predictions are blended with actual
usage patterns.
"""

from __future__ import annotations

import logging
import math
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundException
from src.models.enums import RfqStatus
from src.models.product import Product
from src.models.rfq import Rfq
from src.models.rfq_line_item import RfqLineItem
from src.models.vessel import Vessel
from src.modules.prediction.constants import (
    BLENDED_CONFIDENCE,
    CONSUMPTION_RATES,
    HISTORY_BLEND_THRESHOLD,
    HISTORY_WEIGHT,
    RULES_ONLY_CONFIDENCE,
    RULES_WEIGHT,
    VESSEL_TYPE_MULTIPLIERS,
)
from src.modules.prediction.schemas import PredictedItem

logger = logging.getLogger(__name__)


class ConsumptionEngine:
    """Predict consumption quantities using rules, optionally blended with history."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def predict_quantities(
        self,
        vessel_id: uuid.UUID,
        voyage_days: int,
        crew_size: int,
        categories: list[str] | None = None,
    ) -> list[PredictedItem]:
        """Predict consumption quantities for a vessel voyage.

        Steps:
        1. Load vessel to determine vessel_type.
        2. For each IMPA category (filtered if ``categories`` is provided):
           - Compute rule-based quantity using base_rate, multiplier, and buffer.
        3. Check historical RFQ count; blend if vessel has >= 5 completed RFQs.
        4. Look up top catalog products per category.
        5. Return list of PredictedItem.
        """
        vessel = await self._load_vessel(vessel_id)
        vessel_type_name = vessel.vessel_type.value

        target_categories = categories if categories else list(CONSUMPTION_RATES.keys())

        # Check for historical data (cold start detection)
        historical_rfq_count = await self._count_completed_rfqs(vessel_id)
        has_history = historical_rfq_count >= HISTORY_BLEND_THRESHOLD

        historical_averages: dict[str, Decimal] = {}
        if has_history:
            historical_averages = await self._compute_historical_averages(
                vessel_id, target_categories
            )

        results: list[PredictedItem] = []
        for category_prefix in target_categories:
            rate_config = CONSUMPTION_RATES.get(category_prefix)
            if rate_config is None:
                continue

            rule_quantity = self._compute_rule_quantity(
                rate_config=rate_config,
                vessel_type=vessel_type_name,
                category_prefix=category_prefix,
                voyage_days=voyage_days,
                crew_size=crew_size,
            )

            # Blend with history when available
            if has_history and category_prefix in historical_averages:
                historical_qty = historical_averages[category_prefix]
                blended_quantity = Decimal(str(
                    float(rule_quantity) * RULES_WEIGHT
                    + float(historical_qty) * HISTORY_WEIGHT
                ))
                confidence = BLENDED_CONFIDENCE
            else:
                blended_quantity = rule_quantity
                confidence = RULES_ONLY_CONFIDENCE

            # Round up — better to over-supply than under-supply at sea
            final_quantity = Decimal(str(math.ceil(float(blended_quantity) * 100) / 100))

            # Look up top catalog products for this category
            catalog_products = await self._find_products_for_category(category_prefix)

            if catalog_products:
                for product in catalog_products:
                    results.append(
                        PredictedItem(
                            impa_code=product.impa_code,
                            product_id=product.id,
                            description=product.name,
                            quantity=final_quantity,
                            unit=rate_config["unit"],
                            confidence=confidence,
                            category_prefix=category_prefix,
                        )
                    )
            else:
                # No catalog products found — return a generic prediction
                results.append(
                    PredictedItem(
                        impa_code=f"{category_prefix}0000",
                        product_id=None,
                        description=f"Category {category_prefix} supplies",
                        quantity=final_quantity,
                        unit=rate_config["unit"],
                        confidence=confidence * 0.8,  # lower confidence without catalog match
                        category_prefix=category_prefix,
                    )
                )

        logger.info(
            "Predicted %d items for vessel %s (%d-day voyage, crew %d, history=%s)",
            len(results),
            vessel_id,
            voyage_days,
            crew_size,
            has_history,
        )
        return results

    # ------------------------------------------------------------------
    # Rule-based computation
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_rule_quantity(
        rate_config: dict,
        vessel_type: str,
        category_prefix: str,
        voyage_days: int,
        crew_size: int,
    ) -> Decimal:
        """Calculate quantity from base rate, vessel multiplier, and buffer."""
        base_rate = rate_config["base_rate"]
        buffer = rate_config["buffer"]
        per = rate_config["per"]

        # Get vessel type multiplier
        type_multipliers = VESSEL_TYPE_MULTIPLIERS.get(vessel_type, {"DEFAULT": 1.0})
        multiplier = type_multipliers.get(
            category_prefix, type_multipliers.get("DEFAULT", 1.0)
        )

        if per == "person/day":
            quantity = base_rate * crew_size * voyage_days * multiplier * buffer
        else:
            # "vessel/day"
            quantity = base_rate * voyage_days * multiplier * buffer

        return Decimal(str(round(quantity, 2)))

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------

    async def _load_vessel(self, vessel_id: uuid.UUID) -> Vessel:
        """Load a vessel by ID. Raises NotFoundException if not found."""
        result = await self.db.execute(
            select(Vessel).where(Vessel.id == vessel_id)
        )
        vessel = result.scalar_one_or_none()
        if vessel is None:
            raise NotFoundException(f"Vessel {vessel_id} not found")
        return vessel

    async def _count_completed_rfqs(self, vessel_id: uuid.UUID) -> int:
        """Count completed/awarded RFQs for a vessel."""
        result = await self.db.execute(
            select(func.count())
            .select_from(Rfq)
            .where(
                Rfq.vessel_id == vessel_id,
                Rfq.status.in_([RfqStatus.COMPLETED, RfqStatus.AWARDED]),
            )
        )
        return result.scalar() or 0

    async def _compute_historical_averages(
        self,
        vessel_id: uuid.UUID,
        categories: list[str],
    ) -> dict[str, Decimal]:
        """Compute average quantities per category from past completed RFQs."""
        # Subquery: IDs of completed RFQs for this vessel
        completed_rfq_ids = (
            select(Rfq.id)
            .where(
                Rfq.vessel_id == vessel_id,
                Rfq.status.in_([RfqStatus.COMPLETED, RfqStatus.AWARDED]),
            )
            .scalar_subquery()
        )

        averages: dict[str, Decimal] = {}
        for category_prefix in categories:
            pattern = f"{category_prefix}%"
            result = await self.db.execute(
                select(func.avg(RfqLineItem.quantity))
                .where(
                    RfqLineItem.rfq_id.in_(completed_rfq_ids),
                    RfqLineItem.impa_code.ilike(pattern),
                )
            )
            avg_val = result.scalar()
            if avg_val is not None:
                averages[category_prefix] = Decimal(str(round(float(avg_val), 2)))

        return averages

    async def _find_products_for_category(
        self, category_prefix: str, limit: int = 5
    ) -> list[Product]:
        """Find top products whose IMPA code starts with the given prefix."""
        pattern = f"{category_prefix}%"
        result = await self.db.execute(
            select(Product)
            .where(Product.impa_code.ilike(pattern))
            .order_by(Product.name)
            .limit(limit)
        )
        return list(result.scalars().all())
