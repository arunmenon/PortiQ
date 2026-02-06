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

```typescript
// embedding/services/embedding.service.ts
import OpenAI from 'openai';

@Injectable()
export class EmbeddingService {
  private openai: OpenAI;

  constructor(private readonly configService: ConfigService) {
    this.openai = new OpenAI({
      apiKey: this.configService.get('OPENAI_API_KEY')
    });
  }

  async generateEmbedding(text: string): Promise<number[]> {
    const response = await this.openai.embeddings.create({
      model: 'text-embedding-ada-002',
      input: text
    });

    return response.data[0].embedding;
  }

  async generateEmbeddings(texts: string[]): Promise<number[][]> {
    // Batch processing for efficiency
    const response = await this.openai.embeddings.create({
      model: 'text-embedding-ada-002',
      input: texts
    });

    return response.data.map(d => d.embedding);
  }

  buildProductText(product: Product): string {
    // Combine relevant fields for embedding
    return [
      product.name,
      product.description,
      product.impaCode,
      product.category?.name,
      ...(product.specifications
        ? Object.values(product.specifications).map(String)
        : [])
    ].filter(Boolean).join(' ');
  }
}
```

### Vector Search Service

```typescript
// search/services/vector-search.service.ts
@Injectable()
export class VectorSearchService {
  constructor(
    private readonly dataSource: DataSource,
    private readonly embeddingService: EmbeddingService
  ) {}

  async searchSimilarProducts(
    query: string,
    options: VectorSearchOptions = {}
  ): Promise<SimilarProduct[]> {
    const {
      limit = 10,
      minSimilarity = 0.5,
      categoryFilter
    } = options;

    // Generate embedding for query
    const queryEmbedding = await this.embeddingService.generateEmbedding(query);

    // Perform vector similarity search
    const results = await this.dataSource.query(`
      SELECT
        p.id,
        p.impa_code,
        p.name,
        p.description,
        p.category_id,
        c.name as category_name,
        1 - (p.embedding <=> $1::vector) as similarity
      FROM products p
      LEFT JOIN categories c ON p.category_id = c.id
      WHERE p.embedding IS NOT NULL
        AND 1 - (p.embedding <=> $1::vector) >= $2
        ${categoryFilter ? 'AND p.category_id = $4' : ''}
      ORDER BY p.embedding <=> $1::vector
      LIMIT $3
    `, [
      `[${queryEmbedding.join(',')}]`,
      minSimilarity,
      limit,
      ...(categoryFilter ? [categoryFilter] : [])
    ]);

    return results.map(row => ({
      id: row.id,
      impaCode: row.impa_code,
      name: row.name,
      description: row.description,
      categoryName: row.category_name,
      similarity: row.similarity
    }));
  }

  async findMatchingProduct(
    extractedItem: ExtractedLineItem
  ): Promise<ProductMatch[]> {
    // Build search text from extracted data
    const searchText = [
      extractedItem.productName,
      extractedItem.specifications
    ].filter(Boolean).join(' ');

    // Search with higher limit for reranking
    const candidates = await this.searchSimilarProducts(searchText, {
      limit: 20,
      minSimilarity: 0.4
    });

    // Rerank using additional signals
    const reranked = await this.rerankCandidates(
      extractedItem,
      candidates
    );

    return reranked.slice(0, 5).map(c => ({
      product: c,
      confidence: this.calculateConfidence(c, extractedItem),
      matchReason: this.explainMatch(c, extractedItem)
    }));
  }

  private async rerankCandidates(
    query: ExtractedLineItem,
    candidates: SimilarProduct[]
  ): Promise<SimilarProduct[]> {
    // Additional scoring factors
    return candidates.map(candidate => {
      let boost = 0;

      // Exact IMPA code match
      if (query.impaCode && candidate.impaCode === query.impaCode) {
        boost += 0.3;
      }

      // Unit match
      if (query.unit && this.unitsMatch(query.unit, candidate)) {
        boost += 0.1;
      }

      return {
        ...candidate,
        similarity: Math.min(candidate.similarity + boost, 1.0)
      };
    }).sort((a, b) => b.similarity - a.similarity);
  }

  private calculateConfidence(
    product: SimilarProduct,
    extracted: ExtractedLineItem
  ): number {
    let confidence = product.similarity;

    // Adjust based on extraction confidence
    confidence *= extracted.confidence;

    // Penalize if category doesn't match expected
    if (extracted.expectedCategory &&
        product.categoryName !== extracted.expectedCategory) {
      confidence *= 0.8;
    }

    return confidence;
  }
}
```

### Batch Embedding Generation Job

```typescript
// embedding/jobs/generate-embeddings.job.ts
@Processor('embedding-generation')
export class GenerateEmbeddingsProcessor {
  constructor(
    private readonly embeddingService: EmbeddingService,
    private readonly productRepository: ProductRepository
  ) {}

  @Process('batch-generate')
  async handleBatchGenerate(job: Job<{ productIds: string[] }>) {
    const { productIds } = job.data;
    const batchSize = 100;

    for (let i = 0; i < productIds.length; i += batchSize) {
      const batch = productIds.slice(i, i + batchSize);
      const products = await this.productRepository.findByIds(batch);

      const texts = products.map(p =>
        this.embeddingService.buildProductText(p)
      );

      const embeddings = await this.embeddingService.generateEmbeddings(texts);

      // Update products with embeddings
      await Promise.all(
        products.map((product, idx) =>
          this.productRepository.updateEmbedding(product.id, embeddings[idx])
        )
      );

      // Update job progress
      await job.progress(Math.round((i + batchSize) / productIds.length * 100));
    }
  }
}
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

```typescript
// Adjust ef_search based on use case
async searchWithPrecision(query: string, precision: 'fast' | 'balanced' | 'accurate') {
  const efSearch = {
    fast: 50,      // Autocomplete
    balanced: 100, // Default
    accurate: 200  // Document AI matching
  }[precision];

  await this.dataSource.query(`SET LOCAL hnsw.ef_search = ${efSearch}`);
  // ... execute search
}
```

---

## References
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [HNSW Algorithm](https://arxiv.org/abs/1603.09320)
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
- [PostgreSQL Vector Search Benchmarks](https://supabase.com/blog/pgvector-performance)
