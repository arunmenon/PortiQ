"""TcoEngineService — core TCO scoring engine and split-order optimization."""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import BusinessRuleException, NotFoundException
from src.models.enums import QuoteStatus, RfqStatus, TcoCalculationStatus
from src.models.quote import Quote
from src.models.rfq import Rfq
from src.models.supplier_profile import SupplierProfile
from src.models.tco_audit_trail import TcoAuditTrail
from src.models.tco_calculation import TcoCalculation
from src.models.tco_configuration import TcoConfiguration
from src.modules.tco.constants import (
    INCOTERMS_SCORE,
    PAYMENT_TERMS_SCORE,
    SUPPLIER_TIER_QUALITY_SCORE,
)

logger = logging.getLogger(__name__)

# Missing data strategies
STRATEGY_PENALIZE = "penalize"
STRATEGY_NEUTRAL = "neutral"
STRATEGY_EXCLUDE = "exclude"


class TcoEngineService:
    """Core TCO scoring engine."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def calculate_tco(
        self,
        rfq_id: uuid.UUID,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        configuration_id: uuid.UUID | None = None,
        base_currency: str = "USD",
        missing_data_strategy: str = STRATEGY_PENALIZE,
    ) -> TcoCalculation:
        """Run a TCO calculation for an RFQ.

        Scores all SUBMITTED quotes on 6 weighted factors and ranks them.
        """
        # 1. Load RFQ and validate
        rfq = await self._load_rfq(rfq_id)
        if rfq.status not in (
            RfqStatus.BIDDING_CLOSED,
            RfqStatus.EVALUATION,
            RfqStatus.AWARDED,
            RfqStatus.COMPLETED,
        ):
            raise BusinessRuleException(
                f"TCO calculation requires RFQ in BIDDING_CLOSED or later state "
                f"(current: {rfq.status.value})"
            )

        # 2. Load configuration weights
        weights = await self._load_weights(configuration_id, organization_id)

        # 3. Load submitted quotes
        quotes = await self._load_submitted_quotes(rfq_id)
        if not quotes:
            raise BusinessRuleException("No submitted quotes found for this RFQ")

        # 4. Load supplier profiles for tier lookups
        supplier_org_ids = [q.supplier_organization_id for q in quotes]
        supplier_profiles = await self._load_supplier_profiles(supplier_org_ids)

        # 5. Create calculation record
        weights_snapshot = {k: str(v) for k, v in weights.items()}
        calculation = TcoCalculation(
            rfq_id=rfq_id,
            configuration_id=configuration_id,
            weights_snapshot=weights_snapshot,
            status=TcoCalculationStatus.CALCULATING,
            base_currency=base_currency,
            missing_data_strategy=missing_data_strategy,
        )
        self.db.add(calculation)
        await self.db.flush()

        # Audit: CALCULATION_STARTED
        self.db.add(TcoAuditTrail(
            calculation_id=calculation.id,
            rfq_id=rfq_id,
            action="CALCULATION_STARTED",
            actor_id=user_id,
            actor_organization_id=organization_id,
            details={"quote_count": len(quotes), "weights": weights_snapshot},
        ))
        await self.db.flush()

        try:
            # 6. Score each quote
            scored_quotes = self._score_quotes(
                quotes, weights, supplier_profiles, missing_data_strategy
            )

            # 7. Rank by total_score descending
            scored_quotes.sort(key=lambda q: q["total_score"], reverse=True)
            for rank, entry in enumerate(scored_quotes, start=1):
                entry["rank"] = rank

            # 8. Store results
            calculation.results = scored_quotes
            calculation.status = TcoCalculationStatus.COMPLETED

            # Audit: CALCULATION_COMPLETED
            self.db.add(TcoAuditTrail(
                calculation_id=calculation.id,
                rfq_id=rfq_id,
                action="CALCULATION_COMPLETED",
                actor_id=user_id,
                actor_organization_id=organization_id,
                details={
                    "top_quote_id": str(scored_quotes[0]["quote_id"]),
                    "top_score": scored_quotes[0]["total_score"],
                },
            ))
            await self.db.flush()

            logger.info(
                "TCO calculation %s completed for RFQ %s: %d quotes scored",
                calculation.id,
                rfq_id,
                len(scored_quotes),
            )
            return calculation

        except Exception:
            calculation.status = TcoCalculationStatus.FAILED
            await self.db.flush()
            raise

    def _score_quotes(
        self,
        quotes: list[Quote],
        weights: dict[str, Decimal],
        supplier_profiles: dict[uuid.UUID, SupplierProfile],
        missing_data_strategy: str,
    ) -> list[dict]:
        """Score all quotes across 6 factors."""
        # Pre-compute normalization ranges
        amounts = [
            float(q.total_amount) for q in quotes if q.total_amount is not None
        ]
        delivery_days = [
            q.estimated_delivery_days for q in quotes if q.estimated_delivery_days is not None
        ]

        amount_min = min(amounts) if amounts else 0
        amount_max = max(amounts) if amounts else 0
        days_min = min(delivery_days) if delivery_days else 0
        days_max = max(delivery_days) if delivery_days else 0

        results = []
        for quote in quotes:
            profile = supplier_profiles.get(quote.supplier_organization_id)
            factor_scores = []

            # Factor 1: Unit Price (inverse — lower is better)
            price_score = self._score_unit_price(
                quote.total_amount, amount_min, amount_max, missing_data_strategy
            )
            factor_scores.append({
                "factor": "unit_price",
                "raw_value": float(quote.total_amount) if quote.total_amount else 0,
                "normalized_score": price_score,
                "weight": str(weights["weight_unit_price"]),
                "weighted_score": price_score * float(weights["weight_unit_price"]),
            })

            # Factor 2: Shipping (incoterms)
            shipping_score = self._score_shipping(
                quote.shipping_terms, missing_data_strategy
            )
            factor_scores.append({
                "factor": "shipping",
                "raw_value": INCOTERMS_SCORE.get(
                    (quote.shipping_terms or "").upper(), 0
                ),
                "normalized_score": shipping_score,
                "weight": str(weights["weight_shipping"]),
                "weighted_score": shipping_score * float(weights["weight_shipping"]),
            })

            # Factor 3: Lead Time (inverse — shorter is better)
            lead_time_score = self._score_lead_time(
                quote.estimated_delivery_days, days_min, days_max, missing_data_strategy
            )
            factor_scores.append({
                "factor": "lead_time",
                "raw_value": quote.estimated_delivery_days or 0,
                "normalized_score": lead_time_score,
                "weight": str(weights["weight_lead_time"]),
                "weighted_score": lead_time_score * float(weights["weight_lead_time"]),
            })

            # Factor 4: Quality (supplier tier)
            quality_score = self._score_quality(profile, missing_data_strategy)
            factor_scores.append({
                "factor": "quality",
                "raw_value": SUPPLIER_TIER_QUALITY_SCORE.get(
                    profile.tier, 0
                ) if profile else 0,
                "normalized_score": quality_score,
                "weight": str(weights["weight_quality"]),
                "weighted_score": quality_score * float(weights["weight_quality"]),
            })

            # Factor 5: Payment Terms
            payment_score = self._score_payment_terms(
                quote.payment_terms, missing_data_strategy
            )
            factor_scores.append({
                "factor": "payment_terms",
                "raw_value": PAYMENT_TERMS_SCORE.get(
                    (quote.payment_terms or "").upper(), 0
                ),
                "normalized_score": payment_score,
                "weight": str(weights["weight_payment_terms"]),
                "weighted_score": payment_score * float(weights["weight_payment_terms"]),
            })

            # Factor 6: Supplier Rating (same tier score)
            rating_score = self._score_supplier_rating(profile, missing_data_strategy)
            factor_scores.append({
                "factor": "supplier_rating",
                "raw_value": SUPPLIER_TIER_QUALITY_SCORE.get(
                    profile.tier, 0
                ) if profile else 0,
                "normalized_score": rating_score,
                "weight": str(weights["weight_supplier_rating"]),
                "weighted_score": rating_score * float(weights["weight_supplier_rating"]),
            })

            total_score = sum(fs["weighted_score"] for fs in factor_scores)

            results.append({
                "quote_id": str(quote.id),
                "supplier_organization_id": str(quote.supplier_organization_id),
                "total_score": round(total_score, 2),
                "factor_scores": factor_scores,
                "rank": 0,
            })

        return results

    def _score_unit_price(
        self,
        total_amount: Decimal | None,
        min_amount: float,
        max_amount: float,
        strategy: str,
    ) -> float:
        """Score unit price: lower is better (inverse normalization)."""
        if total_amount is None:
            return self._missing_score(strategy)
        val = float(total_amount)
        if max_amount == min_amount:
            return 100.0
        return round(100.0 * (max_amount - val) / (max_amount - min_amount), 2)

    def _score_shipping(self, shipping_terms: str | None, strategy: str) -> float:
        """Score shipping based on incoterms lookup."""
        if not shipping_terms:
            return self._missing_score(strategy)
        score = INCOTERMS_SCORE.get(shipping_terms.upper())
        if score is None:
            return self._missing_score(strategy)
        return float(score)

    def _score_lead_time(
        self,
        days: int | None,
        min_days: int,
        max_days: int,
        strategy: str,
    ) -> float:
        """Score lead time: shorter is better (inverse normalization)."""
        if days is None:
            return self._missing_score(strategy)
        if max_days == min_days:
            return 100.0
        return round(100.0 * (max_days - days) / (max_days - min_days), 2)

    def _score_quality(
        self, profile: SupplierProfile | None, strategy: str
    ) -> float:
        """Score quality based on supplier tier."""
        if profile is None:
            return self._missing_score(strategy)
        score = SUPPLIER_TIER_QUALITY_SCORE.get(profile.tier)
        if score is None:
            return self._missing_score(strategy)
        return float(score)

    def _score_payment_terms(self, terms: str | None, strategy: str) -> float:
        """Score payment terms from lookup map."""
        if not terms:
            return self._missing_score(strategy)
        score = PAYMENT_TERMS_SCORE.get(terms.upper())
        if score is None:
            return self._missing_score(strategy)
        return float(score)

    def _score_supplier_rating(
        self, profile: SupplierProfile | None, strategy: str
    ) -> float:
        """Score supplier rating based on tier (same underlying data as quality)."""
        return self._score_quality(profile, strategy)

    @staticmethod
    def _missing_score(strategy: str) -> float:
        """Return score for missing data based on strategy."""
        if strategy == STRATEGY_PENALIZE:
            return 0.0
        if strategy == STRATEGY_NEUTRAL:
            return 50.0
        # STRATEGY_EXCLUDE: handled at weight level; for individual scores return 0
        return 0.0

    async def generate_split_order(
        self,
        calculation_id: uuid.UUID,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        max_suppliers: int = 3,
        min_allocation_percent: Decimal = Decimal("10.0"),
    ) -> TcoCalculation:
        """Generate a split-order allocation from an existing calculation."""
        result = await self.db.execute(
            select(TcoCalculation).where(TcoCalculation.id == calculation_id)
        )
        calculation = result.scalar_one_or_none()
        if calculation is None:
            raise NotFoundException(f"Calculation {calculation_id} not found")

        if calculation.status != TcoCalculationStatus.COMPLETED:
            raise BusinessRuleException(
                f"Split order requires COMPLETED calculation (current: {calculation.status.value})"
            )

        if not calculation.results:
            raise BusinessRuleException("No results in calculation to split")

        ranked_quotes = sorted(calculation.results, key=lambda q: q["rank"])

        # Limit to top N suppliers
        top_n = ranked_quotes[:max_suppliers]

        # Score-weighted allocation
        total_score = sum(q["total_score"] for q in top_n)
        if total_score == 0:
            raise BusinessRuleException("All top suppliers scored zero — cannot split")

        allocations = []
        for quote_result in top_n:
            raw_percent = (quote_result["total_score"] / total_score) * 100
            allocation_percent = max(float(min_allocation_percent), round(raw_percent, 1))
            allocations.append({
                "quote_id": quote_result["quote_id"],
                "supplier_organization_id": quote_result.get("supplier_organization_id"),
                "allocation_percent": str(allocation_percent),
                "score": quote_result["total_score"],
                "allocated_items": [],
            })

        # Normalize to sum to 100%
        alloc_sum = sum(float(a["allocation_percent"]) for a in allocations)
        if alloc_sum > 0:
            for a in allocations:
                a["allocation_percent"] = str(
                    round(float(a["allocation_percent"]) / alloc_sum * 100, 1)
                )

        # Calculate blended score
        blended_score = sum(
            q["total_score"] * float(a["allocation_percent"]) / 100
            for q, a in zip(top_n, allocations)
        )

        best_single = ranked_quotes[0]["total_score"] if ranked_quotes else 0
        strategy_notes = []
        if blended_score > best_single:
            strategy_notes.append(
                f"Split order yields {round(blended_score - best_single, 2)} points above best single supplier"
            )
        strategy_notes.append(f"Allocated across {len(allocations)} suppliers")

        split_result = {
            "allocations": allocations,
            "total_blended_score": round(blended_score, 2),
            "strategy_notes": strategy_notes,
        }

        calculation.split_order_result = split_result
        await self.db.flush()

        # Audit
        self.db.add(TcoAuditTrail(
            calculation_id=calculation.id,
            rfq_id=calculation.rfq_id,
            action="SPLIT_ORDER_GENERATED",
            actor_id=user_id,
            actor_organization_id=organization_id,
            details={
                "max_suppliers": max_suppliers,
                "supplier_count": len(allocations),
                "blended_score": round(blended_score, 2),
            },
        ))
        await self.db.flush()

        logger.info(
            "Split order generated for calculation %s: %d suppliers",
            calculation_id,
            len(allocations),
        )
        return calculation

    # ── Private data loaders ────────────────────────────────────────────

    async def _load_rfq(self, rfq_id: uuid.UUID) -> Rfq:
        result = await self.db.execute(
            select(Rfq).where(Rfq.id == rfq_id)
        )
        rfq = result.scalar_one_or_none()
        if rfq is None:
            raise NotFoundException(f"RFQ {rfq_id} not found")
        return rfq

    async def _load_weights(
        self,
        configuration_id: uuid.UUID | None,
        organization_id: uuid.UUID,
    ) -> dict[str, Decimal]:
        """Load weights from config or default."""
        if configuration_id:
            result = await self.db.execute(
                select(TcoConfiguration).where(TcoConfiguration.id == configuration_id)
            )
            config = result.scalar_one_or_none()
            if config is None:
                raise NotFoundException(f"Configuration {configuration_id} not found")
        else:
            # Try org default
            result = await self.db.execute(
                select(TcoConfiguration).where(
                    TcoConfiguration.organization_id == organization_id,
                    TcoConfiguration.is_default.is_(True),
                    TcoConfiguration.is_active.is_(True),
                )
            )
            config = result.scalar_one_or_none()

        if config:
            return {
                "weight_unit_price": Decimal(str(config.weight_unit_price)),
                "weight_shipping": Decimal(str(config.weight_shipping)),
                "weight_lead_time": Decimal(str(config.weight_lead_time)),
                "weight_quality": Decimal(str(config.weight_quality)),
                "weight_payment_terms": Decimal(str(config.weight_payment_terms)),
                "weight_supplier_rating": Decimal(str(config.weight_supplier_rating)),
            }

        # Fallback: commodity template defaults
        from src.models.enums import TcoTemplateType
        from src.modules.tco.constants import INDUSTRY_TEMPLATES

        return dict(INDUSTRY_TEMPLATES[TcoTemplateType.COMMODITY])

    async def _load_submitted_quotes(self, rfq_id: uuid.UUID) -> list[Quote]:
        result = await self.db.execute(
            select(Quote).where(
                Quote.rfq_id == rfq_id,
                Quote.status == QuoteStatus.SUBMITTED,
            )
        )
        return list(result.scalars().all())

    async def _load_supplier_profiles(
        self, org_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, SupplierProfile]:
        if not org_ids:
            return {}
        result = await self.db.execute(
            select(SupplierProfile).where(
                SupplierProfile.organization_id.in_(org_ids)
            )
        )
        profiles = result.scalars().all()
        return {p.organization_id: p for p in profiles}
