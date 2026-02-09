"""Supplier matching service — 6-stage pipeline for procurement recommendations."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.enums import OnboardingStatus, QuoteStatus, SupplierTier
from src.models.organization import Organization
from src.models.quote import Quote
from src.models.supplier_profile import SupplierProfile
from src.modules.intelligence.schemas import SupplierMatch, SupplierMatchResult

logger = logging.getLogger(__name__)

# Tier ordering for filtering and scoring
_TIER_ORDER: dict[str, int] = {
    SupplierTier.PREMIUM.value: 5,
    SupplierTier.PREFERRED.value: 4,
    SupplierTier.VERIFIED.value: 3,
    SupplierTier.BASIC.value: 2,
    SupplierTier.PENDING.value: 1,
}

# Base performance scores by tier
_TIER_SCORES: dict[str, float] = {
    SupplierTier.PREMIUM.value: 90.0,
    SupplierTier.PREFERRED.value: 75.0,
    SupplierTier.VERIFIED.value: 60.0,
    SupplierTier.BASIC.value: 40.0,
    SupplierTier.PENDING.value: 20.0,
}

_MIN_COVERAGE_SCORE = 0.3
_MIN_CANDIDATES = 3
_MAX_RECOMMENDED = 5


class SupplierMatchingService:
    """Six-stage supplier matching pipeline for procurement intelligence."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def match_suppliers(
        self,
        delivery_port: str,
        impa_codes: list[str] | None = None,
        buyer_organization_id: uuid.UUID | None = None,
        min_tier: str = "VERIFIED",
    ) -> SupplierMatchResult:
        """Execute the 6-stage supplier matching pipeline.

        Stages:
            1. Port Filter — suppliers covering the delivery port
            2. Category Match — coverage of requested IMPA categories
            3. Tier Filter — minimum tier with fallback
            4. Performance Scoring — tier-based + historical quote bonus
            5. Diversity Check — flag single-source risk
            6. Ranking — top recommended + rest as other
        """
        # Stage 1: Port Filter
        candidates = await self._stage_port_filter(delivery_port)
        logger.info("Stage 1 (Port Filter): %d candidates", len(candidates))

        # Stage 2: Category Match
        if impa_codes:
            candidates = self._stage_category_match(candidates, impa_codes)
            logger.info("Stage 2 (Category Match): %d candidates", len(candidates))

        # Stage 3: Tier Filter (with fallback)
        candidates, include_basic = self._stage_tier_filter(candidates, min_tier)
        logger.info(
            "Stage 3 (Tier Filter): %d candidates (include_basic=%s)",
            len(candidates),
            include_basic,
        )

        # Stage 4: Performance Scoring
        scored = await self._stage_performance_scoring(candidates)
        logger.info("Stage 4 (Performance Scoring): %d scored", len(scored))

        # Stage 5: Diversity Check
        single_source_risk = len(scored) <= 1

        # Stage 6: Ranking
        scored.sort(key=lambda match: match.score, reverse=True)
        recommended = scored[:_MAX_RECOMMENDED]
        other = scored[_MAX_RECOMMENDED:]

        for match in recommended:
            match.is_recommended = True

        verified_plus_count = sum(
            1
            for match in scored
            if _TIER_ORDER.get(match.tier, 0) >= _TIER_ORDER[SupplierTier.VERIFIED.value]
        )

        return SupplierMatchResult(
            total_count=len(scored),
            verified_plus_count=verified_plus_count,
            recommended=recommended,
            other=other,
            single_source_risk=single_source_risk,
        )

    # ------------------------------------------------------------------
    # Stage implementations
    # ------------------------------------------------------------------

    async def _stage_port_filter(
        self,
        delivery_port: str,
    ) -> list[_CandidateSupplier]:
        """Stage 1: Filter suppliers whose port_coverage contains the delivery port."""
        # SupplierProfile.port_coverage is a JSONB array, e.g. ["INMAA", "INBOM"]
        # We query all approved suppliers and filter in Python for JSONB array contains.
        stmt = (
            select(
                SupplierProfile.id,
                SupplierProfile.organization_id,
                SupplierProfile.tier,
                SupplierProfile.categories,
                SupplierProfile.port_coverage,
                SupplierProfile.city,
                Organization.name.label("organization_name"),
            )
            .join(Organization, SupplierProfile.organization_id == Organization.id)
            .where(SupplierProfile.onboarding_status == OnboardingStatus.APPROVED)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        candidates = []
        for row in rows:
            port_coverage = row.port_coverage or []
            city = row.city or ""

            # Match either by port_coverage array or city name
            port_matches = (
                delivery_port in port_coverage
                or delivery_port.upper() in [p.upper() for p in port_coverage]
                or city.upper() == delivery_port.upper()
            )
            if port_matches:
                candidates.append(
                    _CandidateSupplier(
                        supplier_id=row.id,
                        organization_id=row.organization_id,
                        organization_name=row.organization_name,
                        tier=row.tier.value if hasattr(row.tier, "value") else str(row.tier),
                        categories=row.categories or [],
                        coverage_score=1.0,
                    )
                )

        return candidates

    def _stage_category_match(
        self,
        candidates: list[_CandidateSupplier],
        impa_codes: list[str],
    ) -> list[_CandidateSupplier]:
        """Stage 2: Score each candidate on category coverage of requested IMPA codes.

        SupplierProfile.categories is a JSONB array of category names/codes.
        We compute coverage_score = intersection / total requested.
        Filter where coverage_score >= MIN_COVERAGE_SCORE.
        """
        if not impa_codes:
            return candidates

        # Extract IMPA category prefixes (first 2 digits = category group)
        requested_categories = set()
        for code in impa_codes:
            if len(code) >= 2:
                requested_categories.add(code[:2])

        if not requested_categories:
            return candidates

        filtered = []
        for candidate in candidates:
            supplier_categories = set()
            for cat in candidate.categories:
                if isinstance(cat, str) and len(cat) >= 2:
                    supplier_categories.add(cat[:2])
                elif isinstance(cat, dict):
                    cat_code = cat.get("code", cat.get("impa_prefix", ""))
                    if len(str(cat_code)) >= 2:
                        supplier_categories.add(str(cat_code)[:2])

            if not supplier_categories:
                # If supplier has no categories listed, give benefit of the doubt
                candidate.coverage_score = 0.5
                filtered.append(candidate)
                continue

            overlap = requested_categories & supplier_categories
            coverage_score = len(overlap) / len(requested_categories)
            candidate.coverage_score = coverage_score

            if coverage_score >= _MIN_COVERAGE_SCORE:
                filtered.append(candidate)

        return filtered

    def _stage_tier_filter(
        self,
        candidates: list[_CandidateSupplier],
        min_tier: str,
    ) -> tuple[list[_CandidateSupplier], bool]:
        """Stage 3: Filter by minimum tier, with fallback to BASIC if too few candidates."""
        min_tier_order = _TIER_ORDER.get(min_tier, _TIER_ORDER[SupplierTier.VERIFIED.value])

        filtered = [
            c for c in candidates if _TIER_ORDER.get(c.tier, 0) >= min_tier_order
        ]

        # Fallback: include BASIC if fewer than minimum candidates
        include_basic = False
        if len(filtered) < _MIN_CANDIDATES and min_tier_order > _TIER_ORDER[SupplierTier.BASIC.value]:
            filtered = [
                c
                for c in candidates
                if _TIER_ORDER.get(c.tier, 0) >= _TIER_ORDER[SupplierTier.BASIC.value]
            ]
            include_basic = True

        return filtered, include_basic

    async def _stage_performance_scoring(
        self,
        candidates: list[_CandidateSupplier],
    ) -> list[SupplierMatch]:
        """Stage 4: Score suppliers based on tier + historical quote activity."""
        if not candidates:
            return []

        # Fetch historical quote counts for candidate organizations
        org_ids = [c.organization_id for c in candidates]
        quote_count_stmt = (
            select(
                Quote.supplier_organization_id,
                func.count(Quote.id).label("quote_count"),
            )
            .where(
                Quote.supplier_organization_id.in_(org_ids),
                Quote.status.in_((QuoteStatus.SUBMITTED, QuoteStatus.AWARDED)),
            )
            .group_by(Quote.supplier_organization_id)
        )

        result = await self.db.execute(quote_count_stmt)
        quote_counts: dict[uuid.UUID, int] = {
            row.supplier_organization_id: row.quote_count for row in result.all()
        }

        matches = []
        for candidate in candidates:
            tier_score = _TIER_SCORES.get(candidate.tier, 20.0)
            historical_quotes = quote_counts.get(candidate.organization_id, 0)
            # Quote bonus: up to +10 points, scales with log-ish growth
            quote_bonus = min(10.0, historical_quotes * 2.0)
            total_score = tier_score + quote_bonus

            matches.append(
                SupplierMatch(
                    supplier_id=candidate.supplier_id,
                    organization_id=candidate.organization_id,
                    organization_name=candidate.organization_name,
                    tier=candidate.tier,
                    score=round(total_score, 2),
                    coverage_score=round(candidate.coverage_score, 2),
                    is_recommended=False,
                )
            )

        return matches


class _CandidateSupplier:
    """Internal data class for pipeline candidates."""

    __slots__ = (
        "supplier_id",
        "organization_id",
        "organization_name",
        "tier",
        "categories",
        "coverage_score",
    )

    def __init__(
        self,
        supplier_id: uuid.UUID,
        organization_id: uuid.UUID,
        organization_name: str,
        tier: str,
        categories: list,
        coverage_score: float = 1.0,
    ) -> None:
        self.supplier_id = supplier_id
        self.organization_id = organization_id
        self.organization_name = organization_name
        self.tier = tier
        self.categories = categories
        self.coverage_score = coverage_score
