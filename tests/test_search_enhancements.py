"""Tests for Track B search enhancements: synonyms, faceted search, configurable weights, Celery tasks."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.modules.search.schemas import FacetCount, TextSearchResult
from src.modules.search.text_search import TextSearchService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_embedding_service():
    service = AsyncMock()
    service.generate_embedding.return_value = [0.0] * 1536
    return service


@pytest.fixture
def mock_session():
    """Returns an AsyncMock that behaves like an AsyncSession."""
    session = AsyncMock()
    return session


@pytest.fixture
def text_search_service(mock_session, mock_embedding_service):
    return TextSearchService(session=mock_session, embedding_service=mock_embedding_service)


# ---------------------------------------------------------------------------
# 1. Synonym expansion
# ---------------------------------------------------------------------------

class TestSynonymExpansion:
    @pytest.mark.asyncio
    async def test_expand_synonyms_with_known_terms(self, text_search_service, mock_session):
        """When a query term has synonyms, they should be appended to the query."""
        # Mock the DB response for synonym lookup
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [
            {"term": "bolt", "synonyms": ["fastener"]},
            {"term": "ss", "synonyms": ["stainless steel"]},
        ]
        mock_session.execute.return_value = mock_result

        expanded = await text_search_service._expand_synonyms("bolt ss fitting")
        assert "bolt ss fitting" in expanded
        assert "fastener" in expanded
        assert "stainless steel" in expanded

    @pytest.mark.asyncio
    async def test_expand_synonyms_no_matches(self, text_search_service, mock_session):
        """When no synonym matches, the original query is returned unchanged."""
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        expanded = await text_search_service._expand_synonyms("unknown widget")
        assert expanded == "unknown widget"

    @pytest.mark.asyncio
    async def test_expand_synonyms_empty_query(self, text_search_service):
        """Empty query returns empty string."""
        expanded = await text_search_service._expand_synonyms("")
        assert expanded == ""

    @pytest.mark.asyncio
    async def test_expand_synonyms_case_insensitive(self, text_search_service, mock_session):
        """Synonym lookup should lowercase query terms before lookup."""
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [
            {"term": "valve", "synonyms": ["stopcock"]},
        ]
        mock_session.execute.return_value = mock_result

        expanded = await text_search_service._expand_synonyms("VALVE")
        assert "stopcock" in expanded


# ---------------------------------------------------------------------------
# 2. Configurable weights
# ---------------------------------------------------------------------------

class TestConfigurableWeights:
    def test_default_weights(self):
        """Default weights should sum to 1.0 (approximately)."""
        assert TextSearchService.FTS_WEIGHT == 0.4
        assert TextSearchService.TRIGRAM_WEIGHT == 0.3
        assert TextSearchService.VECTOR_WEIGHT == 0.3
        total = TextSearchService.FTS_WEIGHT + TextSearchService.TRIGRAM_WEIGHT + TextSearchService.VECTOR_WEIGHT
        assert abs(total - 1.0) < 1e-9

    def test_weights_are_class_level(self):
        """Weights can be overridden at the class level."""
        original_fts = TextSearchService.FTS_WEIGHT
        try:
            TextSearchService.FTS_WEIGHT = 0.6
            assert TextSearchService.FTS_WEIGHT == 0.6
        finally:
            TextSearchService.FTS_WEIGHT = original_fts


# ---------------------------------------------------------------------------
# 3. FacetedSearchService
# ---------------------------------------------------------------------------

class TestFacetedSearchService:
    @pytest.mark.asyncio
    async def test_facet_counting(self, mock_session, mock_embedding_service):
        from src.modules.search.faceted_search import FacetedSearchService

        service = FacetedSearchService(session=mock_session, embedding_service=mock_embedding_service)

        # Mock the two SQL executions (results query, then facets query)
        product_id = uuid.uuid4()
        result_row = {
            "id": product_id,
            "impa_code": "123456",
            "name": "Test Bolt",
            "description": "A test bolt",
            "category_name": "Fasteners",
            "score": 0.85,
            "highlight": "<b>Test</b> Bolt",
            "total_count": 1,
        }

        facet_rows = [
            {"facet_kind": "category", "facet_value": "Fasteners", "facet_count": 5},
            {"facet_kind": "category", "facet_value": "Tools", "facet_count": 3},
            {"facet_kind": "ihm_relevant", "facet_value": "true", "facet_count": 4},
            {"facet_kind": "ihm_relevant", "facet_value": "false", "facet_count": 6},
            {"facet_kind": "hazmat_class", "facet_value": "3", "facet_count": 2},
        ]

        mock_result_1 = MagicMock()
        mock_result_1.mappings.return_value.all.return_value = [result_row]
        mock_result_2 = MagicMock()
        mock_result_2.mappings.return_value.all.return_value = facet_rows

        mock_session.execute.side_effect = [mock_result_1, mock_result_2]

        results, total, facets = await service.search_with_facets(query="bolt")

        assert total == 1
        assert len(results) == 1
        assert results[0].name == "Test Bolt"

        # Check facets
        assert "category" in facets
        assert len(facets["category"]) == 2
        assert facets["category"][0].value == "Fasteners"
        assert facets["category"][0].count == 5

        assert "ihm_relevant" in facets
        assert len(facets["ihm_relevant"]) == 2

        assert "hazmat_class" in facets
        assert len(facets["hazmat_class"]) == 1
        assert facets["hazmat_class"][0].value == "3"

    @pytest.mark.asyncio
    async def test_empty_results_return_empty_facets(self, mock_session, mock_embedding_service):
        from src.modules.search.faceted_search import FacetedSearchService

        service = FacetedSearchService(session=mock_session, embedding_service=mock_embedding_service)

        mock_result_1 = MagicMock()
        mock_result_1.mappings.return_value.all.return_value = []
        mock_result_2 = MagicMock()
        mock_result_2.mappings.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_result_1, mock_result_2]

        results, total, facets = await service.search_with_facets(query="nonexistent")

        assert total == 0
        assert len(results) == 0
        assert facets == {"category": [], "ihm_relevant": [], "hazmat_class": []}


# ---------------------------------------------------------------------------
# 4. Celery tasks (sync_search_index, bulk_generate_embeddings)
# ---------------------------------------------------------------------------

class TestCeleryTasks:
    @patch("src.modules.search.tasks.sync_engine")
    def test_sync_search_index_no_stale(self, mock_engine):
        """sync_search_index returns zeros when no stale products exist."""
        from src.modules.search.tasks import sync_search_index

        mock_session_ctx = MagicMock()
        mock_session = MagicMock()
        mock_session_ctx.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.__exit__ = MagicMock(return_value=False)

        # Patch Session to return our mock
        with patch("src.modules.search.tasks.Session", return_value=mock_session_ctx):
            mock_session.execute.return_value.scalar_one.return_value = 0

            # Call with a mock self (Celery task)
            mock_self = MagicMock()
            result = sync_search_index.__wrapped__(mock_self, )

        assert result == {"processed": 0, "total": 0, "errors": 0}

    @patch("src.modules.search.tasks.sync_engine")
    def test_bulk_generate_embeddings_no_missing(self, mock_engine):
        """bulk_generate_embeddings returns zeros when no products lack embeddings."""
        from src.modules.search.tasks import bulk_generate_embeddings

        mock_session_ctx = MagicMock()
        mock_session = MagicMock()
        mock_session_ctx.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.__exit__ = MagicMock(return_value=False)

        with patch("src.modules.search.tasks.Session", return_value=mock_session_ctx):
            mock_session.execute.return_value.scalar_one.return_value = 0

            mock_self = MagicMock()
            result = bulk_generate_embeddings.__wrapped__(mock_self, batch_size=100)

        assert result == {"processed": 0, "total": 0, "errors": 0}

    @patch("src.modules.search.tasks.sync_engine")
    def test_sync_search_index_processes_batch(self, mock_engine):
        """sync_search_index processes a batch of stale products."""
        from src.modules.search.tasks import sync_search_index

        mock_self = MagicMock()
        mock_self.retry.side_effect = Exception("retry")
        mock_self.MaxRetriesExceededError = Exception

        product_id = uuid.uuid4()
        product_row = MagicMock()
        product_row.id = product_id
        product_row.impa_code = "123456"
        product_row.name = "Test Product"
        product_row.description = "Description"
        product_row.category_name = "Category"

        mock_session_ctx = MagicMock()
        mock_session = MagicMock()
        mock_session_ctx.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.__exit__ = MagicMock(return_value=False)

        # First call: count query returns 1
        # Second call: fetch stale products returns 1 row
        # Third call: update embedding succeeds
        # Fourth call: fetch returns empty (loop end)
        call_count = 0
        def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one.return_value = 1
            elif call_count == 2:
                result.fetchall.return_value = [product_row]
            elif call_count == 4:
                result.fetchall.return_value = []
            return result

        mock_session.execute.side_effect = execute_side_effect

        mock_openai_client = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.1] * 1536
        mock_embedding.index = 0
        mock_openai_response = MagicMock()
        mock_openai_response.data = [mock_embedding]
        mock_openai_client.embeddings.create.return_value = mock_openai_response

        with patch("src.modules.search.tasks.Session", return_value=mock_session_ctx), \
             patch("openai.OpenAI", return_value=mock_openai_client):
            result = sync_search_index.__wrapped__(mock_self)

        assert result["processed"] == 1
        assert result["errors"] == 0

    @patch("src.modules.search.tasks.sync_engine")
    def test_bulk_generate_embeddings_processes_batch(self, mock_engine):
        """bulk_generate_embeddings processes products missing embeddings."""
        from src.modules.search.tasks import bulk_generate_embeddings

        mock_self = MagicMock()

        product_id = uuid.uuid4()
        product_row = MagicMock()
        product_row.id = product_id
        product_row.impa_code = "654321"
        product_row.name = "Bulk Product"
        product_row.description = "Bulk desc"
        product_row.category_name = "Tools"

        mock_session_ctx = MagicMock()
        mock_session = MagicMock()
        mock_session_ctx.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.__exit__ = MagicMock(return_value=False)

        call_count = 0
        def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one.return_value = 1
            elif call_count == 2:
                result.fetchall.return_value = [product_row]
            elif call_count == 4:
                result.fetchall.return_value = []
            return result

        mock_session.execute.side_effect = execute_side_effect

        mock_openai_client = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.2] * 1536
        mock_embedding.index = 0
        mock_openai_response = MagicMock()
        mock_openai_response.data = [mock_embedding]
        mock_openai_client.embeddings.create.return_value = mock_openai_response

        with patch("src.modules.search.tasks.Session", return_value=mock_session_ctx), \
             patch("openai.OpenAI", return_value=mock_openai_client):
            result = bulk_generate_embeddings.__wrapped__(mock_self, batch_size=100)

        assert result["processed"] == 1
        assert result["errors"] == 0


# ---------------------------------------------------------------------------
# 5. Schema validation
# ---------------------------------------------------------------------------

class TestSchemas:
    def test_faceted_search_response_structure(self):
        from src.modules.search.schemas import FacetedSearchResponse

        response = FacetedSearchResponse(
            results=[],
            query="test",
            total=0,
            page=1,
            total_pages=0,
            facets={"category": [], "ihm_relevant": [], "hazmat_class": []},
        )
        assert response.total == 0
        assert response.facets == {"category": [], "ihm_relevant": [], "hazmat_class": []}

    def test_synonym_entry_from_attributes(self):
        from src.modules.search.schemas import SynonymEntry

        entry = SynonymEntry(term="bolt", synonyms=["fastener"], domain="maritime")
        assert entry.term == "bolt"
        assert entry.synonyms == ["fastener"]
        assert entry.domain == "maritime"

    def test_faceted_search_request_defaults(self):
        from src.modules.search.schemas import FacetedSearchRequest

        req = FacetedSearchRequest(query="test")
        assert req.limit == 20
        assert req.page == 1
        assert req.category_id is None
        assert req.ihm_relevant is None
        assert req.hazmat_class is None
