"""Tests for the Prediction Service — consumption engine, templates, reorder, co-occurrence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.exceptions import NotFoundException
from src.models.enums import RfqStatus, VesselStatus, VesselType
from src.models.product import Product
from src.models.rfq import Rfq
from src.models.rfq_line_item import RfqLineItem
from src.models.vessel import Vessel
from src.modules.prediction.co_occurrence import CoOccurrenceService
from src.modules.prediction.constants import CONSUMPTION_RATES
from src.modules.prediction.consumption_engine import ConsumptionEngine
from src.modules.prediction.reorder_service import ReorderService
from src.modules.prediction.schemas import PredictedItem
from src.modules.prediction.template_service import TemplateService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def sample_vessel():
    vessel = Vessel(
        id=uuid.uuid4(),
        imo_number="9876543",
        name="MV Maritime Star",
        vessel_type=VesselType.TANKER,
        status=VesselStatus.ACTIVE,
        crew_size=25,
        metadata_extra={},
    )
    return vessel


@pytest.fixture
def sample_vessel_container():
    vessel = Vessel(
        id=uuid.uuid4(),
        imo_number="1234567",
        name="MV Container King",
        vessel_type=VesselType.CONTAINER,
        status=VesselStatus.ACTIVE,
        crew_size=20,
        metadata_extra={},
    )
    return vessel


@pytest.fixture
def sample_product():
    product = Product(
        id=uuid.uuid4(),
        impa_code="310001",
        name="Fire Extinguisher ABC 6KG",
        unit_of_measure="PIECE",
        category_id=uuid.uuid4(),
        specifications={},
    )
    return product


@pytest.fixture
def sample_rfq(sample_vessel):
    rfq = Rfq(
        id=uuid.uuid4(),
        reference_number="RFQ-2026-00001",
        buyer_organization_id=uuid.uuid4(),
        title="Monthly Supply Order",
        status=RfqStatus.COMPLETED,
        vessel_id=sample_vessel.id,
        delivery_port="INMAA",
        created_by=uuid.uuid4(),
        created_at=datetime(2026, 1, 15, tzinfo=UTC),
        updated_at=datetime(2026, 1, 15, tzinfo=UTC),
        metadata_extra={},
    )
    return rfq


@pytest.fixture
def sample_line_items(sample_rfq):
    items = [
        RfqLineItem(
            id=uuid.uuid4(),
            rfq_id=sample_rfq.id,
            line_number=1,
            impa_code="310001",
            description="Fire Extinguisher ABC 6KG",
            quantity=Decimal("10.000"),
            unit_of_measure="PIECE",
            created_at=datetime(2026, 1, 15, tzinfo=UTC),
            updated_at=datetime(2026, 1, 15, tzinfo=UTC),
        ),
        RfqLineItem(
            id=uuid.uuid4(),
            rfq_id=sample_rfq.id,
            line_number=2,
            impa_code="000100",
            description="Rice, Long Grain 25KG",
            quantity=Decimal("50.000"),
            unit_of_measure="KG",
            created_at=datetime(2026, 1, 15, tzinfo=UTC),
            updated_at=datetime(2026, 1, 15, tzinfo=UTC),
        ),
    ]
    return items


# ---------------------------------------------------------------------------
# Helper to build mock DB result objects (sync methods on result)
# ---------------------------------------------------------------------------


def _make_scalar_result(value):
    """Build a MagicMock that mimics a SQLAlchemy Result with .scalar() returning ``value``."""
    result = MagicMock()
    result.scalar.return_value = value
    return result


def _make_scalar_one_or_none_result(value):
    """Build a MagicMock with .scalar_one_or_none() returning ``value``."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_scalars_all_result(values):
    """Build a MagicMock with .scalars().all() returning ``values``."""
    result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = values
    result.scalars.return_value = mock_scalars
    return result


def _make_unique_scalar_result(value):
    """Build a MagicMock with .unique().scalar_one_or_none() returning ``value``."""
    result = MagicMock()
    mock_unique = MagicMock()
    mock_unique.scalar_one_or_none.return_value = value
    result.unique.return_value = mock_unique
    return result


def _make_all_result(rows):
    """Build a MagicMock with .all() returning ``rows``."""
    result = MagicMock()
    result.all.return_value = rows
    return result


# ---------------------------------------------------------------------------
# ConsumptionEngine tests
# ---------------------------------------------------------------------------


