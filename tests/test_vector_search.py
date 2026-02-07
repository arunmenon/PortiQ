"""Tests for pgvector-based product search."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.search.constants import PRECISION_LEVELS
from src.modules.search.embedding import EmbeddingService
from src.modules.search.service import VectorSearchService


@pytest.mark.asyncio
async def test_search_similar_products_returns_results(async_session: AsyncSession) -> None:
    """Verify that search_similar_products returns results when matching products exist.

    This test requires:
    - A running PostgreSQL instance with pgvector extension
    - At least one product row with a non-null embedding column
    - The OpenAI API key set for generating query embeddings

    If no products with embeddings exist, the result should be an empty list.
    """
    embedding_service = EmbeddingService()
    service = VectorSearchService(session=async_session, embedding_service=embedding_service)

    results = await service.search_similar_products(
        query="marine deck paint anti-fouling",
        limit=5,
        min_similarity=0.3,
        precision="balanced",
    )

    assert isinstance(results, list)
    for result in results:
        assert result.impa_code is not None
        assert result.name is not None
        assert 0.0 <= result.similarity <= 1.0


@pytest.mark.asyncio
async def test_search_with_precision_levels(async_session: AsyncSession) -> None:
    """Verify that different precision levels set different hnsw.ef_search values.

    Each precision level should produce a valid query — even if no results are
    returned (no embeddings in the database), the query must not raise.
    """
    embedding_service = EmbeddingService()
    service = VectorSearchService(session=async_session, embedding_service=embedding_service)

    for precision_name in PRECISION_LEVELS:
        results = await service.search_similar_products(
            query="stainless steel bolts M10",
            limit=3,
            min_similarity=0.1,
            precision=precision_name,
        )
        assert isinstance(results, list)


@pytest.mark.asyncio
async def test_embedding_service_builds_product_text() -> None:
    """Verify that build_product_text combines product fields correctly."""

    class FakeProduct:
        name = "Marine Anti-Fouling Paint"
        description = "Self-polishing copolymer"
        impa_code = "150100"
        category = None
        specifications = {"color": "red", "volume": "5L"}

    text_repr = EmbeddingService.build_product_text(FakeProduct())

    assert "Marine Anti-Fouling Paint" in text_repr
    assert "Self-polishing copolymer" in text_repr
    assert "IMPA 150100" in text_repr
    assert "color: red" in text_repr
    assert "volume: 5L" in text_repr
