# ADR-NF-003: Search Engine - Meilisearch

**Status:** Superseded
**Date:** 2025-01-20
**Technical Area:** Infrastructure

**Superseded By:** PostgreSQL-native hybrid search (FTS + pg_trgm + pgvector)
**Superseded Date:** 2026-02-06
**Rationale:** At 50K-100K products, PostgreSQL FTS + pg_trgm + pgvector provides
sub-50ms search with zero sync infrastructure. Meilisearch adds operational complexity
(data sync pipeline, separate service) not justified at current scale. Revisit if
search quality proves insufficient after real user testing, or when ParadeDB pg_search
becomes available on AWS RDS.

---

## Context

The platform requires fast, typo-tolerant product search with faceted filtering to enable efficient catalog navigation for buyers and procurement teams.

### Business Context
Maritime procurement professionals need to find products quickly:
- Search by product name, IMPA code, or description
- Handle typos and abbreviations common in the industry
- Filter by category, supplier, certification, price range
- Auto-complete suggestions as users type
- Sub-100ms response for interactive experience

### Technical Context
- 50K+ products growing to 100K+
- PostgreSQL as primary data store (ADR-NF-001)
- pgvector for semantic search (ADR-NF-002)
- Need text search complementary to vector search
- Real-time index updates as catalog changes

### Assumptions
- Text search and vector search serve different purposes
- Typo tolerance is important for user experience
- Faceted filtering required for catalog navigation
- Index synchronization latency of seconds is acceptable

---

## Decision Drivers

- Search speed (sub-50ms)
- Typo tolerance and fuzzy matching
- Faceted filtering capability
- Ease of setup and operation
- Integration with Node.js/TypeScript
- Cost efficiency

---

## Considered Options

### Option 1: Meilisearch
**Description:** Modern, fast, typo-tolerant search engine designed for end-user search.

**Pros:**
- Sub-50ms search responses
- Built-in typo tolerance
- Easy faceted filtering
- Simple API and SDKs
- Hybrid keyword + semantic search (2024+)
- Minimal configuration
- Self-hosted or cloud

**Cons:**
- Less mature than Elasticsearch
- Smaller ecosystem
- Single-node (no distributed mode yet)

### Option 2: Elasticsearch
**Description:** Industry-standard search and analytics engine.

**Pros:**
- Highly mature and proven
- Distributed architecture
- Extensive features
- Large ecosystem

**Cons:**
- Complex to configure and operate
- Resource intensive
- Overkill for product search
- Steep learning curve

### Option 3: Algolia
**Description:** Managed search-as-a-service platform.

**Pros:**
- Excellent search quality
- Fully managed
- Great developer experience
- Instant results

**Cons:**
- Expensive at scale
- Vendor lock-in
- Limited customization
- Per-record pricing

### Option 4: PostgreSQL Full-Text Search
**Description:** Native PostgreSQL text search with ts_vector.

**Pros:**
- No additional infrastructure
- Native integration
- Good for basic search

**Cons:**
- Limited typo tolerance
- Basic ranking
- No faceting
- Slower than dedicated engines

---

## Decision

**Chosen Option:** Meilisearch

We will use Meilisearch for product catalog search, providing fast, typo-tolerant search with faceted filtering capability.

### Rationale
Meilisearch offers the best balance of search quality, ease of use, and operational simplicity for product catalog search. Its built-in typo tolerance handles the abbreviated and misspelled terms common in maritime procurement. Configuration takes minutes rather than days compared to Elasticsearch. Recent hybrid search capabilities complement our pgvector semantic search.

---

## Consequences

### Positive
- Sub-50ms search responses
- Excellent typo tolerance out of box
- Simple setup and operation
- Great developer experience
- Cost-effective self-hosting

### Negative
- Additional service to operate
- **Mitigation:** Simple to deploy, low maintenance
- Index synchronization required
- **Mitigation:** Event-driven sync, acceptable latency

### Risks
- Data inconsistency: Implement robust sync, handle failures
- Meilisearch limitations at scale: Monitor growth, plan migration path if needed
- Single point of failure: Deploy with redundancy, fallback to PostgreSQL search

---

## Implementation Notes

### Deployment Configuration