class TestConsumptionEngineRuleComputation:
    """Test the static rule-based quantity computation."""

    def test_person_per_day_category(self):
        """Category 00 (provisions) should factor in crew_size."""
        rate_config = CONSUMPTION_RATES["00"]
        quantity = ConsumptionEngine._compute_rule_quantity(
            rate_config=rate_config,
            vessel_type="GENERAL_CARGO",
            category_prefix="00",
            voyage_days=14,
            crew_size=20,
        )
        # Expected: 3.5 * 20 * 14 * 1.0 * 1.2 = 1176.0
        assert quantity == Decimal("1176.0")

    def test_vessel_per_day_category(self):
        """Category 21 (deck) should NOT factor in crew_size."""
        rate_config = CONSUMPTION_RATES["21"]
        quantity = ConsumptionEngine._compute_rule_quantity(
            rate_config=rate_config,
            vessel_type="GENERAL_CARGO",
            category_prefix="21",
            voyage_days=30,
            crew_size=25,
        )
        # Expected: 0.5 * 30 * 1.0 * 1.3 = 19.5
        assert quantity == Decimal("19.5")

    def test_vessel_type_multiplier_tanker_safety(self):
        """Tanker vessels have 1.5x multiplier for category 31 (safety)."""
        rate_config = CONSUMPTION_RATES["31"]
        quantity = ConsumptionEngine._compute_rule_quantity(
            rate_config=rate_config,
            vessel_type="TANKER",
            category_prefix="31",
            voyage_days=30,
            crew_size=20,
        )
        # Expected: 0.02 * 20 * 30 * 1.5 * 1.3 = 23.4
        assert quantity == Decimal("23.4")

    def test_vessel_type_multiplier_passenger_provisions(self):
        """Passenger vessels have 2.5x multiplier for provisions (cat 00)."""
        rate_config = CONSUMPTION_RATES["00"]
        quantity = ConsumptionEngine._compute_rule_quantity(
            rate_config=rate_config,
            vessel_type="PASSENGER",
            category_prefix="00",
            voyage_days=7,
            crew_size=50,
        )
        # Expected: 3.5 * 50 * 7 * 2.5 * 1.2 = 3675.0
        assert quantity == Decimal("3675.0")

    def test_default_multiplier_for_unknown_category(self):
        """When a category has no specific multiplier, DEFAULT is used."""
        rate_config = CONSUMPTION_RATES["85"]
        quantity = ConsumptionEngine._compute_rule_quantity(
            rate_config=rate_config,
            vessel_type="GENERAL_CARGO",
            category_prefix="85",
            voyage_days=90,
            crew_size=20,
        )
        # Expected: 0.02 * 90 * 1.0 * 1.2 = 2.16
        assert quantity == Decimal("2.16")

    def test_offshore_default_multiplier(self):
        """Offshore vessels have DEFAULT=1.1, so even non-listed categories get a boost."""
        rate_config = CONSUMPTION_RATES["00"]
        quantity = ConsumptionEngine._compute_rule_quantity(
            rate_config=rate_config,
            vessel_type="OFFSHORE",
            category_prefix="00",
            voyage_days=14,
            crew_size=30,
        )
        # Expected: 3.5 * 30 * 14 * 1.1 * 1.2 = 1940.4
        assert quantity == Decimal("1940.4")


class TestConsumptionEnginePrediction:
    """Test the full predict_quantities method with mocked DB."""

    @pytest.mark.asyncio
    async def test_cold_start_rules_only(self, mock_session, sample_vessel):
        """When vessel has < 5 completed RFQs, predictions are rules-only."""
        engine = ConsumptionEngine(mock_session)

        mock_session.execute.side_effect = [
            _make_scalar_one_or_none_result(sample_vessel),  # _load_vessel
            _make_scalar_result(0),                           # _count_completed_rfqs
            _make_scalars_all_result([]),                      # _find_products_for_category
        ]

        results = await engine.predict_quantities(
            vessel_id=sample_vessel.id,
            voyage_days=14,
            crew_size=20,
            categories=["31"],
        )

        assert len(results) == 1
        item = results[0]
        assert item.category_prefix == "31"
        # Cold start confidence should be 0.55 * 0.8 = 0.44 (no catalog match)
        assert item.confidence == pytest.approx(0.55 * 0.8, rel=0.01)
        assert item.impa_code == "310000"  # generic code when no products found

    @pytest.mark.asyncio
    async def test_with_catalog_products(self, mock_session, sample_vessel, sample_product):
        """When catalog products exist, they appear in results."""
        engine = ConsumptionEngine(mock_session)

        mock_session.execute.side_effect = [
            _make_scalar_one_or_none_result(sample_vessel),  # _load_vessel
            _make_scalar_result(0),                           # _count_completed_rfqs
            _make_scalars_all_result([sample_product]),        # _find_products_for_category
        ]

        results = await engine.predict_quantities(
            vessel_id=sample_vessel.id,
            voyage_days=14,
            crew_size=20,
            categories=["31"],
        )

        assert len(results) == 1
        assert results[0].impa_code == "310001"
        assert results[0].product_id == sample_product.id
        assert results[0].confidence == pytest.approx(0.55, rel=0.01)

    @pytest.mark.asyncio
    async def test_vessel_not_found(self, mock_session):
        """Should raise NotFoundException when vessel does not exist."""
        engine = ConsumptionEngine(mock_session)

        mock_session.execute.return_value = _make_scalar_one_or_none_result(None)

        with pytest.raises(NotFoundException, match="not found"):
            await engine.predict_quantities(
                vessel_id=uuid.uuid4(),
                voyage_days=14,
                crew_size=20,
            )


