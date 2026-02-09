"""Tests for TcoEngineService — scoring normalization, calculation, and split order."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.enums import (
    QuoteStatus,
    RfqStatus,
    SupplierTier,
    TcoCalculationStatus,
)
from src.models.quote import Quote
from src.models.rfq import Rfq
from src.models.supplier_profile import SupplierProfile
from src.models.tco_calculation import TcoCalculation
from src.modules.tco.engine import (
    STRATEGY_NEUTRAL,
    STRATEGY_PENALIZE,
    TcoEngineService,
)


def _make_quote(
    rfq_id: uuid.UUID,
    supplier_org_id: uuid.UUID | None = None,
    total_amount: Decimal | None = Decimal("1000.00"),
    estimated_delivery_days: int | None = 14,
    shipping_terms: str | None = "CIF",
    payment_terms: str | None = "NET30",
    status: QuoteStatus = QuoteStatus.SUBMITTED,
) -> MagicMock:
    q = MagicMock(spec=Quote)
    q.id = uuid.uuid4()
    q.rfq_id = rfq_id
    q.supplier_organization_id = supplier_org_id or uuid.uuid4()
    q.total_amount = total_amount
    q.estimated_delivery_days = estimated_delivery_days
    q.shipping_terms = shipping_terms
    q.payment_terms = payment_terms
    q.status = status
    return q


def _make_rfq(
    buyer_org_id: uuid.UUID | None = None,
    status: RfqStatus = RfqStatus.EVALUATION,
) -> MagicMock:
    rfq = MagicMock(spec=Rfq)
    rfq.id = uuid.uuid4()
    rfq.buyer_organization_id = buyer_org_id or uuid.uuid4()
    rfq.status = status
    return rfq


def _make_supplier_profile(
    org_id: uuid.UUID, tier: SupplierTier = SupplierTier.VERIFIED
) -> MagicMock:
    sp = MagicMock(spec=SupplierProfile)
    sp.organization_id = org_id
    sp.tier = tier
    return sp


class TestScoreUnitPrice:
    """Tests for unit price scoring (inverse normalization)."""

    def setup_method(self) -> None:
        self.engine = TcoEngineService(AsyncMock())

    def test_single_quote_scores_100(self) -> None:
        score = self.engine._score_unit_price(
            Decimal("500"), 500.0, 500.0, STRATEGY_PENALIZE
        )
        assert score == 100.0

    def test_cheapest_scores_100(self) -> None:
        score = self.engine._score_unit_price(
            Decimal("100"), 100.0, 500.0, STRATEGY_PENALIZE
        )
        assert score == 100.0

    def test_most_expensive_scores_0(self) -> None:
        score = self.engine._score_unit_price(
            Decimal("500"), 100.0, 500.0, STRATEGY_PENALIZE
        )
        assert score == 0.0

    def test_midpoint_scores_50(self) -> None:
        score = self.engine._score_unit_price(
            Decimal("300"), 100.0, 500.0, STRATEGY_PENALIZE
        )
        assert score == 50.0

    def test_missing_amount_penalize(self) -> None:
        score = self.engine._score_unit_price(None, 100.0, 500.0, STRATEGY_PENALIZE)
        assert score == 0.0

    def test_missing_amount_neutral(self) -> None:
        score = self.engine._score_unit_price(None, 100.0, 500.0, STRATEGY_NEUTRAL)
        assert score == 50.0


class TestScoreShipping:
    """Tests for shipping (incoterms) scoring."""

    def setup_method(self) -> None:
        self.engine = TcoEngineService(AsyncMock())

    def test_ddp_scores_100(self) -> None:
        assert self.engine._score_shipping("DDP", STRATEGY_PENALIZE) == 100.0

    def test_fob_scores_50(self) -> None:
        assert self.engine._score_shipping("FOB", STRATEGY_PENALIZE) == 50.0

    def test_exw_scores_20(self) -> None:
        assert self.engine._score_shipping("EXW", STRATEGY_PENALIZE) == 20.0

    def test_missing_penalize(self) -> None:
        assert self.engine._score_shipping(None, STRATEGY_PENALIZE) == 0.0

    def test_case_insensitive(self) -> None:
        assert self.engine._score_shipping("cif", STRATEGY_PENALIZE) == 85.0


class TestScoreLeadTime:
    """Tests for lead time scoring (inverse normalization)."""

    def setup_method(self) -> None:
        self.engine = TcoEngineService(AsyncMock())

    def test_shortest_scores_100(self) -> None:
        score = self.engine._score_lead_time(7, 7, 30, STRATEGY_PENALIZE)
        assert score == 100.0

    def test_longest_scores_0(self) -> None:
        score = self.engine._score_lead_time(30, 7, 30, STRATEGY_PENALIZE)
        assert score == 0.0


class TestScoreQuotes:
    """Tests for full quote scoring pipeline."""

    def setup_method(self) -> None:
        self.engine = TcoEngineService(AsyncMock())
        self.rfq_id = uuid.uuid4()

    def test_single_quote_ranks_first(self) -> None:
        org_id = uuid.uuid4()
        quotes = [_make_quote(self.rfq_id, supplier_org_id=org_id)]
        profiles = {org_id: _make_supplier_profile(org_id)}
        weights = {
            "weight_unit_price": Decimal("0.4"),
            "weight_shipping": Decimal("0.15"),
            "weight_lead_time": Decimal("0.15"),
            "weight_quality": Decimal("0.15"),
            "weight_payment_terms": Decimal("0.10"),
            "weight_supplier_rating": Decimal("0.05"),
        }

        results = self.engine._score_quotes(quotes, weights, profiles, STRATEGY_PENALIZE)
        assert len(results) == 1
        assert results[0]["total_score"] > 0

    def test_cheaper_quote_ranks_higher(self) -> None:
        org_a = uuid.uuid4()
        org_b = uuid.uuid4()
        quotes = [
            _make_quote(self.rfq_id, supplier_org_id=org_a, total_amount=Decimal("500")),
            _make_quote(self.rfq_id, supplier_org_id=org_b, total_amount=Decimal("1000")),
        ]
        profiles = {
            org_a: _make_supplier_profile(org_a, SupplierTier.VERIFIED),
            org_b: _make_supplier_profile(org_b, SupplierTier.VERIFIED),
        }
        weights = {
            "weight_unit_price": Decimal("0.90"),
            "weight_shipping": Decimal("0.02"),
            "weight_lead_time": Decimal("0.02"),
            "weight_quality": Decimal("0.02"),
            "weight_payment_terms": Decimal("0.02"),
            "weight_supplier_rating": Decimal("0.02"),
        }

        results = self.engine._score_quotes(quotes, weights, profiles, STRATEGY_PENALIZE)
        results.sort(key=lambda q: q["total_score"], reverse=True)

        # Quote A (cheaper) should rank higher
        assert results[0]["quote_id"] == str(quotes[0].id)

    def test_missing_data_penalize_vs_neutral(self) -> None:
        org_id = uuid.uuid4()
        # Quote with all missing optional fields
        quotes = [
            _make_quote(
                self.rfq_id,
                supplier_org_id=org_id,
                total_amount=Decimal("100"),
                estimated_delivery_days=None,
                shipping_terms=None,
                payment_terms=None,
            ),
        ]
        profiles = {}
        weights = {
            "weight_unit_price": Decimal("0.40"),
            "weight_shipping": Decimal("0.15"),
            "weight_lead_time": Decimal("0.15"),
            "weight_quality": Decimal("0.15"),
            "weight_payment_terms": Decimal("0.10"),
            "weight_supplier_rating": Decimal("0.05"),
        }

        penalize_results = self.engine._score_quotes(
            quotes, weights, profiles, STRATEGY_PENALIZE
        )
        neutral_results = self.engine._score_quotes(
            quotes, weights, profiles, STRATEGY_NEUTRAL
        )

        # Neutral should score higher due to 50 for missing vs 0
        assert neutral_results[0]["total_score"] > penalize_results[0]["total_score"]


class TestCalculateTco:
    """Integration-style tests for calculate_tco."""

    @pytest.mark.asyncio
    async def test_rejects_draft_rfq(self) -> None:
        db = AsyncMock()
        rfq = _make_rfq(status=RfqStatus.DRAFT)

        # _load_rfq returns the draft RFQ
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = rfq
        db.execute.return_value = mock_result

        engine = TcoEngineService(db)
        from src.exceptions import BusinessRuleException

        with pytest.raises(BusinessRuleException, match="BIDDING_CLOSED or later"):
            await engine.calculate_tco(
                rfq_id=rfq.id,
                user_id=uuid.uuid4(),
                organization_id=rfq.buyer_organization_id,
            )


class TestGenerateSplitOrder:
    """Tests for split-order generation."""

    @pytest.mark.asyncio
    async def test_rejects_non_completed_calculation(self) -> None:
        db = AsyncMock()
        calc = MagicMock(spec=TcoCalculation)
        calc.id = uuid.uuid4()
        calc.status = TcoCalculationStatus.PENDING
        calc.results = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = calc
        db.execute.return_value = mock_result

        engine = TcoEngineService(db)
        from src.exceptions import BusinessRuleException

        with pytest.raises(BusinessRuleException, match="COMPLETED calculation"):
            await engine.generate_split_order(
                calculation_id=calc.id,
                user_id=uuid.uuid4(),
                organization_id=uuid.uuid4(),
            )

    @pytest.mark.asyncio
    async def test_split_order_normalizes_to_100(self) -> None:
        db = AsyncMock()
        calc = MagicMock(spec=TcoCalculation)
        calc.id = uuid.uuid4()
        calc.rfq_id = uuid.uuid4()
        calc.status = TcoCalculationStatus.COMPLETED
        calc.results = [
            {"quote_id": str(uuid.uuid4()), "total_score": 80.0, "rank": 1},
            {"quote_id": str(uuid.uuid4()), "total_score": 60.0, "rank": 2},
            {"quote_id": str(uuid.uuid4()), "total_score": 40.0, "rank": 3},
        ]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = calc
        db.execute.return_value = mock_result

        engine = TcoEngineService(db)
        result = await engine.generate_split_order(
            calculation_id=calc.id,
            user_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            max_suppliers=3,
        )

        alloc_sum = sum(
            float(a["allocation_percent"])
            for a in result.split_order_result["allocations"]
        )
        assert abs(alloc_sum - 100.0) < 0.5
