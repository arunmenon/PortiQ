"""Search module constants for pgvector-based product search."""

# HNSW index parameters
HNSW_M = 16
HNSW_EF_CONSTRUCTION = 64
HNSW_EF_SEARCH_DEFAULT = 100

# Embedding configuration
EMBEDDING_MODEL = "text-embedding-ada-002"
EMBEDDING_DIMENSIONS = 1536
EMBEDDING_BATCH_SIZE = 100

# Reranking boosts (added to cosine similarity score)
IMPA_CODE_MATCH_BOOST = 0.3
UNIT_MATCH_BOOST = 0.1

# Search precision levels — maps precision name to hnsw.ef_search value
PRECISION_LEVELS: dict[str, int] = {
    "fast": 50,
    "balanced": 100,
    "accurate": 200,
}