# ---------------------------------------------------------------------------
# TemplateService tests
# ---------------------------------------------------------------------------


class TestTemplateService:
    @pytest.mark.asyncio
    async def test_list_all_templates(self, mock_session):
        """Should return vessel-type, voyage-type, and event templates."""
        svc = TemplateService(mock_session)
        templates = await svc.get_templates()

        template_ids = [t.id for t in templates]
        assert "VESSEL_TANKER" in template_ids
        assert "VESSEL_OFFSHORE" in template_ids
        assert "VOYAGE_COASTAL" in template_ids
        assert "VOYAGE_DEEP_SEA" in template_ids
        assert "EVENT_DRYDOCK" in template_ids
        assert "EVENT_CREW_CHANGE" in template_ids

    @pytest.mark.asyncio
    async def test_filter_by_vessel_type(self, mock_session):
        """Filtering by vessel_type should return only matching vessel templates + all voyage/event."""
        svc = TemplateService(mock_session)
        templates = await svc.get_templates(vessel_type="TANKER")

        vessel_templates = [t for t in templates if t.id.startswith("VESSEL_")]
        assert len(vessel_templates) == 1
        assert vessel_templates[0].id == "VESSEL_TANKER"

    @pytest.mark.asyncio
    async def test_filter_by_voyage_days(self, mock_session):
        """Filtering by voyage_days should exclude voyage templates with max_days < voyage_days."""
        svc = TemplateService(mock_session)
        templates = await svc.get_templates(voyage_days=5)

        voyage_templates = [t for t in templates if t.id.startswith("VOYAGE_")]
        voyage_ids = [t.id for t in voyage_templates]
        assert "VOYAGE_COASTAL" in voyage_ids
        assert "VOYAGE_SHORT_SEA" in voyage_ids
        assert "VOYAGE_DEEP_SEA" in voyage_ids

    @pytest.mark.asyncio
    async def test_filter_excludes_short_voyage(self, mock_session):
        """A 30-day voyage should exclude COASTAL (max_days=7) and SHORT_SEA (max_days=21)."""
        svc = TemplateService(mock_session)
        templates = await svc.get_templates(voyage_days=30)

        voyage_templates = [t for t in templates if t.id.startswith("VOYAGE_")]
        voyage_ids = [t.id for t in voyage_templates]
        assert "VOYAGE_COASTAL" not in voyage_ids
        assert "VOYAGE_SHORT_SEA" not in voyage_ids
        assert "VOYAGE_DEEP_SEA" in voyage_ids

    def test_resolve_vessel_template(self):
        """Resolving a VESSEL_ template should return its categories."""
        categories = TemplateService._resolve_template_categories("VESSEL_TANKER")
        assert categories == ["31", "33", "45"]

    def test_resolve_event_template(self):
        """Resolving an EVENT_ template should return its categories."""
        categories = TemplateService._resolve_template_categories("EVENT_DRYDOCK")
        assert categories == ["71", "25", "45"]

    def test_resolve_voyage_template_returns_empty(self):
        """Voyage templates use all categories, so the resolved list is empty."""
        categories = TemplateService._resolve_template_categories("VOYAGE_COASTAL")
        assert categories == []

    def test_resolve_unknown_template_raises(self):
        """Unknown template ID should raise NotFoundException."""
        with pytest.raises(NotFoundException):
            TemplateService._resolve_template_categories("VESSEL_SUBMARINE")

    def test_resolve_invalid_format_raises(self):
        """Template ID without underscore separator should raise NotFoundException."""
        with pytest.raises(NotFoundException):
            TemplateService._resolve_template_categories("INVALID")