```yaml
# docker-compose.yml (development)
services:
  meilisearch:
    image: getmeili/meilisearch:v1.6
    environment:
      - MEILI_MASTER_KEY=${MEILI_MASTER_KEY}
      - MEILI_ENV=development
    ports:
      - "7700:7700"
    volumes:
      - meilisearch_data:/meili_data

# kubernetes/meilisearch.yaml (production)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: meilisearch
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: meilisearch
          image: getmeili/meilisearch:v1.6
          env:
            - name: MEILI_MASTER_KEY
              valueFrom:
                secretKeyRef:
                  name: meilisearch-secrets
                  key: master-key
            - name: MEILI_ENV
              value: production
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "2Gi"
              cpu: "1000m"
          volumeMounts:
            - name: data
              mountPath: /meili_data
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: meilisearch-pvc
```

### Index Configuration

```typescript
// search/config/meilisearch.config.ts
export const productIndexConfig = {
  primaryKey: 'id',

  searchableAttributes: [
    'name',
    'description',
    'impaCode',
    'issaCode',
    'categoryName',
    'supplierName',
    'specifications'
  ],

  filterableAttributes: [
    'categoryId',
    'categoryName',
    'supplierId',
    'supplierName',
    'ihmRelevant',
    'certifications',
    'priceRange',
    'inStock'
  ],

  sortableAttributes: [
    'name',
    'impaCode',
    'price',
    'createdAt',
    'popularity'
  ],

  rankingRules: [
    'words',
    'typo',
    'proximity',
    'attribute',
    'sort',
    'exactness',
    'popularity:desc'  // Custom ranking
  ],

  typoTolerance: {
    enabled: true,
    minWordSizeForTypos: {
      oneTypo: 4,
      twoTypos: 8
    }
  },

  faceting: {
    maxValuesPerFacet: 100
  },

  pagination: {
    maxTotalHits: 1000
  }
};
```

### Meilisearch Service

```typescript
// search/services/meilisearch.service.ts
import { MeiliSearch, Index } from 'meilisearch';

@Injectable()
export class MeilisearchService {
  private client: MeiliSearch;
  private productIndex: Index;

  constructor(private readonly configService: ConfigService) {
    this.client = new MeiliSearch({
      host: this.configService.get('MEILISEARCH_HOST'),
      apiKey: this.configService.get('MEILISEARCH_API_KEY')
    });
    this.productIndex = this.client.index('products');
  }

  async initialize(): Promise<void> {
    // Create index if not exists
    await this.client.createIndex('products', { primaryKey: 'id' });

    // Configure index settings
    await this.productIndex.updateSettings(productIndexConfig);
  }

  async searchProducts(
    query: string,
    options: SearchOptions = {}
  ): Promise<SearchResult<ProductDocument>> {
    const {
      filters,
      facets,
      page = 1,
      hitsPerPage = 20,
      sort
    } = options;

    const searchParams: any = {
      q: query,
      page,
      hitsPerPage,
      attributesToRetrieve: [
        'id', 'impaCode', 'name', 'description',
        'categoryName', 'price', 'inStock', 'supplierName'
      ],
      attributesToHighlight: ['name', 'description']
    };

    // Build filter string
    if (filters) {
      searchParams.filter = this.buildFilterString(filters);
    }

    // Add facets
    if (facets) {
      searchParams.facets = facets;
    }

    // Add sorting
    if (sort) {
      searchParams.sort = [sort];
    }

    const result = await this.productIndex.search(query, searchParams);

    return {
      hits: result.hits,
      totalHits: result.estimatedTotalHits,
      page: result.page,
      totalPages: result.totalPages,
      facetDistribution: result.facetDistribution,
      processingTimeMs: result.processingTimeMs
    };
  }

  private buildFilterString(filters: SearchFilters): string {
    const conditions: string[] = [];

    if (filters.categoryId) {
      conditions.push(`categoryId = "${filters.categoryId}"`);
    }

    if (filters.supplierId) {
      conditions.push(`supplierId = "${filters.supplierId}"`);
    }

    if (filters.ihmRelevant !== undefined) {
      conditions.push(`ihmRelevant = ${filters.ihmRelevant}`);
    }

    if (filters.priceMin !== undefined || filters.priceMax !== undefined) {
      if (filters.priceMin !== undefined && filters.priceMax !== undefined) {
        conditions.push(`price ${filters.priceMin} TO ${filters.priceMax}`);
      } else if (filters.priceMin !== undefined) {
        conditions.push(`price >= ${filters.priceMin}`);
      } else {
        conditions.push(`price <= ${filters.priceMax}`);
      }
    }

    if (filters.certifications?.length) {
      const certFilter = filters.certifications
        .map(c => `certifications = "${c}"`)
        .join(' OR ');
      conditions.push(`(${certFilter})`);
    }

    return conditions.join(' AND ');
  }

  async indexProduct(product: Product): Promise<void> {
    const document = this.mapToDocument(product);
    await this.productIndex.addDocuments([document]);
  }

  async indexProducts(products: Product[]): Promise<void> {
    const documents = products.map(p => this.mapToDocument(p));
    await this.productIndex.addDocuments(documents, { primaryKey: 'id' });
  }

  async removeProduct(productId: string): Promise<void> {
    await this.productIndex.deleteDocument(productId);
  }

  private mapToDocument(product: Product): ProductDocument {
    return {
      id: product.id,
      impaCode: product.impaCode,
      issaCode: product.issaCode,
      name: product.name,
      description: product.description,
      categoryId: product.categoryId,
      categoryName: product.category?.name,
      supplierId: product.supplierId,
      supplierName: product.supplier?.name,
      price: product.basePrice,
      priceRange: this.getPriceRange(product.basePrice),
      inStock: product.stockLevel > 0,
      ihmRelevant: product.ihmRelevant,
      certifications: product.certifications || [],
      specifications: JSON.stringify(product.specifications),
      popularity: product.orderCount || 0,
      createdAt: product.createdAt.getTime()
    };
  }
}
```

