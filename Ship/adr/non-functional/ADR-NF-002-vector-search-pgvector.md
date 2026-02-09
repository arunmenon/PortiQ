# ADR-NF-002: Vector Search with pgvector

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Data

---

## Context

The document AI pipeline requires semantic search capability to match extracted line items against the product catalog, finding similar products even when exact text doesn't match.

### Business Context
Maritime requisitions contain varied product descriptions that don't always match catalog entries exactly:
- "SS Bolt M10x50" should match "Stainless Steel Hexagonal Bolt, Metric 10mm x 50mm"
- "Safety helmet" should match products in the "Protective Gear" category
- Abbreviated or misspelled items need fuzzy matching

Vector embeddings enable semantic similarity matching that goes beyond keyword search.

### Technical Context
- PostgreSQL as primary database (ADR-NF-001)
- 50K+ products in catalog, growing to 100K+
- Embeddings from OpenAI (1536 dimensions) or similar
- Sub-100ms query latency required for interactive use
- Integration with document AI pipeline (ADR-FN-006)

### Assumptions
- Embedding generation done asynchronously during ingestion
- Query volume moderate (not real-time for all users)
- Approximate nearest neighbor acceptable
- PostgreSQL can handle vector workload at our scale

---

## Decision Drivers

- Integration with existing PostgreSQL database
- Query performance for interactive use
- Operational simplicity
- Cost efficiency
- Accuracy of semantic matching
- Scalability to 100K+ products

---

## Considered Options

### Option 1: pgvector Extension
**Description:** PostgreSQL extension for vector similarity search with HNSW indexing.

**Pros:**
- Native PostgreSQL integration
- Single database, no synchronization
- HNSW index for fast approximate search
- Supports common distance metrics
- Joins with other tables
- No additional infrastructure

**Cons:**
- Extension dependency
- Less specialized than dedicated vector DBs
- Performance ceiling at very large scale

### Option 2: Dedicated Vector Database (Pinecone)
**Description:** Managed vector database service optimized for similarity search.

**Pros:**
- Purpose-built for vectors
- Managed service
- Highly optimized
- Auto-scaling

**Cons:**
- Additional service to manage
- Data synchronization required
- Additional costs
- No SQL joins

### Option 3: Elasticsearch with Dense Vectors
**Description:** Elasticsearch/OpenSearch with KNN plugin for vector search.

**Pros:**
- Combines text and vector search
- Already common infrastructure
- Good tooling

**Cons:**
- Another system to manage
- Synchronization needed
- Resource intensive
- Overkill if only for vectors

### Option 4: Self-Hosted Milvus/Weaviate
**Description:** Open-source vector databases deployed in-house.

**Pros:**
- Purpose-built for vectors
- Advanced features
- No vendor lock-in

**Cons:**
- Operational overhead
- Infrastructure complexity
- Scaling challenges

---

## Decision

**Chosen Option:** pgvector Extension

We will use the pgvector extension for PostgreSQL to handle vector similarity search, leveraging HNSW indexing for performance.

### Rationale
pgvector eliminates the need for a separate vector database, maintaining our unified PostgreSQL strategy. At our scale (50-100K products), pgvector with HNSW indexing delivers sub-50ms queries—sufficient for interactive use. The ability to join vector results with product data in a single query simplifies the application layer significantly.

---

## Consequences

### Positive
- Single database simplifies architecture
- No data synchronization needed
- SQL joins with product data
- Lower infrastructure costs
- Simpler operations

### Negative
- Not as optimized as dedicated vector DBs
- **Mitigation:** HNSW indexing provides good performance; monitor and optimize
- Large vectors increase storage
- **Mitigation:** Storage is cheap; use appropriate embedding dimensions

### Risks
- Performance degradation at scale: Monitor query times, consider partitioning or dedicated vector DB if needed
- Index rebuild times: Schedule during low-traffic periods

---

## Implementation Notes

### Schema Setup

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to products
ALTER TABLE products
ADD COLUMN embedding vector(1536);  -- OpenAI ada-002 dimension

-- Create HNSW index for fast approximate nearest neighbor
CREATE INDEX idx_products_embedding
ON products
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Index parameters:
-- m: Max connections per layer (higher = more accurate, more memory)
-- ef_construction: Size of dynamic candidate list (higher = better quality, slower build)
```

### Embedding Generation Service

```python
# src/modules/search/embedding.py
from openai import AsyncOpenAI
from src.config import settings