# ---------------------------------------------------------------------------
# ReorderService tests
# ---------------------------------------------------------------------------


class TestReorderService:
    @pytest.mark.asyncio
    async def test_get_last_order_found(
        self, mock_session, sample_rfq, sample_line_items
    ):
        """Should return the most recent completed RFQ as a ReorderSuggestion."""
        svc = ReorderService(mock_session)
        sample_rfq.line_items = sample_line_items

        mock_session.execute.return_value = _make_unique_scalar_result(sample_rfq)

        suggestion = await svc.get_last_order(
            vessel_id=sample_rfq.vessel_id, port="INMAA"
        )

        assert suggestion is not None
        assert suggestion.source_rfq_id == sample_rfq.id
        assert suggestion.source_rfq_reference == "RFQ-2026-00001"
        assert suggestion.delivery_port == "INMAA"
        assert len(suggestion.line_items) == 2
        assert suggestion.line_items[0].impa_code == "310001"
        assert suggestion.line_items[1].impa_code == "000100"

    @pytest.mark.asyncio
    async def test_get_last_order_not_found(self, mock_session):
        """Should return None when no completed RFQ exists for the vessel."""
        svc = ReorderService(mock_session)

        mock_session.execute.return_value = _make_unique_scalar_result(None)

        suggestion = await svc.get_last_order(vessel_id=uuid.uuid4())
        assert suggestion is None

    @pytest.mark.asyncio
    async def test_copy_from_rfq_no_adjustments(
        self, mock_session, sample_rfq, sample_line_items
    ):
        """copy_from_rfq without adjustments should copy quantities as-is."""
        svc = ReorderService(mock_session)
        sample_rfq.line_items = sample_line_items

        mock_session.execute.return_value = _make_unique_scalar_result(sample_rfq)

        items = await svc.copy_from_rfq(source_rfq_id=sample_rfq.id)

        assert len(items) == 2
        assert items[0].quantity == Decimal("10.000")
        assert items[1].quantity == Decimal("50.000")
        assert items[0].confidence == 0.9

    @pytest.mark.asyncio
    async def test_copy_from_rfq_with_voyage_adjustment(
        self, mock_session, sample_rfq, sample_line_items
    ):
        """copy_from_rfq with voyage_days=28 should scale quantities ~2x (vs 14-day ref)."""
        svc = ReorderService(mock_session)
        sample_rfq.line_items = sample_line_items

        mock_session.execute.return_value = _make_unique_scalar_result(sample_rfq)

        items = await svc.copy_from_rfq(
            source_rfq_id=sample_rfq.id, voyage_days=28
        )

        # 28/14 = 2.0x factor
        assert items[0].quantity == Decimal("20.00")
        assert items[1].quantity == Decimal("100.00")
        assert items[0].confidence == 0.75  # adjusted confidence

    @pytest.mark.asyncio
    async def test_copy_from_rfq_not_found(self, mock_session):
        """Should raise NotFoundException when source RFQ does not exist."""
        svc = ReorderService(mock_session)

        mock_session.execute.return_value = _make_unique_scalar_result(None)

        with pytest.raises(NotFoundException, match="not found"):
            await svc.copy_from_rfq(source_rfq_id=uuid.uuid4())


# ---------------------------------------------------------------------------
# CoOccurrenceService tests
# ---------------------------------------------------------------------------


