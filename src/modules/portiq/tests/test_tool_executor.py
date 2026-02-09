"""Tests for PortiQ ToolExecutor — all 10 tool dispatch handlers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.portiq.tool_executor import ToolExecutor


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def mock_user():
    return MagicMock(
        id=uuid.uuid4(),
        email="buyer@test.com",
        organization_id=uuid.uuid4(),
        organization_type="BUYER",
        role="ADMIN",
        is_platform_admin=False,
    )


class TestToolExecutorDispatch:
    """Test that execute() dispatches to correct handlers."""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self, mock_db, mock_user):
        executor = ToolExecutor(mock_db, mock_user)
        result = await executor.execute("nonexistent_tool", {})
        assert "error" in result
        assert "Unknown tool" in result["error"]

    @pytest.mark.asyncio
    async def test_handler_exception_returns_error(self, mock_db, mock_user):
        executor = ToolExecutor(mock_db, mock_user)
        with patch.object(
            executor, "_handle_search_products", side_effect=Exception("DB down")
        ):
            result = await executor.execute("search_products", {"query": "test"})
            assert "error" in result
            assert "DB down" in result["error"]


class TestSearchProducts:
    @pytest.mark.asyncio
    async def test_search_products(self, mock_db, mock_user):
        executor = ToolExecutor(mock_db, mock_user)

        mock_result = MagicMock()
        mock_result.id = uuid.uuid4()
        mock_result.impa_code = "123456"
        mock_result.name = "Marine Paint Red"
        mock_result.description = "Anti-fouling paint"
        mock_result.category_name = "Paints"
        mock_result.score = 0.85

        with patch(
            "src.modules.search.text_search.TextSearchService"
        ) as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.keyword_search.return_value = ([mock_result], 1)
            mock_svc_cls.return_value = mock_svc

            with patch("src.modules.search.embedding.EmbeddingService"):
                result = await executor.execute(
                    "search_products", {"query": "marine paint", "limit": 5}
                )

            assert "items" in result
            assert result["total"] == 1
            assert result["items"][0]["impa_code"] == "123456"


class TestGetProductDetails:
    @pytest.mark.asyncio
    async def test_get_by_impa(self, mock_db, mock_user):
        executor = ToolExecutor(mock_db, mock_user)

        mock_product = MagicMock()
        mock_product.id = uuid.uuid4()
        mock_product.impa_code = "123456"
        mock_product.name = "Marine Paint"
        mock_product.description = "Paint"
        mock_product.unit_of_measure = "LTR"
        mock_product.category_id = uuid.uuid4()
        mock_product.specifications = {}

        with patch(
            "src.modules.product.service.ProductService"
        ) as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_product_by_impa.return_value = mock_product
            mock_svc_cls.return_value = mock_svc

            result = await executor.execute(
                "get_product_details", {"product_id_or_impa": "123456"}
            )

            assert result["impa_code"] == "123456"
            mock_svc.get_product_by_impa.assert_called_once_with("123456")

    @pytest.mark.asyncio
    async def test_get_by_uuid(self, mock_db, mock_user):
        executor = ToolExecutor(mock_db, mock_user)
        product_id = uuid.uuid4()

        mock_product = MagicMock()
        mock_product.id = product_id
        mock_product.impa_code = "654321"
        mock_product.name = "Bolt"
        mock_product.description = "Steel bolt"
        mock_product.unit_of_measure = "PCS"
        mock_product.category_id = None
        mock_product.specifications = None

        with patch(
            "src.modules.product.service.ProductService"
        ) as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_product_detail.return_value = mock_product
            mock_svc_cls.return_value = mock_svc

            result = await executor.execute(
                "get_product_details", {"product_id_or_impa": str(product_id)}
            )

            assert result["id"] == str(product_id)
            mock_svc.get_product_detail.assert_called_once_with(product_id)


class TestCreateRfq:
    @pytest.mark.asyncio
    async def test_create_rfq_with_line_items(self, mock_db, mock_user):
        executor = ToolExecutor(mock_db, mock_user)

        mock_rfq = MagicMock()
        mock_rfq.id = uuid.uuid4()
        mock_rfq.reference_number = "RFQ-2026-00001"
        mock_rfq.title = "Paint Order"
        mock_rfq.status.value = "DRAFT"
        mock_rfq.delivery_port = "INMAA"

        with patch(
            "src.modules.rfq.rfq_service.RfqService"
        ) as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.create_rfq.return_value = mock_rfq
            mock_svc.add_line_item.return_value = MagicMock()
            mock_svc_cls.return_value = mock_svc

            result = await executor.execute("create_rfq", {
                "title": "Paint Order",
                "delivery_port": "INMAA",
                "line_items": [
                    {"description": "Red paint", "quantity": 10, "unit": "LTR"},
                    {"description": "Blue paint", "quantity": 5, "unit": "LTR"},
                ],
            })

            assert result["reference_number"] == "RFQ-2026-00001"
            assert result["line_item_count"] == 2
            assert mock_svc.add_line_item.call_count == 2


class TestListRfqs:
    @pytest.mark.asyncio
    async def test_list_rfqs_no_filter(self, mock_db, mock_user):
        executor = ToolExecutor(mock_db, mock_user)

        mock_rfq = MagicMock()
        mock_rfq.id = uuid.uuid4()
        mock_rfq.reference_number = "RFQ-2026-00001"
        mock_rfq.title = "Test RFQ"
        mock_rfq.status.value = "DRAFT"
        mock_rfq.delivery_port = "INBOM"
        mock_rfq.created_at = datetime.now(UTC)

        with patch(
            "src.modules.rfq.rfq_service.RfqService"
        ) as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.list_rfqs.return_value = ([mock_rfq], 1)
            mock_svc_cls.return_value = mock_svc

            result = await executor.execute("list_rfqs", {})

            assert result["total"] == 1
            assert len(result["items"]) == 1


class TestGetRfqDetails:
    @pytest.mark.asyncio
    async def test_get_rfq_details(self, mock_db, mock_user):
        executor = ToolExecutor(mock_db, mock_user)
        rfq_id = uuid.uuid4()

        mock_rfq = MagicMock()
        mock_rfq.id = rfq_id
        mock_rfq.reference_number = "RFQ-2026-00001"
        mock_rfq.title = "Test"
        mock_rfq.description = "Desc"
        mock_rfq.status.value = "DRAFT"
        mock_rfq.delivery_port = "INMAA"
        mock_rfq.delivery_date = None
        mock_rfq.bidding_deadline = None
        mock_rfq.currency = "USD"
        mock_rfq.created_at = datetime.now(UTC)

        mock_li = MagicMock()
        mock_li.line_number = 1
        mock_li.description = "Paint"
        mock_li.quantity = Decimal("10")
        mock_li.unit_of_measure = "LTR"
        mock_li.impa_code = "123456"
        mock_rfq.line_items = [mock_li]
        mock_rfq.invitations = []

        with patch(
            "src.modules.rfq.rfq_service.RfqService"
        ) as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_rfq.return_value = mock_rfq
            mock_svc_cls.return_value = mock_svc

            result = await executor.execute(
                "get_rfq_details", {"rfq_id": str(rfq_id)}
            )

            assert result["reference_number"] == "RFQ-2026-00001"
            assert len(result["line_items"]) == 1


class TestListSuppliers:
    @pytest.mark.asyncio
    async def test_list_suppliers(self, mock_db, mock_user):
        executor = ToolExecutor(mock_db, mock_user)

        mock_profile = MagicMock()
        mock_profile.id = uuid.uuid4()
        mock_profile.company_name = "Marine Supplies Co"
        mock_profile.tier.value = "VERIFIED"
        mock_profile.categories = ["paints"]
        mock_profile.port_coverage = ["INMAA"]
        mock_profile.city = "Chennai"
        mock_profile.country = "India"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_profile]
        mock_db.execute.return_value = mock_result

        result = await executor.execute("list_suppliers", {"port": "INMAA"})
        assert result["total"] == 1
        assert result["items"][0]["company_name"] == "Marine Supplies Co"


class TestGetIntelligence:
    @pytest.mark.asyncio
    async def test_get_intelligence_with_port(self, mock_db, mock_user):
        executor = ToolExecutor(mock_db, mock_user)

        with patch(
            "src.modules.intelligence.supplier_matching.SupplierMatchingService"
        ) as mock_matching_cls:
            mock_matching = AsyncMock()
            mock_match_result = MagicMock()
            mock_match_result.ranked_suppliers = []
            mock_match_result.total_candidates = 0
            mock_matching.match_suppliers.return_value = mock_match_result
            mock_matching_cls.return_value = mock_matching

            with patch(
                "src.modules.intelligence.risk_analyzer.RiskAnalyzer"
            ) as mock_risk_cls:
                mock_risk = AsyncMock()
                mock_risk.analyze_risks.return_value = []
                mock_risk_cls.return_value = mock_risk

                with patch(
                    "src.modules.intelligence.timing_advisor.TimingAdvisor"
                ) as mock_timing_cls:
                    mock_timing = AsyncMock()
                    mock_timing_result = MagicMock()
                    mock_timing_result.assessment = "SUFFICIENT"
                    mock_timing_result.recommended_bidding_window_days = 7
                    mock_timing_result.vessel_eta = None
                    mock_timing_result.avg_response_days = 3.5
                    mock_timing.get_timing_advice.return_value = mock_timing_result
                    mock_timing_cls.return_value = mock_timing

                    result = await executor.execute(
                        "get_intelligence", {"delivery_port": "INMAA"}
                    )

                    assert "suppliers" in result
                    assert "timing" in result


class TestPredictConsumption:
    @pytest.mark.asyncio
    async def test_predict_consumption(self, mock_db, mock_user):
        executor = ToolExecutor(mock_db, mock_user)
        vessel_id = uuid.uuid4()

        mock_prediction = MagicMock()
        mock_prediction.category = "Provisions"
        mock_prediction.product_name = "Rice"
        mock_prediction.impa_code = "390001"
        mock_prediction.predicted_quantity = Decimal("500")
        mock_prediction.unit = "KG"
        mock_prediction.confidence = 0.85

        with patch(
            "src.modules.prediction.consumption_engine.ConsumptionEngine"
        ) as mock_engine_cls:
            mock_engine = AsyncMock()
            mock_engine.predict_quantities.return_value = [mock_prediction]
            mock_engine_cls.return_value = mock_engine

            result = await executor.execute("predict_consumption", {
                "vessel_id": str(vessel_id),
                "crew_size": 25,
                "voyage_days": 14,
            })

            assert len(result["items"]) == 1
            assert result["items"][0]["category"] == "Provisions"


class TestGetVesselInfo:
    @pytest.mark.asyncio
    async def test_get_vessel_by_imo(self, mock_db, mock_user):
        executor = ToolExecutor(mock_db, mock_user)

        mock_vessel = MagicMock()
        mock_vessel.id = uuid.uuid4()
        mock_vessel.name = "MV Test Ship"
        mock_vessel.imo_number = "1234567"
        mock_vessel.mmsi = "123456789"
        mock_vessel.vessel_type.value = "BULK_CARRIER"
        mock_vessel.status.value = "ACTIVE"
        mock_vessel.flag_state = "India"
        mock_vessel.gross_tonnage = Decimal("50000")
        mock_vessel.deadweight_tonnage = Decimal("80000")
        mock_vessel.year_built = 2015

        with patch(
            "src.modules.vessel.vessel_service.VesselService"
        ) as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_vessel_by_imo.return_value = mock_vessel
            mock_svc_cls.return_value = mock_svc

            # Mock position query (returns None)
            mock_pos_result = MagicMock()
            mock_pos_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_pos_result

            result = await executor.execute(
                "get_vessel_info", {"vessel_id_or_imo": "1234567"}
            )

            assert result["name"] == "MV Test Ship"
            assert result["imo_number"] == "1234567"
            mock_svc.get_vessel_by_imo.assert_called_once_with("1234567")


class TestMatchSuppliersForPort:
    @pytest.mark.asyncio
    async def test_match_suppliers_for_port(self, mock_db, mock_user):
        executor = ToolExecutor(mock_db, mock_user)

        mock_supplier = MagicMock()
        mock_supplier.supplier_id = uuid.uuid4()
        mock_supplier.company_name = "Best Supplier"
        mock_supplier.tier = "PREFERRED"
        mock_supplier.score = 0.92
        mock_supplier.port_coverage = ["INMAA"]
        mock_supplier.category_match_ratio = 0.8

        mock_match_result = MagicMock()
        mock_match_result.ranked_suppliers = [mock_supplier]
        mock_match_result.total_candidates = 5

        with patch(
            "src.modules.intelligence.supplier_matching.SupplierMatchingService"
        ) as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.match_suppliers.return_value = mock_match_result
            mock_svc_cls.return_value = mock_svc

            result = await executor.execute(
                "match_suppliers_for_port",
                {"port": "INMAA", "impa_codes": ["123456"]},
            )

            assert result["port"] == "INMAA"
            assert len(result["ranked_suppliers"]) == 1
            assert result["total_candidates"] == 5