class EmbeddingService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def generate_embedding(self, text: str) -> list[float]:
        response = await self.client.embeddings.create(
            model="text-embedding-ada-002",
            input=text,
        )
        return response.data[0].embedding

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        # Batch processing for efficiency
        response = await self.client.embeddings.create(
            model="text-embedding-ada-002",
            input=texts,
        )
        return [d.embedding for d in response.data]

    def build_product_text(self, product) -> str:
        # Combine relevant fields for embedding
        parts = [
            product.name,
            product.description,
            product.impa_code,
            product.category.name if product.category else None,
            *(str(v) for v in (product.specifications or {}).values()),
        ]
        return " ".join(p for p in parts if p)
```

### Vector Search Service

```python
# src/modules/search/service.py
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

class VectorSearchService:
    def __init__(self, session: AsyncSession, embedding_service: EmbeddingService):
        self.session = session
        self.embedding_service = embedding_service

    async def search_similar_products(
        self, query: str, *, limit: int = 10, min_similarity: float = 0.5,
        category_filter: str | None = None,
    ) -> list[dict]:
        query_embedding = await self.embedding_service.generate_embedding(query)
        embedding_str = f"[{','.join(str(v) for v in query_embedding)}]"

        sql = text("""
            SELECT p.id, p.impa_code, p.name, p.description, p.category_id,
                   c.name AS category_name,
                   1 - (p.embedding <=> :embedding::vector) AS similarity
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.embedding IS NOT NULL
              AND 1 - (p.embedding <=> :embedding::vector) >= :min_sim
              AND (:cat_filter IS NULL OR p.category_id = :cat_filter::uuid)
            ORDER BY p.embedding <=> :embedding::vector
            LIMIT :lim
        """)
        result = await self.session.execute(sql, {
            "embedding": embedding_str,
            "min_sim": min_similarity,
            "lim": limit,
            "cat_filter": category_filter,
        })
        return [dict(row._mapping) for row in result]

    async def find_matching_product(self, extracted_item) -> list[dict]:
        search_text = " ".join(
            p for p in [extracted_item.product_name, extracted_item.specifications] if p
        )
        candidates = await self.search_similar_products(
            search_text, limit=20, min_similarity=0.4,
        )
        reranked = self._rerank_candidates(extracted_item, candidates)
        return [
            {"product": c, "confidence": self._calculate_confidence(c, extracted_item)}
            for c in reranked[:5]
        ]
```

### Batch Embedding Generation Job

```python
# src/modules/search/tasks.py
from celery import shared_task
from sqlalchemy import text
from src.database.engine import sync_session

@shared_task(bind=True, max_retries=3)
def generate_embeddings(self, product_ids: list[str]):
    """Celery task: batch-generate embeddings for products."""
    from src.modules.search.embedding import EmbeddingService
    embedding_service = EmbeddingService()
    batch_size = 100

    for i in range(0, len(product_ids), batch_size):
        batch = product_ids[i : i + batch_size]
        with sync_session() as session:
            products = session.execute(
                text("SELECT id, name, description, impa_code FROM products WHERE id = ANY(:ids)"),
                {"ids": batch},
            ).fetchall()

            texts = [embedding_service.build_product_text(p) for p in products]
            embeddings = embedding_service.generate_embeddings_sync(texts)

            for product, emb in zip(products, embeddings):
                session.execute(
                    text("UPDATE products SET embedding = :emb::vector WHERE id = :id"),
                    {"emb": f"[{','.join(str(v) for v in emb)}]", "id": product.id},
                )
            session.commit()

        self.update_state(
            state="PROGRESS",
            meta={"current": min(i + batch_size, len(product_ids)), "total": len(product_ids)},
        )
```

### Query Optimization

```sql
-- Set HNSW search parameters at session level
SET hnsw.ef_search = 100;  -- Higher = more accurate, slower

-- Use with SET LOCAL in transaction for specific queries
BEGIN;
SET LOCAL hnsw.ef_search = 200;  -- More accurate for critical matching
SELECT * FROM products
ORDER BY embedding <=> $1
LIMIT 10;
COMMIT;

-- Monitor index usage
SELECT
  indexrelname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