### Index Synchronization

```typescript
// search/sync/product-sync.service.ts
@Injectable()
export class ProductSyncService {
  constructor(
    private readonly meilisearchService: MeilisearchService,
    private readonly productRepository: ProductRepository
  ) {}

  @OnEvent('product.created')
  @OnEvent('product.updated')
  async handleProductChange(event: ProductEvent): Promise<void> {
    const product = await this.productRepository.findById(event.productId);
    if (product) {
      await this.meilisearchService.indexProduct(product);
    }
  }

  @OnEvent('product.deleted')
  async handleProductDeleted(event: ProductEvent): Promise<void> {
    await this.meilisearchService.removeProduct(event.productId);
  }

  @Cron('0 * * * *')  // Every hour
  async fullResync(): Promise<void> {
    const batchSize = 1000;
    let offset = 0;
    let hasMore = true;

    while (hasMore) {
      const products = await this.productRepository.findAll({
        skip: offset,
        take: batchSize
      });

      if (products.length > 0) {
        await this.meilisearchService.indexProducts(products);
        offset += products.length;
      }

      hasMore = products.length === batchSize;
    }

    logger.info(`Full resync completed: ${offset} products indexed`);
  }
}
```

### Search API Controller

```typescript
// search/controllers/search.controller.ts
@Controller('search')
export class SearchController {
  constructor(private readonly meilisearchService: MeilisearchService) {}

  @Get('products')
  async searchProducts(
    @Query('q') query: string,
    @Query('category') categoryId?: string,
    @Query('supplier') supplierId?: string,
    @Query('page') page: number = 1,
    @Query('limit') limit: number = 20,
    @Query('sort') sort?: string
  ): Promise<SearchResult<ProductDocument>> {
    return this.meilisearchService.searchProducts(query, {
      filters: { categoryId, supplierId },
      facets: ['categoryName', 'supplierName', 'certifications', 'priceRange'],
      page,
      hitsPerPage: Math.min(limit, 100),
      sort
    });
  }

  @Get('products/suggest')
  async suggestProducts(
    @Query('q') query: string,
    @Query('limit') limit: number = 5
  ): Promise<ProductSuggestion[]> {
    const result = await this.meilisearchService.searchProducts(query, {
      hitsPerPage: limit
    });

    return result.hits.map(hit => ({
      id: hit.id,
      impaCode: hit.impaCode,
      name: hit.name,
      categoryName: hit.categoryName
    }));
  }
}
```

### Dependencies
- ADR-NF-001: PostgreSQL as Unified Data Store
- ADR-NF-002: Vector Search with pgvector
- ADR-UI-011: Search UX Pattern

### Migration Strategy
1. Deploy Meilisearch instance
2. Configure index settings
3. Initial full sync from PostgreSQL
4. Implement event-driven sync
5. Build search API endpoints
6. Integrate with frontend search UI
7. Set up monitoring and alerting

---

## Synchronization and Index Management

### Sync Strategy

| Event | Sync Method | Latency Target |
|-------|-------------|----------------|
| Product created | Real-time push | <5 seconds |
| Product updated | Real-time push | <5 seconds |
| Product deleted | Real-time push | <5 seconds |
| Bulk import | Batch sync | <5 minutes |
| Initial seed | Full reindex | Scheduled overnight |