class TestCoOccurrenceService:
    @pytest.mark.asyncio
    async def test_empty_input_returns_empty(self, mock_session):
        """Empty input list should return empty suggestions."""
        svc = CoOccurrenceService(mock_session)
        suggestions = await svc.get_suggestions(current_impa_codes=[])
        assert suggestions == []

    @pytest.mark.asyncio
    async def test_no_rfqs_returns_empty(self, mock_session):
        """When there are no RFQs at all, should return empty suggestions."""
        svc = CoOccurrenceService(mock_session)

        mock_session.execute.return_value = _make_scalar_result(0)

        suggestions = await svc.get_suggestions(current_impa_codes=["310001"])
        assert suggestions == []

    @pytest.mark.asyncio
    async def test_co_occurrence_with_sufficient_lift(self, mock_session):
        """Should return suggestions with lift > min_lift and support >= min_support."""
        svc = CoOccurrenceService(mock_session)

        product_for_candidate = Product(
            id=uuid.uuid4(),
            impa_code="450001",
            name="Lubricating Oil 20L",
            unit_of_measure="L",
            category_id=uuid.uuid4(),
            specifications={},
        )

        mock_session.execute.side_effect = [
            _make_scalar_result(100),                         # _count_total_rfqs
            _make_all_result([("450001", 10)]),               # _find_co_occurring_items: candidates
            _make_all_result([("310001",)]),                   # _find_co_occurring_input_codes
            _make_scalar_result(15),                           # _count_rfqs_with_item("450001")
            _make_scalar_result(20),                           # _count_rfqs_with_item("310001")
            _make_scalar_one_or_none_result(product_for_candidate),  # _find_product("450001")
        ]

        suggestions = await svc.get_suggestions(
            current_impa_codes=["310001"],
            min_lift=2.0,
            min_support=5,
        )

        # P(A) = 20/100 = 0.2
        # P(B) = 15/100 = 0.15
        # P(A and B) = 10/100 = 0.1
        # lift = 0.1 / (0.2 * 0.15) = 0.1 / 0.03 = 3.33
        assert len(suggestions) == 1
        assert suggestions[0].impa_code == "450001"
        assert suggestions[0].lift_score == pytest.approx(3.33, abs=0.01)
        assert suggestions[0].support_count == 10
        assert suggestions[0].co_occurs_with == ["310001"]

    @pytest.mark.asyncio
    async def test_co_occurrence_below_lift_threshold(self, mock_session):
        """Candidates with lift below min_lift should be filtered out."""
        svc = CoOccurrenceService(mock_session)

        mock_session.execute.side_effect = [
            _make_scalar_result(100),                         # _count_total_rfqs
            _make_all_result([("990001", 5)]),                # candidates
            _make_all_result([("310001",)]),                   # co_occurring_input_codes
            _make_scalar_result(80),                           # _count_rfqs_with_item("990001")
            _make_scalar_result(20),                           # _count_rfqs_with_item("310001")
        ]

        # lift = (5/100) / (0.2 * 0.8) = 0.05 / 0.16 = 0.3125 < 2.0
        suggestions = await svc.get_suggestions(
            current_impa_codes=["310001"],
            min_lift=2.0,
        )

        assert len(suggestions) == 0


# ---------------------------------------------------------------------------
# Schemas validation tests
# ---------------------------------------------------------------------------


class TestPredictedItemSchema:
    def test_valid_predicted_item(self):
        item = PredictedItem(
            impa_code="310001",
            product_id=uuid.uuid4(),
            description="Fire Extinguisher",
            quantity=Decimal("10.00"),
            unit="PIECE",
            confidence=0.55,
            category_prefix="31",
        )
        assert item.confidence == 0.55
        assert item.quantity == Decimal("10.00")

    def test_confidence_bounds(self):
        """Confidence must be between 0 and 1."""
        with pytest.raises(Exception):
            PredictedItem(
                impa_code="310001",
                description="Test",
                quantity=Decimal("1"),
                unit="PIECE",
                confidence=1.5,  # out of bounds
                category_prefix="31",
            )


class TestReorderServiceAdjustments:
    def test_quantity_adjustment_double_voyage(self):
        """Doubling voyage days should double quantities."""
        items = [
            PredictedItem(
                impa_code="310001",
                description="Test Item",
                quantity=Decimal("100.00"),
                unit="PIECE",
                confidence=0.9,
                category_prefix="31",
            )
        ]
        adjusted = ReorderService._adjust_quantities(items, voyage_days=28)
        # 28/14 = 2x
        assert adjusted[0].quantity == Decimal("200.00")

    def test_quantity_adjustment_with_crew(self):
        """Adjusting crew size should scale quantities proportionally."""
        items = [
            PredictedItem(
                impa_code="000100",
                description="Rice",
                quantity=Decimal("100.00"),
                unit="KG",
                confidence=0.9,
                category_prefix="00",
            )
        ]
        adjusted = ReorderService._adjust_quantities(items, crew_size=40)
        # 40/20 = 2x
        assert adjusted[0].quantity == Decimal("200.00")

    def test_quantity_adjustment_both_factors(self):
        """Both voyage and crew adjustments should multiply."""
        items = [
            PredictedItem(
                impa_code="000100",
                description="Rice",
                quantity=Decimal("100.00"),
                unit="KG",
                confidence=0.9,
                category_prefix="00",
            )
        ]
        adjusted = ReorderService._adjust_quantities(items, voyage_days=28, crew_size=40)
        # (28/14) * (40/20) = 2 * 2 = 4x
        assert adjusted[0].quantity == Decimal("400.00")
        assert adjusted[0].confidence == 0.75