FROM pg_stat_user_indexes
WHERE indexrelname = 'idx_products_embedding';
```

### Dependencies
- ADR-NF-001: PostgreSQL as Unified Data Store
- ADR-FN-006: Document AI Pipeline Architecture
- ADR-FN-008: LLM Provider for Normalization

### Migration Strategy
1. Enable pgvector extension
2. Add embedding column to products table
3. Create HNSW index
4. Generate embeddings for existing products (batch job)
5. Integrate embedding generation into product ingestion
6. Build search service
7. Performance test and tune index parameters

---

## Index Configuration and Performance Targets

### HNSW Index Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Index Type** | HNSW | Best balance of speed and recall for our scale |
| **m** | 16 | Connections per node; good default for 50-100K vectors |
| **ef_construction** | 64 | Build quality; higher for better recall |
| **ef_search** | 100 | Query-time search breadth (adjustable per query) |
| **Distance Metric** | Cosine | Standard for text embeddings |

### Performance Benchmarks (Targets)

| Metric | Target | Acceptable | Action Trigger |
|--------|--------|------------|----------------|
| **Query Latency (p50)** | <20ms | <50ms | Investigate at >50ms |
| **Query Latency (p99)** | <50ms | <100ms | Tune ef_search or upgrade |
| **Recall@10** | >95% | >90% | Increase ef_construction |
| **Index Build Time** | <30min for 100K | <1hr | Acceptable for nightly |

### Benchmark Methodology

```sql
-- Create test dataset for benchmarking
-- 1. Generate ground truth with exact search (slow but accurate)
CREATE TEMP TABLE ground_truth AS
SELECT query_id, array_agg(product_id ORDER BY embedding <-> query_embedding) as exact_results
FROM test_queries, products
GROUP BY query_id;

-- 2. Run approximate search and compare
-- Recall = |approximate ∩ exact| / k
```

## Embedding Lifecycle Management

### Embedding Refresh Strategy

| Trigger | Action | Frequency |
|---------|--------|-----------|
| Product created | Generate embedding | Immediate (async) |
| Product name/description updated | Regenerate embedding | Immediate (async) |
| Embedding model changed | Full re-generation | Manual migration |
| Category structure changed | Re-index affected products | Batch job |

### Versioning Strategy

```sql
-- Track embedding model version for future migrations
ALTER TABLE products ADD COLUMN embedding_model VARCHAR(50) DEFAULT 'text-embedding-ada-002';
ALTER TABLE products ADD COLUMN embedding_updated_at TIMESTAMPTZ;

-- When embedding model changes, track which products need re-embedding
CREATE INDEX idx_products_embedding_model ON products(embedding_model)
WHERE embedding IS NOT NULL;
```

**Migration Process for Model Changes:**
1. Add new embedding column (`embedding_v2`)
2. Batch generate new embeddings in background
3. A/B test new model performance
4. Switch application to use new column
5. Drop old column after validation

### Storage Growth Planning

| Products | Embedding Size | Storage | Index Size |
|----------|----------------|---------|------------|
| 50,000 | 1536 × 4 bytes | ~300 MB | ~400 MB |
| 100,000 | 1536 × 4 bytes | ~600 MB | ~800 MB |
| 500,000 | 1536 × 4 bytes | ~3 GB | ~4 GB |
| 1,000,000 | 1536 × 4 bytes | ~6 GB | ~8 GB |

**Storage Optimization Options:**
- Use `halfvec` (16-bit) for 50% storage reduction with minimal recall loss
- Consider smaller embedding models (384 or 768 dimensions) for cost/performance tradeoff
- Archive embeddings for discontinued products

```sql
-- Optional: Use half-precision vectors for storage efficiency
ALTER TABLE products ADD COLUMN embedding_half halfvec(1536);
-- Requires pgvector 0.6.0+
```

## Search Use Case Requirements

### Recall and Latency Targets by Use Case

| Use Case | Recall Target | Latency Target | Priority |
|----------|---------------|----------------|----------|
| **Document AI Matching** | >95% | <100ms | Accuracy over speed |
| **Product Search Autocomplete** | >85% | <30ms | Speed over accuracy |
| **Similar Products Widget** | >80% | <50ms | Balanced |
| **Bulk Catalog Matching** | >90% | <500ms/item | Throughput |

### Query-Time Tuning

```python
# Adjust ef_search based on use case
async def search_with_precision(self, query: str, precision: str = "balanced"):
    ef_search = {"fast": 50, "balanced": 100, "accurate": 200}[precision]
    await self.session.execute(
        text(f"SET LOCAL hnsw.ef_search = {ef_search}")
    )
    # ... execute search
```

---

## References
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [HNSW Algorithm](https://arxiv.org/abs/1603.09320)
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
- [PostgreSQL Vector Search Benchmarks](https://supabase.com/blog/pgvector-performance)
