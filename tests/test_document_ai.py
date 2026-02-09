"""Tests for Document AI module — normalizer, matcher, extraction service, dedup, routing."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.document_extraction import DocumentExtraction, ExtractedLineItem
from src.models.enums import (
    DocumentType,
    ExtractionConfidenceTier,
    ExtractionStatus,
)

# ═══════════════════════════════════════════════════════════════════════════
# Normalizer tests
# ═══════════════════════════════════════════════════════════════════════════


class TestNormalizer:
    """Tests for the Normalizer utility class."""

    def setup_method(self) -> None:
        from src.modules.document_ai.normalizer import Normalizer

        self.normalizer = Normalizer()

    # ── Unit normalization ────────────────────────────────────────────────

    def test_normalize_unit_pcs_variants(self) -> None:
        assert self.normalizer.normalize_unit("pcs") == "pcs"
        assert self.normalizer.normalize_unit("pce") == "pcs"
        assert self.normalizer.normalize_unit("pieces") == "pcs"
        assert self.normalizer.normalize_unit("ea") == "pcs"
        assert self.normalizer.normalize_unit("each") == "pcs"
        assert self.normalizer.normalize_unit("nos") == "pcs"

    def test_normalize_unit_kg_variants(self) -> None:
        assert self.normalizer.normalize_unit("kg") == "kg"
        assert self.normalizer.normalize_unit("kgs") == "kg"
        assert self.normalizer.normalize_unit("kilos") == "kg"
        assert self.normalizer.normalize_unit("kilogram") == "kg"

    def test_normalize_unit_meters_variants(self) -> None:
        assert self.normalizer.normalize_unit("m") == "m"
        assert self.normalizer.normalize_unit("mtr") == "m"
        assert self.normalizer.normalize_unit("meters") == "m"
        assert self.normalizer.normalize_unit("metres") == "m"

    def test_normalize_unit_liters_variants(self) -> None:
        assert self.normalizer.normalize_unit("l") == "L"
        assert self.normalizer.normalize_unit("ltr") == "L"
        assert self.normalizer.normalize_unit("liters") == "L"
        assert self.normalizer.normalize_unit("litres") == "L"

    def test_normalize_unit_container_variants(self) -> None:
        assert self.normalizer.normalize_unit("rolls") == "roll"
        assert self.normalizer.normalize_unit("rls") == "roll"
        assert self.normalizer.normalize_unit("drums") == "drum"
        assert self.normalizer.normalize_unit("drm") == "drum"
        assert self.normalizer.normalize_unit("boxes") == "box"
        assert self.normalizer.normalize_unit("bx") == "box"
        assert self.normalizer.normalize_unit("tins") == "tin"
        assert self.normalizer.normalize_unit("cans") == "tin"
        assert self.normalizer.normalize_unit("bottles") == "bottle"
        assert self.normalizer.normalize_unit("btl") == "bottle"

    def test_normalize_unit_unknown_returns_lowercase(self) -> None:
        assert self.normalizer.normalize_unit("gallons") == "gallons"
        assert self.normalizer.normalize_unit("BAGS") == "bags"

    def test_normalize_unit_with_whitespace(self) -> None:
        assert self.normalizer.normalize_unit("  pcs  ") == "pcs"

    # ── Quantity parsing ─────────────────────────────────────────────────

    def test_parse_quantity_with_unit(self) -> None:
        qty, unit = self.normalizer.parse_quantity("50kg")
        assert qty == 50.0
        assert unit == "kg"

    def test_parse_quantity_with_space(self) -> None:
        qty, unit = self.normalizer.parse_quantity("200 meters")
        assert qty == 200.0
        assert unit == "m"

    def test_parse_quantity_decimal(self) -> None:
        qty, unit = self.normalizer.parse_quantity("3.5 L")
        assert qty == 3.5
        assert unit == "L"

    def test_parse_quantity_bare_number(self) -> None:
        qty, unit = self.normalizer.parse_quantity("12")
        assert qty == 12.0
        assert unit is None

    def test_parse_quantity_ambiguous_returns_none(self) -> None:
        qty, unit = self.normalizer.parse_quantity("as required")
        assert qty is None
        assert unit is None

    def test_parse_quantity_tbd_returns_none(self) -> None:
        qty, unit = self.normalizer.parse_quantity("TBD")
        assert qty is None
        assert unit is None

    # ── Description normalization ────────────────────────────────────────

    def test_normalize_description_strips_line_number(self) -> None:
        result = self.normalizer.normalize_description("1. Marine paint red oxide")
        assert result == "Marine paint red oxide"

    def test_normalize_description_strips_line_number_with_paren(self) -> None:
        result = self.normalizer.normalize_description("01) Anchor chain 22mm")
        assert result == "Anchor chain 22mm"

    def test_normalize_description_collapses_whitespace(self) -> None:
        result = self.normalizer.normalize_description("  Rope   manila   50mm  ")
        assert result == "Rope manila 50mm"

    def test_normalize_description_truncates_at_500(self) -> None:
        long_text = "A" * 600
        result = self.normalizer.normalize_description(long_text)
        assert len(result) == 500
        assert result.endswith("...")

    def test_normalize_description_preserves_short_text(self) -> None:
        result = self.normalizer.normalize_description("Short text")
        assert result == "Short text"

    # ── IMPA detection ───────────────────────────────────────────────────

    def test_detect_impa_in_text_valid(self) -> None:
        result = self.normalizer.detect_impa_in_text("Item 390145 - Safety helmet")
        assert result == "390145"

    def test_detect_impa_in_text_multiple_returns_first(self) -> None:
        result = self.normalizer.detect_impa_in_text("390145 or 390146 safety items")
        assert result == "390145"

    def test_detect_impa_in_text_no_match(self) -> None:
        result = self.normalizer.detect_impa_in_text("Safety helmet red color")
        assert result is None

    def test_detect_impa_in_text_ignores_too_small(self) -> None:
        # 5-digit number should be ignored
        result = self.normalizer.detect_impa_in_text("Item 12345 - test")
        assert result is None

    def test_detect_impa_in_text_ignores_below_range(self) -> None:
        # 099999 is below IMPA range
        result = self.normalizer.detect_impa_in_text("Code 099999 item")
        assert result is None

    def test_detect_impa_in_text_boundary(self) -> None:
        result = self.normalizer.detect_impa_in_text("IMPA 100000 item")
        assert result == "100000"


# ═══════════════════════════════════════════════════════════════════════════
# IMPA Matcher tests (Stage 1 — regex detection)
# ═══════════════════════════════════════════════════════════════════════════


class TestImpaMatcherRegex:
    """Test IMPA matcher stage 1 (regex-based detection)."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def matcher(self, mock_db: AsyncMock):
        from src.modules.document_ai.impa_matcher import ImpaMatcher

        return ImpaMatcher(mock_db)

    @pytest.mark.asyncio
    async def test_regex_match_with_detected_code(
        self, matcher, mock_db: AsyncMock
    ) -> None:
        """When a detected IMPA code matches a product, return high confidence."""
        mock_product = MagicMock()
        mock_product.impa_code = "390145"
        mock_product.id = uuid.uuid4()
        mock_product.name = "Safety Helmet White"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_product
        mock_db.execute.return_value = mock_result

        result = await matcher._match_by_regex(
            raw_text="Safety helmet",
            detected_impa_code="390145",
        )

        assert result is not None
        assert result.impa_code == "390145"
        assert result.confidence == 0.98
        assert result.method == "regex"

    @pytest.mark.asyncio
    async def test_regex_match_from_text_scan(
        self, matcher, mock_db: AsyncMock
    ) -> None:
        """When IMPA code found in text matches a product, return 0.95 confidence."""
        mock_product = MagicMock()
        mock_product.impa_code = "390145"
        mock_product.id = uuid.uuid4()
        mock_product.name = "Safety Helmet White"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_product
        mock_db.execute.return_value = mock_result

        result = await matcher._match_by_regex(
            raw_text="Item 390145 - Safety helmet white",
            detected_impa_code=None,
        )

        assert result is not None
        assert result.impa_code == "390145"
        assert result.confidence == 0.95
        assert result.method == "regex"

    @pytest.mark.asyncio
    async def test_regex_no_impa_code_in_text(
        self, matcher, mock_db: AsyncMock
    ) -> None:
        """When no IMPA code is found in text, return None."""
        result = await matcher._match_by_regex(
            raw_text="Marine paint red oxide primer",
            detected_impa_code=None,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_regex_code_not_in_catalog(
        self, matcher, mock_db: AsyncMock
    ) -> None:
        """When IMPA code is found but not in product catalog, return low confidence."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await matcher._match_by_regex(
            raw_text="Item 999999 - Unknown product",
            detected_impa_code=None,
        )

        assert result is not None
        assert result.impa_code == "999999"
        assert result.product_id is None
        assert result.confidence == 0.5

    @pytest.mark.asyncio
    @patch("src.modules.document_ai.impa_matcher.settings")
    async def test_match_item_regex_only_without_openai(
        self, mock_settings, matcher, mock_db: AsyncMock
    ) -> None:
        """Without OpenAI key, only regex matching is used."""
        mock_settings.openai_api_key = ""

        mock_product = MagicMock()
        mock_product.impa_code = "390145"
        mock_product.id = uuid.uuid4()
        mock_product.name = "Safety Helmet"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_product
        mock_db.execute.return_value = mock_result

        result = await matcher.match_item(
            raw_text="IMPA 390145 Safety helmet white",
            detected_impa_code="390145",
        )

        assert result.impa_code == "390145"
        assert result.method == "regex"
        assert result.confidence >= 0.95


# ═══════════════════════════════════════════════════════════════════════════
# Extraction Service tests
# ═══════════════════════════════════════════════════════════════════════════


class TestExtractionService:
    """Tests for ExtractionService CRUD operations."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db: AsyncMock):
        from src.modules.document_ai.extraction_service import ExtractionService

        return ExtractionService(mock_db)

    @pytest.mark.asyncio
    async def test_create_extraction(self, service, mock_db: AsyncMock) -> None:
        """Creating an extraction should set PENDING status and call db.add."""
        user_id = uuid.uuid4()
        rfq_id = uuid.uuid4()

        extraction = await service.create_extraction(
            filename="test.pdf",
            file_type="application/pdf",
            file_size_bytes=1024,
            uploaded_by=user_id,
            rfq_id=rfq_id,
            document_type=DocumentType.PURCHASE_ORDER,
        )

        assert extraction.filename == "test.pdf"
        assert extraction.file_type == "application/pdf"
        assert extraction.file_size_bytes == 1024
        assert extraction.uploaded_by == user_id
        assert extraction.rfq_id == rfq_id
        assert extraction.document_type == DocumentType.PURCHASE_ORDER
        assert extraction.status == ExtractionStatus.PENDING
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_status_to_parsing_sets_started_at(
        self, service, mock_db: AsyncMock
    ) -> None:
        """Updating status to PARSING should set processing_started_at."""
        extraction_id = uuid.uuid4()
        mock_extraction = DocumentExtraction(
            id=extraction_id,
            filename="test.pdf",
            file_type="application/pdf",
            file_size_bytes=1024,
            status=ExtractionStatus.PENDING,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_extraction
        mock_db.execute.return_value = mock_result

        result = await service.update_status(
            extraction_id, ExtractionStatus.PARSING
        )

        assert result.status == ExtractionStatus.PARSING
        assert result.processing_started_at is not None

    @pytest.mark.asyncio
    async def test_update_status_to_completed_sets_completed_at(
        self, service, mock_db: AsyncMock
    ) -> None:
        """Updating status to COMPLETED should set processing_completed_at."""
        extraction_id = uuid.uuid4()
        mock_extraction = DocumentExtraction(
            id=extraction_id,
            filename="test.pdf",
            file_type="application/pdf",
            file_size_bytes=1024,
            status=ExtractionStatus.ROUTING,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_extraction
        mock_db.execute.return_value = mock_result

        result = await service.update_status(
            extraction_id, ExtractionStatus.COMPLETED
        )

        assert result.status == ExtractionStatus.COMPLETED
        assert result.processing_completed_at is not None

    @pytest.mark.asyncio
    async def test_update_status_to_failed_sets_error(
        self, service, mock_db: AsyncMock
    ) -> None:
        """Updating status to FAILED should set error_message and completed_at."""
        extraction_id = uuid.uuid4()
        mock_extraction = DocumentExtraction(
            id=extraction_id,
            filename="test.pdf",
            file_type="application/pdf",
            file_size_bytes=1024,
            status=ExtractionStatus.PARSING,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_extraction
        mock_db.execute.return_value = mock_result

        result = await service.update_status(
            extraction_id,
            ExtractionStatus.FAILED,
            error_message="Azure DI timeout",
        )

        assert result.status == ExtractionStatus.FAILED
        assert result.error_message == "Azure DI timeout"
        assert result.processing_completed_at is not None

    @pytest.mark.asyncio
    async def test_update_status_not_found_raises(
        self, service, mock_db: AsyncMock
    ) -> None:
        """Updating status for non-existent extraction should raise NotFoundException."""
        from src.exceptions import NotFoundException

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundException):
            await service.update_status(
                uuid.uuid4(), ExtractionStatus.PARSING
            )

    @pytest.mark.asyncio
    async def test_save_extracted_items(self, service, mock_db: AsyncMock) -> None:
        """Saving extracted items should create ExtractedLineItem records."""
        extraction_id = uuid.uuid4()
        items = [
            {
                "line_number": 1,
                "raw_text": "Safety helmet white",
                "normalized_description": "Safety helmet white",
                "detected_quantity": 50.0,
                "detected_unit": "pcs",
                "detected_impa_code": "390145",
            },
            {
                "line_number": 2,
                "raw_text": "Rope manila 50mm",
                "normalized_description": "Rope manila 50mm",
            },
        ]

        result = await service.save_extracted_items(extraction_id, items)

        assert len(result) == 2
        assert result[0].line_number == 1
        assert result[0].raw_text == "Safety helmet white"
        assert result[0].detected_impa_code == "390145"
        assert result[1].line_number == 2
        assert result[1].raw_text == "Rope manila 50mm"
        assert mock_db.add.call_count == 2
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_verify_item(self, service, mock_db: AsyncMock) -> None:
        """Verifying an item should set user_verified and optionally corrected_impa."""
        item_id = uuid.uuid4()
        mock_item = ExtractedLineItem(
            id=item_id,
            extraction_id=uuid.uuid4(),
            line_number=1,
            raw_text="Safety helmet",
            user_verified=False,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute.return_value = mock_result

        result = await service.verify_item(item_id, corrected_impa="390146")

        assert result.user_verified is True
        assert result.user_corrected_impa == "390146"

    @pytest.mark.asyncio
    async def test_verify_item_without_correction(
        self, service, mock_db: AsyncMock
    ) -> None:
        """Verifying without corrected_impa should only set user_verified."""
        item_id = uuid.uuid4()
        mock_item = ExtractedLineItem(
            id=item_id,
            extraction_id=uuid.uuid4(),
            line_number=1,
            raw_text="Safety helmet",
            user_verified=False,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute.return_value = mock_result

        result = await service.verify_item(item_id)

        assert result.user_verified is True
        assert result.user_corrected_impa is None


# ═══════════════════════════════════════════════════════════════════════════
# Dedup Service tests
# ═══════════════════════════════════════════════════════════════════════════


class TestDedupService:
    """Tests for DedupService duplicate detection."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def dedup_service(self, mock_db: AsyncMock):
        from src.modules.document_ai.dedup_service import DedupService

        return DedupService(mock_db)

    @pytest.mark.asyncio
    async def test_find_duplicates_across_extractions(
        self, dedup_service, mock_db: AsyncMock
    ) -> None:
        """Items with same IMPA code across different extractions are flagged."""
        rfq_id = uuid.uuid4()
        extraction_id_1 = uuid.uuid4()
        extraction_id_2 = uuid.uuid4()

        extraction_1 = MagicMock()
        extraction_1.id = extraction_id_1
        extraction_1.filename = "doc1.pdf"

        extraction_2 = MagicMock()
        extraction_2.id = extraction_id_2
        extraction_2.filename = "doc2.pdf"

        item_1 = MagicMock()
        item_1.id = uuid.uuid4()
        item_1.extraction_id = extraction_id_1
        item_1.matched_impa_code = "390145"
        item_1.detected_quantity = Decimal("50")
        item_1.line_number = 1

        item_2 = MagicMock()
        item_2.id = uuid.uuid4()
        item_2.extraction_id = extraction_id_2
        item_2.matched_impa_code = "390145"
        item_2.detected_quantity = Decimal("50")
        item_2.line_number = 1

        # Mock the extractions query
        extractions_result = MagicMock()
        extractions_result.scalars.return_value.all.return_value = [
            extraction_1,
            extraction_2,
        ]

        # Mock the line items query
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [item_1, item_2]

        mock_db.execute.side_effect = [extractions_result, items_result]

        duplicates = await dedup_service.find_duplicates(
            extraction_id=extraction_id_1, rfq_id=rfq_id
        )

        assert len(duplicates) == 1
        assert duplicates[0].impa_code == "390145"
        assert len(duplicates[0].items) == 2

    @pytest.mark.asyncio
    async def test_no_duplicates_single_extraction(
        self, dedup_service, mock_db: AsyncMock
    ) -> None:
        """Items in a single extraction should not be flagged as duplicates."""
        rfq_id = uuid.uuid4()
        extraction_id = uuid.uuid4()

        extraction = MagicMock()
        extraction.id = extraction_id
        extraction.filename = "doc1.pdf"

        item_1 = MagicMock()
        item_1.id = uuid.uuid4()
        item_1.extraction_id = extraction_id
        item_1.matched_impa_code = "390145"
        item_1.detected_quantity = Decimal("50")

        item_2 = MagicMock()
        item_2.id = uuid.uuid4()
        item_2.extraction_id = extraction_id
        item_2.matched_impa_code = "390145"
        item_2.detected_quantity = Decimal("50")

        extractions_result = MagicMock()
        extractions_result.scalars.return_value.all.return_value = [extraction]

        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [item_1, item_2]

        mock_db.execute.side_effect = [extractions_result, items_result]

        duplicates = await dedup_service.find_duplicates(
            extraction_id=extraction_id, rfq_id=rfq_id
        )

        assert len(duplicates) == 0

    @pytest.mark.asyncio
    async def test_no_duplicates_empty_rfq(
        self, dedup_service, mock_db: AsyncMock
    ) -> None:
        """No extractions for RFQ should return empty list."""
        extractions_result = MagicMock()
        extractions_result.scalars.return_value.all.return_value = []

        mock_db.execute.return_value = extractions_result

        duplicates = await dedup_service.find_duplicates(
            extraction_id=uuid.uuid4(), rfq_id=uuid.uuid4()
        )

        assert len(duplicates) == 0


# ═══════════════════════════════════════════════════════════════════════════
# Confidence routing tests
# ═══════════════════════════════════════════════════════════════════════════


class TestConfidenceRouting:
    """Test confidence tier assignment based on thresholds."""

    def test_auto_tier_for_high_confidence(self) -> None:
        """Items with confidence >= 0.95 should be AUTO."""
        auto_threshold = 0.95
        quick_review_threshold = 0.80

        confidence = 0.98
        if confidence >= auto_threshold:
            tier = ExtractionConfidenceTier.AUTO
        elif confidence >= quick_review_threshold:
            tier = ExtractionConfidenceTier.QUICK_REVIEW
        else:
            tier = ExtractionConfidenceTier.FULL_REVIEW

        assert tier == ExtractionConfidenceTier.AUTO

    def test_quick_review_tier_for_medium_confidence(self) -> None:
        """Items with confidence 0.80-0.94 should be QUICK_REVIEW."""
        auto_threshold = 0.95
        quick_review_threshold = 0.80

        confidence = 0.87
        if confidence >= auto_threshold:
            tier = ExtractionConfidenceTier.AUTO
        elif confidence >= quick_review_threshold:
            tier = ExtractionConfidenceTier.QUICK_REVIEW
        else:
            tier = ExtractionConfidenceTier.FULL_REVIEW

        assert tier == ExtractionConfidenceTier.QUICK_REVIEW

    def test_full_review_tier_for_low_confidence(self) -> None:
        """Items with confidence < 0.80 should be FULL_REVIEW."""
        auto_threshold = 0.95
        quick_review_threshold = 0.80

        confidence = 0.65
        if confidence >= auto_threshold:
            tier = ExtractionConfidenceTier.AUTO
        elif confidence >= quick_review_threshold:
            tier = ExtractionConfidenceTier.QUICK_REVIEW
        else:
            tier = ExtractionConfidenceTier.FULL_REVIEW

        assert tier == ExtractionConfidenceTier.FULL_REVIEW

    def test_boundary_auto_threshold(self) -> None:
        """Items with confidence exactly 0.95 should be AUTO."""
        auto_threshold = 0.95
        confidence = 0.95

        if confidence >= auto_threshold:
            tier = ExtractionConfidenceTier.AUTO
        else:
            tier = ExtractionConfidenceTier.QUICK_REVIEW

        assert tier == ExtractionConfidenceTier.AUTO

    def test_boundary_quick_review_threshold(self) -> None:
        """Items with confidence exactly 0.80 should be QUICK_REVIEW."""
        auto_threshold = 0.95
        quick_review_threshold = 0.80
        confidence = 0.80

        if confidence >= auto_threshold:
            tier = ExtractionConfidenceTier.AUTO
        elif confidence >= quick_review_threshold:
            tier = ExtractionConfidenceTier.QUICK_REVIEW
        else:
            tier = ExtractionConfidenceTier.FULL_REVIEW

        assert tier == ExtractionConfidenceTier.QUICK_REVIEW

    def test_zero_confidence_is_full_review(self) -> None:
        """Items with 0 confidence should be FULL_REVIEW."""
        auto_threshold = 0.95
        quick_review_threshold = 0.80
        confidence = 0.0

        if confidence >= auto_threshold:
            tier = ExtractionConfidenceTier.AUTO
        elif confidence >= quick_review_threshold:
            tier = ExtractionConfidenceTier.QUICK_REVIEW
        else:
            tier = ExtractionConfidenceTier.FULL_REVIEW

        assert tier == ExtractionConfidenceTier.FULL_REVIEW


# ═══════════════════════════════════════════════════════════════════════════
# Schema / model integration tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSchemas:
    """Test Pydantic schema validation."""

    def test_extraction_create_request_minimal(self) -> None:
        from src.modules.document_ai.schemas import ExtractionCreateRequest

        req = ExtractionCreateRequest(
            filename="test.pdf",
            file_type="application/pdf",
            file_size_bytes=1024,
        )
        assert req.filename == "test.pdf"
        assert req.rfq_id is None
        assert req.document_type is None

    def test_extraction_create_request_full(self) -> None:
        from src.modules.document_ai.schemas import ExtractionCreateRequest

        rfq_id = uuid.uuid4()
        req = ExtractionCreateRequest(
            filename="order.xlsx",
            file_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            file_size_bytes=2048,
            rfq_id=rfq_id,
            document_type=DocumentType.PURCHASE_ORDER,
        )
        assert req.rfq_id == rfq_id
        assert req.document_type == DocumentType.PURCHASE_ORDER

    def test_match_result_schema(self) -> None:
        from src.modules.document_ai.schemas import MatchResult

        result = MatchResult(
            impa_code="390145",
            product_id=uuid.uuid4(),
            product_name="Safety Helmet",
            confidence=0.95,
            method="regex",
        )
        assert result.impa_code == "390145"
        assert result.confidence == 0.95
        assert len(result.alternatives) == 0

    def test_item_verify_request_optional_impa(self) -> None:
        from src.modules.document_ai.schemas import ItemVerifyRequest

        req = ItemVerifyRequest()
        assert req.corrected_impa is None

        req_with_correction = ItemVerifyRequest(corrected_impa="390146")
        assert req_with_correction.corrected_impa == "390146"

    def test_convert_request_optional_ids(self) -> None:
        from src.modules.document_ai.schemas import ConvertToLineItemsRequest

        extraction_id = uuid.uuid4()
        req = ConvertToLineItemsRequest(extraction_id=extraction_id)
        assert req.item_ids is None

        item_ids = [uuid.uuid4(), uuid.uuid4()]
        req_with_ids = ConvertToLineItemsRequest(
            extraction_id=extraction_id, item_ids=item_ids
        )
        assert len(req_with_ids.item_ids) == 2
