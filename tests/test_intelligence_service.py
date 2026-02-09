"""Tests for Market Intelligence Service — price benchmarks, supplier matching,
risk analysis, timing advice, and the combined endpoint.

Uses mock AsyncSession pattern with patched DB queries.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.intelligence.price_benchmark_service import PriceBenchmarkService
from src.modules.intelligence.risk_analyzer import RiskAnalyzer
from src.modules.intelligence.schemas import (
    BudgetEstimate,
    IntelligenceResponse,
    PriceBenchmark,
    RiskFlag,
    SupplierMatchResult,
    TimingAdvice,
)
from src.modules.intelligence.supplier_matching import (
    SupplierMatchingService,
    _CandidateSupplier,
)
from src.modules.intelligence.timing_advisor import TimingAdvisor

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_db():
    """Create a mock AsyncSession."""
    session = AsyncMock()
    return session


def _make_uuid() -> uuid.UUID:
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# Price Benchmark Service Tests
# ---------------------------------------------------------------------------


class TestPriceBenchmarkService:
    """Tests for PriceBenchmarkService."""

    @pytest.mark.asyncio
    async def test_empty_impa_codes_returns_empty(self, mock_db):
        svc = PriceBenchmarkService(mock_db)
        result = await svc.get_price_benchmarks(impa_codes=[])
        assert result == []

    @pytest.mark.asyncio
    async def test_benchmark_with_insufficient_quotes(self, mock_db):
        """When fewer than min quotes, has_data should be False."""
        # Mock the execute to return only 1 price (below threshold of 3)
        mock_result = MagicMock()
        mock_result.all.return_value = [(Decimal("10.00"),)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        svc = PriceBenchmarkService(mock_db)
        with patch("src.modules.intelligence.price_benchmark_service.settings") as mock_settings:
            mock_settings.intelligence_price_benchmark_days = 90
            mock_settings.intelligence_min_quotes_for_benchmark = 3
            result = await svc.get_price_benchmarks(impa_codes=["123456"])

        assert len(result) == 1
        assert result[0].impa_code == "123456"
        assert result[0].has_data is False
        assert result[0].quote_count == 1

    @pytest.mark.asyncio
    async def test_benchmark_with_sufficient_quotes(self, mock_db):
        """When enough quotes, percentiles should be computed."""
        prices = [
            (Decimal("10.00"),),
            (Decimal("20.00"),),
            (Decimal("30.00"),),
            (Decimal("40.00"),),
            (Decimal("50.00"),),
        ]

        # First call returns prices, second call returns currency
        price_result = MagicMock()
        price_result.all.return_value = prices
        currency_result = MagicMock()
        currency_result.first.return_value = ("USD",)

        mock_db.execute = AsyncMock(side_effect=[price_result, currency_result])

        svc = PriceBenchmarkService(mock_db)
        with patch("src.modules.intelligence.price_benchmark_service.settings") as mock_settings:
            mock_settings.intelligence_price_benchmark_days = 90
            mock_settings.intelligence_min_quotes_for_benchmark = 3
            result = await svc.get_price_benchmarks(impa_codes=["123456"])

        assert len(result) == 1
        benchmark = result[0]
        assert benchmark.impa_code == "123456"
        assert benchmark.has_data is True
        assert benchmark.quote_count == 5
        assert benchmark.p25 is not None
        assert benchmark.p50 is not None
        assert benchmark.p75 is not None
        # P50 should be the median (30.00 for sorted [10,20,30,40,50])
        assert benchmark.p50 == Decimal("30.00")

    @pytest.mark.asyncio
    async def test_budget_estimation_math(self, mock_db):
        """Budget estimate should multiply prices by quantities."""
        svc = PriceBenchmarkService(mock_db)

        # Mock get_price_benchmarks to return known benchmarks
        benchmark = PriceBenchmark(
            impa_code="123456",
            p25=Decimal("10.00"),
            p50=Decimal("20.00"),
            p75=Decimal("30.00"),
            quote_count=5,
            has_data=True,
            currency="USD",
            period_days=90,
        )
        with patch.object(svc, "get_price_benchmarks", return_value=[benchmark]):
            result = await svc.estimate_budget(
                line_items=[{"impa_code": "123456", "quantity": 5}],
            )

        assert isinstance(result, BudgetEstimate)
        assert result.low == Decimal("50.00")   # 5 * 10
        assert result.likely == Decimal("100.00")  # 5 * 20
        assert result.high == Decimal("150.00")  # 5 * 30
        assert result.items_with_data == 1
        assert result.items_without_data == 0
        assert result.currency == "USD"

    @pytest.mark.asyncio
    async def test_budget_estimation_with_missing_data(self, mock_db):
        """Items without benchmarks should be counted as items_without_data."""
        svc = PriceBenchmarkService(mock_db)

        no_data_benchmark = PriceBenchmark(
            impa_code="999999",
            has_data=False,
            quote_count=0,
            period_days=90,
        )
        with patch.object(svc, "get_price_benchmarks", return_value=[no_data_benchmark]):
            result = await svc.estimate_budget(
                line_items=[{"impa_code": "999999", "quantity": 10}],
            )

        assert result.items_with_data == 0
        assert result.items_without_data == 1
        assert result.low == Decimal("0")
        assert result.likely == Decimal("0")

    def test_percentile_calculation(self):
        """Test the static percentile method."""
        values = [Decimal("10"), Decimal("20"), Decimal("30"), Decimal("40"), Decimal("50")]
        result = PriceBenchmarkService._percentile(values, 0.5)
        assert result == Decimal("30")

        result_p25 = PriceBenchmarkService._percentile(values, 0.25)
        assert result_p25 == Decimal("20")

        result_p75 = PriceBenchmarkService._percentile(values, 0.75)
        assert result_p75 == Decimal("40")

    def test_percentile_single_value(self):
        """Single-value list should return that value for any percentile."""
        values = [Decimal("42")]
        assert PriceBenchmarkService._percentile(values, 0.5) == Decimal("42")

    def test_percentile_empty_list(self):
        """Empty list should return zero."""
        assert PriceBenchmarkService._percentile([], 0.5) == Decimal("0")


# ---------------------------------------------------------------------------
# Supplier Matching Service Tests
# ---------------------------------------------------------------------------


class TestSupplierMatchingService:
    """Tests for the 6-stage supplier matching pipeline."""

    @pytest.mark.asyncio
    async def test_port_filter_with_matching_suppliers(self, mock_db):
        """Stage 1: Suppliers with port_coverage matching delivery port should pass."""
        org_id = _make_uuid()
        supplier_id = _make_uuid()

        row = MagicMock()
        row.id = supplier_id
        row.organization_id = org_id
        row.tier = MagicMock(value="VERIFIED")
        row.categories = ["12", "34"]
        row.port_coverage = ["INMAA", "INBOM"]
        row.city = "Chennai"
        row.organization_name = "Test Supplier"

        mock_result = MagicMock()
        mock_result.all.return_value = [row]
        mock_db.execute = AsyncMock(return_value=mock_result)

        svc = SupplierMatchingService(mock_db)
        candidates = await svc._stage_port_filter("INMAA")

        assert len(candidates) == 1
        assert candidates[0].organization_id == org_id

    @pytest.mark.asyncio
    async def test_port_filter_no_match(self, mock_db):
        """Stage 1: Suppliers without matching port should be filtered out."""
        row = MagicMock()
        row.id = _make_uuid()
        row.organization_id = _make_uuid()
        row.tier = MagicMock(value="VERIFIED")
        row.categories = []
        row.port_coverage = ["SGSIN"]
        row.city = "Singapore"
        row.organization_name = "Singapore Supplier"

        mock_result = MagicMock()
        mock_result.all.return_value = [row]
        mock_db.execute = AsyncMock(return_value=mock_result)

        svc = SupplierMatchingService(mock_db)
        candidates = await svc._stage_port_filter("INMAA")

        assert len(candidates) == 0

    def test_category_match_scores_correctly(self):
        """Stage 2: Coverage score = intersection / total."""
        svc = SupplierMatchingService(MagicMock())

        candidate = _CandidateSupplier(
            supplier_id=_make_uuid(),
            organization_id=_make_uuid(),
            organization_name="Test",
            tier="VERIFIED",
            categories=["12", "34", "56"],
        )

        result = svc._stage_category_match([candidate], ["120001", "340002", "780003"])
        # Supplier has categories 12, 34 matching 2 out of 3 requested prefixes
        assert len(result) == 1
        assert result[0].coverage_score == pytest.approx(2 / 3, abs=0.01)

    def test_category_match_filters_low_coverage(self):
        """Stage 2: Suppliers with coverage < 0.3 should be filtered."""
        svc = SupplierMatchingService(MagicMock())

        candidate = _CandidateSupplier(
            supplier_id=_make_uuid(),
            organization_id=_make_uuid(),
            organization_name="Test",
            tier="VERIFIED",
            categories=["99"],
        )

        # Only 1 category, none matching the requested ones
        result = svc._stage_category_match(
            [candidate], ["120001", "340002", "560003", "780004"]
        )
        assert len(result) == 0

    def test_tier_filter_verified_default(self):
        """Stage 3: Default filter should keep VERIFIED+ suppliers."""
        svc = SupplierMatchingService(MagicMock())

        candidates = [
            _CandidateSupplier(
                supplier_id=_make_uuid(),
                organization_id=_make_uuid(),
                organization_name="Basic",
                tier="BASIC",
                categories=[],
            ),
            _CandidateSupplier(
                supplier_id=_make_uuid(),
                organization_id=_make_uuid(),
                organization_name="Verified",
                tier="VERIFIED",
                categories=[],
            ),
            _CandidateSupplier(
                supplier_id=_make_uuid(),
                organization_id=_make_uuid(),
                organization_name="Premium",
                tier="PREMIUM",
                categories=[],
            ),
        ]

        filtered, include_basic = svc._stage_tier_filter(candidates, "VERIFIED")
        tier_names = [c.organization_name for c in filtered]
        assert "Verified" in tier_names
        assert "Premium" in tier_names
        assert "Basic" not in tier_names
        assert include_basic is False

    def test_tier_filter_fallback_to_basic(self):
        """Stage 3: If fewer than 3 candidates, fallback to include BASIC."""
        svc = SupplierMatchingService(MagicMock())

        candidates = [
            _CandidateSupplier(
                supplier_id=_make_uuid(),
                organization_id=_make_uuid(),
                organization_name="Basic",
                tier="BASIC",
                categories=[],
            ),
            _CandidateSupplier(
                supplier_id=_make_uuid(),
                organization_id=_make_uuid(),
                organization_name="Verified",
                tier="VERIFIED",
                categories=[],
            ),
        ]

        # Only 1 VERIFIED, which is < 3 threshold
        filtered, include_basic = svc._stage_tier_filter(candidates, "VERIFIED")
        assert len(filtered) == 2
        assert include_basic is True

    @pytest.mark.asyncio
    async def test_performance_scoring(self, mock_db):
        """Stage 4: Scores should reflect tier + quote bonus."""
        candidates = [
            _CandidateSupplier(
                supplier_id=_make_uuid(),
                organization_id=_make_uuid(),
                organization_name="Premium Supplier",
                tier="PREMIUM",
                categories=[],
            ),
        ]

        # Mock quote count query
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.supplier_organization_id = candidates[0].organization_id
        mock_row.quote_count = 3
        mock_result.all.return_value = [mock_row]
        mock_db.execute = AsyncMock(return_value=mock_result)

        svc = SupplierMatchingService(mock_db)
        matches = await svc._stage_performance_scoring(candidates)

        assert len(matches) == 1
        # Premium base = 90, quote bonus = min(10, 3*2) = 6
        assert matches[0].score == 96.0
        assert matches[0].tier == "PREMIUM"

    @pytest.mark.asyncio
    async def test_full_pipeline_single_source_risk(self, mock_db):
        """Diversity check: 1 supplier = single source risk."""
        org_id = _make_uuid()
        supplier_id = _make_uuid()

        # Stage 1 mock
        row = MagicMock()
        row.id = supplier_id
        row.organization_id = org_id
        row.tier = MagicMock(value="VERIFIED")
        row.categories = []
        row.port_coverage = ["INMAA"]
        row.city = "Chennai"
        row.organization_name = "Only Supplier"

        stage1_result = MagicMock()
        stage1_result.all.return_value = [row]

        # Stage 4 mock (quote counts)
        stage4_result = MagicMock()
        stage4_result.all.return_value = []

        mock_db.execute = AsyncMock(side_effect=[stage1_result, stage4_result])

        svc = SupplierMatchingService(mock_db)
        result = await svc.match_suppliers(delivery_port="INMAA")

        assert result.single_source_risk is True
        assert result.total_count == 1


# ---------------------------------------------------------------------------
# Risk Analyzer Tests
# ---------------------------------------------------------------------------


class TestRiskAnalyzer:
    """Tests for the RiskAnalyzer."""

    @pytest.mark.asyncio
    async def test_tight_timeline_high_severity(self, mock_db):
        """Delivery in 3 days should trigger HIGH severity."""
        svc = RiskAnalyzer(mock_db)
        delivery_date = datetime.now(tz=UTC) + timedelta(days=3)
        flag = svc._check_tight_timeline(delivery_date)
        assert flag is not None
        assert flag.risk_type == "TIGHT_TIMELINE"
        assert flag.severity == "HIGH"

    @pytest.mark.asyncio
    async def test_tight_timeline_medium_severity(self, mock_db):
        """Delivery in 10 days should trigger MEDIUM severity."""
        svc = RiskAnalyzer(mock_db)
        delivery_date = datetime.now(tz=UTC) + timedelta(days=10)
        flag = svc._check_tight_timeline(delivery_date)
        assert flag is not None
        assert flag.risk_type == "TIGHT_TIMELINE"
        assert flag.severity == "MEDIUM"

    @pytest.mark.asyncio
    async def test_tight_timeline_no_flag(self, mock_db):
        """Delivery in 30 days should not trigger a flag."""
        svc = RiskAnalyzer(mock_db)
        delivery_date = datetime.now(tz=UTC) + timedelta(days=30)
        flag = svc._check_tight_timeline(delivery_date)
        assert flag is None

    @pytest.mark.asyncio
    async def test_single_source_risk(self, mock_db):
        """Only 1 supplier at port should flag SINGLE_SOURCE."""
        # First query: total approved count
        count_result = MagicMock()
        count_result.scalar.return_value = 5

        # Second query: port coverage check
        port_result = MagicMock()
        row1 = (["INMAA", "INBOM"],)
        port_result.all.return_value = [row1]

        mock_db.execute = AsyncMock(side_effect=[count_result, port_result])

        svc = RiskAnalyzer(mock_db)
        flag = await svc._check_single_source("INMAA", ["123456"])

        assert flag is not None
        assert flag.risk_type == "SINGLE_SOURCE"
        assert flag.severity == "HIGH"

    @pytest.mark.asyncio
    async def test_no_price_history_risk(self, mock_db):
        """When >50% items lack pricing, should flag NO_PRICE_HISTORY."""
        # Mock: all items return 0 quotes
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        mock_db.execute = AsyncMock(return_value=count_result)

        svc = RiskAnalyzer(mock_db)
        with patch("src.modules.intelligence.risk_analyzer.settings") as mock_settings:
            mock_settings.intelligence_price_benchmark_days = 90
            mock_settings.intelligence_min_quotes_for_benchmark = 3
            flag = await svc._check_no_price_history(
                ["123456", "234567", "345678"], "INMAA"
            )

        assert flag is not None
        assert flag.risk_type == "NO_PRICE_HISTORY"
        assert flag.severity == "MEDIUM"

    @pytest.mark.asyncio
    async def test_new_category_risk(self, mock_db):
        """Buyer ordering from a new IMPA category should flag NEW_CATEGORY."""
        # Historical: buyer has ordered from prefix "12" only
        historical_result = MagicMock()
        historical_result.all.return_value = [("120001",)]
        mock_db.execute = AsyncMock(return_value=historical_result)

        svc = RiskAnalyzer(mock_db)
        buyer_id = _make_uuid()
        flag = await svc._check_new_category(["340001"], buyer_id)

        assert flag is not None
        assert flag.risk_type == "NEW_CATEGORY"
        assert flag.severity == "LOW"
        assert "34" in flag.details["new_category_prefixes"]

    @pytest.mark.asyncio
    async def test_suspended_suppliers_risk(self, mock_db):
        """Previously used but now suspended suppliers should flag."""
        # Mock: invited org IDs
        invited_result = MagicMock()
        org_id = _make_uuid()
        invited_result.all.return_value = [(org_id,)]

        # Mock: suspended count
        suspended_result = MagicMock()
        suspended_result.scalar.return_value = 1

        mock_db.execute = AsyncMock(side_effect=[invited_result, suspended_result])

        svc = RiskAnalyzer(mock_db)
        flag = await svc._check_suspended_suppliers(_make_uuid())

        assert flag is not None
        assert flag.risk_type == "SUSPENDED_SUPPLIERS"
        assert flag.severity == "MEDIUM"

    @pytest.mark.asyncio
    async def test_low_response_port_risk(self, mock_db):
        """Port with <50% response ratio should flag LOW_RESPONSE_PORT."""
        invite_result = MagicMock()
        invite_result.scalar.return_value = 10

        quote_result = MagicMock()
        quote_result.scalar.return_value = 3  # 30% ratio

        mock_db.execute = AsyncMock(side_effect=[invite_result, quote_result])

        svc = RiskAnalyzer(mock_db)
        flag = await svc._check_low_response_port("INMAA")

        assert flag is not None
        assert flag.risk_type == "LOW_RESPONSE_PORT"
        assert flag.severity == "MEDIUM"
        assert flag.details["response_ratio"] == 0.3

    @pytest.mark.asyncio
    async def test_low_response_port_no_invitations(self, mock_db):
        """Port with zero invitations should not flag."""
        invite_result = MagicMock()
        invite_result.scalar.return_value = 0
        mock_db.execute = AsyncMock(return_value=invite_result)

        svc = RiskAnalyzer(mock_db)
        flag = await svc._check_low_response_port("XXXXX")
        assert flag is None

    @pytest.mark.asyncio
    async def test_analyze_risks_combines_flags(self, mock_db):
        """The main analyze_risks should combine all applicable risk checks."""
        svc = RiskAnalyzer(mock_db)

        # Patch each individual check to return known flags
        with (
            patch.object(
                svc,
                "_check_single_source",
                return_value=RiskFlag(
                    risk_type="SINGLE_SOURCE",
                    severity="HIGH",
                    message="Only 1 supplier",
                ),
            ),
            patch.object(
                svc,
                "_check_no_price_history",
                return_value=RiskFlag(
                    risk_type="NO_PRICE_HISTORY",
                    severity="MEDIUM",
                    message="No data",
                ),
            ),
            patch.object(svc, "_check_unusual_quantity", return_value=[]),
            patch.object(svc, "_check_new_category", return_value=None),
            patch.object(svc, "_check_suspended_suppliers", return_value=None),
            patch.object(svc, "_check_low_response_port", return_value=None),
        ):
            flags = await svc.analyze_risks(
                delivery_port="INMAA",
                delivery_date=datetime.now(tz=UTC) + timedelta(days=30),
                impa_codes=["123456"],
                buyer_organization_id=_make_uuid(),
            )

        risk_types = [f.risk_type for f in flags]
        assert "SINGLE_SOURCE" in risk_types
        assert "NO_PRICE_HISTORY" in risk_types


# ---------------------------------------------------------------------------
# Timing Advisor Tests
# ---------------------------------------------------------------------------


class TestTimingAdvisor:
    """Tests for the TimingAdvisor."""

    @pytest.mark.asyncio
    async def test_timing_sufficient_window(self, mock_db):
        """Delivery 30 days out should be assessed as sufficient."""
        svc = TimingAdvisor(mock_db)

        # Patch ETA and response time lookups
        with (
            patch.object(svc, "_get_vessel_eta", return_value=None),
            patch.object(svc, "_get_avg_response_days", return_value=3.5),
        ):
            result = await svc.get_timing_advice(
                delivery_port="INMAA",
                delivery_date=datetime.now(tz=UTC) + timedelta(days=30),
            )

        assert result.timeline_assessment == "sufficient"
        assert result.avg_response_days == 3.5
        assert result.optimal_window_days >= 3

    @pytest.mark.asyncio
    async def test_timing_tight_window(self, mock_db):
        """Delivery 10 days out should be assessed as tight."""
        svc = TimingAdvisor(mock_db)

        with (
            patch.object(svc, "_get_vessel_eta", return_value=None),
            patch.object(svc, "_get_avg_response_days", return_value=None),
        ):
            result = await svc.get_timing_advice(
                delivery_port="INMAA",
                delivery_date=datetime.now(tz=UTC) + timedelta(days=10),
            )

        assert result.timeline_assessment == "tight"

    @pytest.mark.asyncio
    async def test_timing_risky_window(self, mock_db):
        """Delivery 3 days out should be assessed as risky."""
        svc = TimingAdvisor(mock_db)

        with (
            patch.object(svc, "_get_vessel_eta", return_value=None),
            patch.object(svc, "_get_avg_response_days", return_value=None),
        ):
            result = await svc.get_timing_advice(
                delivery_port="INMAA",
                delivery_date=datetime.now(tz=UTC) + timedelta(days=3),
            )

        assert result.timeline_assessment == "risky"
        assert "tight" in result.recommendation.lower() or "risky" in result.recommendation.lower()

    @pytest.mark.asyncio
    async def test_timing_with_vessel_eta(self, mock_db):
        """Vessel ETA should be included in the response."""
        svc = TimingAdvisor(mock_db)
        eta = datetime.now(tz=UTC) + timedelta(days=5)

        with (
            patch.object(svc, "_get_vessel_eta", return_value=eta),
            patch.object(svc, "_get_avg_response_days", return_value=2.0),
        ):
            result = await svc.get_timing_advice(
                delivery_port="INMAA",
                vessel_id=_make_uuid(),
            )

        assert result.vessel_eta == eta
        assert "Vessel ETA" in result.recommendation

    def test_compute_optimal_window_with_response_data(self):
        """Optimal window should be 2x average response time."""
        svc = TimingAdvisor(MagicMock())
        window = svc._compute_optimal_window(avg_response_days=3.0, days_available=30)
        # 2x 3.0 = 6, min 3, max 14
        assert window == 6

    def test_compute_optimal_window_capped(self):
        """Optimal window should not exceed 14 days."""
        svc = TimingAdvisor(MagicMock())
        window = svc._compute_optimal_window(avg_response_days=10.0, days_available=30)
        assert window == 14

    def test_compute_optimal_window_shrinks_for_short_timeline(self):
        """Optimal window should shrink when time is limited."""
        svc = TimingAdvisor(MagicMock())
        window = svc._compute_optimal_window(avg_response_days=5.0, days_available=8)
        # 8 - 3 = 5 max window
        assert window == 5

    def test_assess_timeline_classification(self):
        """Test timeline assessment boundaries."""
        svc = TimingAdvisor(MagicMock())

        assert svc._assess_timeline(30, None, None) == "sufficient"
        assert svc._assess_timeline(14, None, None) == "sufficient"
        assert svc._assess_timeline(10, None, None) == "tight"
        assert svc._assess_timeline(7, None, None) == "tight"
        assert svc._assess_timeline(6, None, None) == "risky"
        assert svc._assess_timeline(3, None, None) == "risky"
        assert svc._assess_timeline(None, None, None) == "sufficient"


# ---------------------------------------------------------------------------
# Schema Tests
# ---------------------------------------------------------------------------


class TestSchemas:
    """Tests for Pydantic schema validation."""

    def test_price_benchmark_defaults(self):
        benchmark = PriceBenchmark(impa_code="123456")
        assert benchmark.has_data is False
        assert benchmark.quote_count == 0
        assert benchmark.currency == "USD"
        assert benchmark.period_days == 90
        assert benchmark.p25 is None
        assert benchmark.p50 is None
        assert benchmark.p75 is None

    def test_budget_estimate_defaults(self):
        estimate = BudgetEstimate()
        assert estimate.low == Decimal("0")
        assert estimate.likely == Decimal("0")
        assert estimate.high == Decimal("0")
        assert estimate.items_with_data == 0

    def test_supplier_match_result_defaults(self):
        result = SupplierMatchResult()
        assert result.total_count == 0
        assert result.recommended == []
        assert result.other == []
        assert result.single_source_risk is False

    def test_intelligence_response_defaults(self):
        response = IntelligenceResponse()
        assert response.suppliers is None
        assert response.price_benchmarks == []
        assert response.budget_estimate is None
        assert response.risk_flags == []
        assert response.timing is None

    def test_risk_flag_with_details(self):
        flag = RiskFlag(
            risk_type="SINGLE_SOURCE",
            severity="HIGH",
            message="Test",
            details={"port": "INMAA"},
        )
        assert flag.details["port"] == "INMAA"

    def test_timing_advice_defaults(self):
        advice = TimingAdvice(recommendation="OK")
        assert advice.optimal_window_days == 0
        assert advice.vessel_eta is None
        assert advice.timeline_assessment == "sufficient"
        assert advice.avg_response_days is None


# ---------------------------------------------------------------------------
# Combined Intelligence Endpoint Integration Test
# ---------------------------------------------------------------------------


class TestCombinedIntelligence:
    """Tests for the combined intelligence endpoint assembly."""

    @pytest.mark.asyncio
    async def test_combined_response_with_all_sections(self, mock_db):
        """When all parameters are provided, all sections should be populated."""
        from src.modules.intelligence.router import get_intelligence

        benchmarks = [
            PriceBenchmark(
                impa_code="123456",
                p25=Decimal("10"),
                p50=Decimal("20"),
                p75=Decimal("30"),
                has_data=True,
                quote_count=5,
            )
        ]
        budget = BudgetEstimate(
            low=Decimal("10"),
            likely=Decimal("20"),
            high=Decimal("30"),
            items_with_data=1,
        )
        suppliers = SupplierMatchResult(
            total_count=3,
            verified_plus_count=2,
            recommended=[],
            other=[],
        )
        flags = [
            RiskFlag(risk_type="TIGHT_TIMELINE", severity="HIGH", message="Tight")
        ]
        timing = TimingAdvice(
            recommendation="OK",
            optimal_window_days=7,
            timeline_assessment="tight",
        )

        with (
            patch(
                "src.modules.intelligence.router.PriceBenchmarkService"
            ) as mock_price_cls,
            patch(
                "src.modules.intelligence.router.SupplierMatchingService"
            ) as mock_supplier_cls,
            patch(
                "src.modules.intelligence.router.RiskAnalyzer"
            ) as mock_risk_cls,
            patch(
                "src.modules.intelligence.router.TimingAdvisor"
            ) as mock_timing_cls,
        ):
            mock_price_svc = AsyncMock()
            mock_price_svc.get_price_benchmarks.return_value = benchmarks
            mock_price_svc.estimate_budget.return_value = budget
            mock_price_cls.return_value = mock_price_svc

            mock_supplier_svc = AsyncMock()
            mock_supplier_svc.match_suppliers.return_value = suppliers
            mock_supplier_cls.return_value = mock_supplier_svc

            mock_risk_svc = AsyncMock()
            mock_risk_svc.analyze_risks.return_value = flags
            mock_risk_cls.return_value = mock_risk_svc

            mock_timing_svc = AsyncMock()
            mock_timing_svc.get_timing_advice.return_value = timing
            mock_timing_cls.return_value = mock_timing_svc

            result = await get_intelligence(
                delivery_port="INMAA",
                impa_codes="123456",
                vessel_id=_make_uuid(),
                delivery_date=datetime.now(tz=UTC) + timedelta(days=10),
                bidding_deadline=datetime.now(tz=UTC) + timedelta(days=5),
                buyer_organization_id=_make_uuid(),
                db=mock_db,
            )

        assert len(result.price_benchmarks) == 1
        assert result.budget_estimate is not None
        assert result.suppliers is not None
        assert len(result.risk_flags) == 1
        assert result.timing is not None
        assert result.timing.timeline_assessment == "tight"

    @pytest.mark.asyncio
    async def test_combined_response_minimal_params(self, mock_db):
        """With no params, response should be mostly empty."""
        from src.modules.intelligence.router import get_intelligence

        result = await get_intelligence(
            delivery_port=None,
            impa_codes=None,
            vessel_id=None,
            delivery_date=None,
            bidding_deadline=None,
            buyer_organization_id=None,
            db=mock_db,
        )

        assert result.price_benchmarks == []
        assert result.budget_estimate is None
        assert result.suppliers is None
        assert result.risk_flags == []
        assert result.timing is None
