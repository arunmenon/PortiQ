"""Search module — pgvector-based product similarity search and matching."""

from src.modules.search.embedding import EmbeddingService
from src.modules.search.service import VectorSearchService
from src.modules.search.text_search import TextSearchService

__all__ = [
    "EmbeddingService",
    "TextSearchService",
    "VectorSearchService",
]