```typescript
// Real-time sync via events
@OnEvent('product.created')
@OnEvent('product.updated')
async handleProductChange(event: ProductEvent) {
  await this.meilisearchService.indexDocument('products', {
    id: event.product.id,
    name: event.product.name,
    impaCode: event.product.impaCode,
    description: event.product.description,
    categoryPath: event.product.category.path,
    supplierName: event.product.supplier.name,
    // ... searchable fields
  });
}

@OnEvent('product.deleted')
async handleProductDeleted(event: ProductDeletedEvent) {
  await this.meilisearchService.deleteDocument('products', event.productId);
}
```

### Schema Evolution

| Change Type | Strategy | Downtime |
|-------------|----------|----------|
| Add searchable field | Update settings + reindex | None (background) |
| Add filterable field | Update settings + reindex | None (background) |
| Remove field | Update settings | None |
| Change ranking rules | Update settings | None |
| Major schema change | Create new index, swap | None (blue-green) |

```typescript
// Blue-green index swap for major changes
async reindexWithNewSchema() {
  const newIndex = `products_${Date.now()}`;
  await this.meilisearch.createIndex(newIndex);
  await this.meilisearch.index(newIndex).updateSettings(newSettings);
  await this.fullReindex(newIndex);
  await this.meilisearch.swapIndexes([{ indexes: ['products', newIndex] }]);
  await this.meilisearch.deleteIndex(newIndex); // Old one now has temp name
}
```

### Reindexing Process

- **Scheduled**: Weekly full reindex Sunday 2 AM
- **On-demand**: Via admin API for emergencies
- **Partial**: Category-scoped reindex for targeted updates
- **Monitoring**: Track reindex progress via Meilisearch tasks API

## High Availability and Backup

### HA Architecture (Production)

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
    ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
    │ Meilisearch 1 │ │ Meilisearch 2 │ │ Meilisearch 3 │
    │   (Primary)   │ │   (Replica)   │ │   (Replica)   │
    └───────────────┘ └───────────────┘ └───────────────┘
```

**Note**: Meilisearch Cloud handles replication. Self-hosted requires manual setup or single-node with fast recovery.

### Backup Strategy

| Component | Backup Method | Frequency | Retention |
|-----------|---------------|-----------|-----------|
| Index data | Meilisearch snapshot | Daily | 7 days |
| Settings | Export to S3 | On change | 30 days |
| Source data | PostgreSQL (authoritative) | Per DB backup | Full |

```bash
# Backup script
curl -X POST "http://meilisearch:7700/dumps" -H "Authorization: Bearer $MEILI_MASTER_KEY"
# Copy dump to S3
aws s3 cp /meili/dumps/latest.dump s3://backups/meilisearch/
```

### Recovery Procedures

| Scenario | RTO | Recovery Steps |
|----------|-----|----------------|
| Index corruption | <30 min | Restore from dump or full reindex |
| Node failure | <5 min | Failover to replica (cloud) or reindex (self-hosted) |
| Complete loss | <2 hours | Deploy new instance, full reindex from PostgreSQL |

## Relevance Tuning

### Ranking Rules

```typescript
const rankingRules = [
  'words',        // Exact word matches
  'typo',         // Fewer typos ranked higher
  'proximity',    // Words closer together ranked higher
  'attribute',    // Field priority (name > description)
  'sort',         // User-requested sort
  'exactness'     // Exact matches over partial
];

const searchableAttributes = [
  'name',         // Highest priority
  'impaCode',
  'description',
  'categoryPath',
  'supplierName'  // Lowest priority
];
```

### Relevance Evaluation

| Metric | Measurement | Target |
|--------|-------------|--------|
| **Click-through rate (CTR)** | Clicks / Impressions | >15% |
| **Zero-result rate** | Searches with 0 results | <5% |
| **Mean Reciprocal Rank (MRR)** | 1/rank of first click | >0.5 |
| **Search exit rate** | Sessions ending at search | <20% |

### Tuning Process

1. **Collect analytics**: Track search queries, clicks, conversions
2. **Identify issues**: Zero-result queries, low-CTR queries
3. **Add synonyms**: Map industry terms (e.g., "bolt" = "fastener")
4. **Adjust weights**: Tune searchable attribute order
5. **A/B test**: Compare ranking rule changes
6. **Iterate**: Monthly relevance review

```typescript
// Synonym configuration
await index.updateSettings({
  synonyms: {
    'bolt': ['fastener', 'screw'],
    'ss': ['stainless steel'],
    'ppe': ['personal protective equipment', 'safety gear']
  }
});
```

---

## References
- [Meilisearch Documentation](https://www.meilisearch.com/docs)
- [Meilisearch JavaScript SDK](https://github.com/meilisearch/meilisearch-js)
- [Hybrid Search in Meilisearch](https://www.meilisearch.com/docs/learn/experimental/vector_search)
