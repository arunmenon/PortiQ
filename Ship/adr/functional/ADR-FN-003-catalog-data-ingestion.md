# ADR-FN-003: Catalog Data Ingestion Strategy

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

The platform needs to ingest and maintain product catalog data from multiple sources including IMPA MSG (official maritime product database), supplier catalogs, and manual uploads, while ensuring data quality and consistency.

### Business Context
IMPA releases bi-annual updates to the Marine Stores Guide containing 50,000+ product codes. Suppliers maintain their own catalogs that must be mapped to IMPA codes. The platform must support both initial bulk imports and ongoing incremental updates. Data freshness directly impacts buyer trust and order accuracy.

### Technical Context
- IMPA offers two integration paths: MSG Data Licence (CSV/Excel) and MSG API (launched 2022)
- Supplier catalogs arrive in various formats (CSV, Excel, XML, API feeds)
- PostgreSQL database with JSONB for flexible attributes
- BullMQ for async job processing (ADR-NF-008)
- Need to generate vector embeddings for semantic search

### Assumptions
- IMPA MSG API provides reliable, real-time access to product data
- Suppliers will provide catalogs in standard formats with reasonable frequency
- Catalog updates should not disrupt ongoing operations
- Vector embedding generation can be done asynchronously

---

## Decision Drivers

- Data freshness and accuracy requirements
- Integration complexity and maintenance burden
- Cost of different integration approaches
- Support for multiple data sources and formats
- Scalability for growing supplier network
- Minimal disruption during updates

---

## Considered Options

### Option 1: Batch CSV Import Only
**Description:** Use MSG Data Licence CSV files with bi-annual manual imports and scheduled supplier catalog uploads.

**Pros:**
- Simple implementation
- Lower initial cost
- Full control over import timing
- Easy to validate before import

**Cons:**
- Data can be up to 6 months stale
- Manual process prone to errors
- No real-time updates
- Requires dedicated operations time

### Option 2: API-First with Batch Fallback
**Description:** Primary integration via MSG API for IMPA data with batch import as fallback, and configurable API/batch ingestion for suppliers.

**Pros:**
- Near real-time IMPA data access
- Automated updates reduce operational burden
- Flexible supplier integration options
- Resilient with fallback mechanism
- Future-proof as more suppliers offer APIs

**Cons:**
- Higher implementation complexity
- API dependency and potential rate limits
- Higher licensing costs for MSG API

### Option 3: Event-Driven Streaming
**Description:** Real-time streaming ingestion using webhooks and change data capture.

**Pros:**
- Immediate updates
- Event-driven architecture alignment
- Minimal data latency

**Cons:**
- IMPA doesn't offer webhooks
- Most suppliers lack streaming capability
- Over-engineered for actual data change frequency
- Higher infrastructure complexity

---

## Decision

**Chosen Option:** API-First with Batch Fallback

We will implement an API-first ingestion strategy using MSG API for IMPA data, with batch import capability as fallback and for suppliers who don't offer APIs.

### Rationale
The MSG API (launched 2022) provides modern integration capabilities that justify the additional licensing cost through reduced operational burden and improved data freshness. MESPAS's successful integration in February 2025 validates this approach. Batch fallback ensures resilience and supports suppliers with varying technical capabilities.

---

## Consequences

### Positive
- Automated IMPA catalog synchronization
- Reduced operational overhead for data management
- Near real-time product data availability
- Flexible support for diverse supplier capabilities
- Scalable ingestion pipeline

### Negative
- Higher IMPA licensing costs for API access
- **Mitigation:** Factor into platform economics; savings in operations justify cost
- API dependency introduces external service risk
- **Mitigation:** Implement circuit breaker, fallback to batch, maintain local cache

### Risks
- MSG API downtime: Maintain cached catalog, implement batch fallback
- Rate limiting impacts: Implement exponential backoff, optimize sync frequency
- Supplier data quality issues: Validate incoming data, flag for review

---

## Implementation Notes

### Ingestion Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Ingestion Orchestrator                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │  MSG API     │   │  Batch CSV   │   │ Supplier API │        │
│  │  Connector   │   │  Importer    │   │  Connectors  │        │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘        │
│         │                  │                  │                 │
│         └──────────────────┴──────────────────┘                 │
│                            │                                    │
│                   ┌────────▼────────┐                          │
│                   │  Validation &   │                          │
│                   │  Transformation │                          │
│                   └────────┬────────┘                          │
│                            │                                    │
│         ┌──────────────────┼──────────────────┐                │
│         │                  │                  │                 │
│  ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐          │
│  │   Product   │   │   Vector    │   │   Search    │          │
│  │   Database  │   │  Embeddings │   │   Index     │          │
│  └─────────────┘   └─────────────┘   └─────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Job Types (BullMQ)

```typescript
// IMPA sync job - runs daily
interface ImpaSyncJob {
  type: 'impa-sync';
  mode: 'full' | 'incremental';
  lastSyncTimestamp?: Date;
}

// Supplier catalog import
interface SupplierImportJob {
  type: 'supplier-import';
  supplierId: string;
  source: 'api' | 'csv' | 'excel';
  fileUrl?: string;
  apiEndpoint?: string;
}

// Embedding generation
interface EmbeddingJob {
  type: 'generate-embeddings';
  productIds: string[];
  batchSize: number;
}
```

### Validation Rules
1. IMPA code format validation (6 digits)
2. Required field presence check
3. Unit of measure standardization
4. Duplicate detection and merge handling
5. Category mapping validation
6. IHM flag verification against hazmat database

### Dependencies
- ADR-FN-001: IMPA/ISSA Code as Primary Identifier
- ADR-FN-002: Product Master Data Model
- ADR-NF-001: PostgreSQL as Unified Data Store
- ADR-NF-002: Vector Search with pgvector
- ADR-NF-008: Async Processing (BullMQ)

### Migration Strategy
1. Implement batch importer for initial IMPA catalog load
2. Set up MSG API integration and daily sync job
3. Create supplier onboarding ingestion workflow
4. Implement embedding generation pipeline
5. Build admin dashboard for ingestion monitoring

---

## Operational Considerations

### Ingestion Cadence

| Source | Sync Type | Frequency | Window | Rationale |
|--------|-----------|-----------|--------|-----------|
| IMPA MSG API | Incremental | Daily | 02:00-04:00 UTC | Low-traffic window, captures bi-annual major updates |
| IMPA MSG API | Full Sync | Monthly | First Sunday, 01:00 UTC | Catch any missed incremental changes |
| Supplier APIs | Incremental | Every 6 hours | On the hour | Balance freshness vs API load |
| Supplier CSV/Excel | On-demand | Manual trigger | N/A | Uploaded via admin portal |
| Vector Embeddings | Async batch | Continuous | N/A | Queue processes within 5 min of product change |

```typescript
// BullMQ job scheduling configuration
const INGESTION_SCHEDULES = {
  'impa-daily-sync': {
    cron: '0 2 * * *',           // Daily at 02:00 UTC
    jobData: { type: 'impa-sync', mode: 'incremental' }
  },
  'impa-monthly-full': {
    cron: '0 1 1 * *',           // First of month at 01:00 UTC
    jobData: { type: 'impa-sync', mode: 'full' }
  },
  'supplier-incremental': {
    cron: '0 */6 * * *',         // Every 6 hours
    jobData: { type: 'supplier-sync', mode: 'incremental' }
  }
};
```

### Validation Rules

All ingested data passes through a validation pipeline before persistence:

| Rule ID | Category | Validation | Action on Failure |
|---------|----------|------------|-------------------|
| V001 | Format | IMPA code is exactly 6 digits | Reject record |
| V002 | Format | ISSA code matches pattern `[A-Z]{2}[0-9]{4}` if present | Flag for review |
| V003 | Required | Product name is non-empty, <= 255 chars | Reject record |
| V004 | Required | Unit of measure is in approved list | Map to standard or reject |
| V005 | Duplicate | IMPA code does not already exist (for inserts) | Merge/update existing |
| V006 | Duplicate | Fuzzy match on name within category (>90% similarity) | Flag for dedup review |
| V007 | Reference | Category ID exists in categories table | Assign to 'Uncategorized' |
| V008 | Reference | Supplier ID exists (for supplier products) | Reject record |
| V009 | Compliance | IHM-relevant products have hazmat_class populated | Flag for compliance review |
| V010 | Quality | Description length >= 20 chars | Accept with warning |
| V011 | Quality | No HTML/script tags in text fields | Sanitize and accept |
| V012 | Pricing | Price > 0 and currency is valid ISO 4217 | Reject price record |

```typescript
// Validation pipeline implementation
interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
  sanitizedData?: ProductInput;
}

class IngestionValidator {
  private rules: ValidationRule[] = [
    new ImpaCodeFormatRule(),       // V001
    new IssaCodeFormatRule(),       // V002
    new RequiredFieldsRule(),       // V003, V004
    new DuplicateDetectionRule(),   // V005, V006
    new ReferentialIntegrityRule(), // V007, V008
    new ComplianceRule(),           // V009
    new DataQualityRule(),          // V010, V011
    new PricingValidationRule()     // V012
  ];

  async validate(data: ProductInput): Promise<ValidationResult> {
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];
    let sanitizedData = { ...data };

    for (const rule of this.rules) {
      const result = await rule.validate(sanitizedData);
      errors.push(...result.errors);
      warnings.push(...result.warnings);
      if (result.sanitizedData) {
        sanitizedData = result.sanitizedData;
      }
    }

    return {
      valid: errors.filter(e => e.severity === 'BLOCKING').length === 0,
      errors,
      warnings,
      sanitizedData
    };
  }
}
```

### Duplicate Prevention

| Scenario | Detection Method | Resolution |
|----------|------------------|------------|
| Exact IMPA match | Primary key constraint | Update existing record |
| Same supplier SKU | Unique constraint on (product_id, supplier_id, supplier_sku) | Update existing supplier_product |
| Similar name in category | Levenshtein distance < 0.1 | Queue for manual review |
| Potential cross-category duplicate | Vector similarity > 0.95 on embeddings | Queue for manual review |

```sql
-- Duplicate detection query for fuzzy matching
SELECT p1.id, p1.name, p2.id as potential_dup_id, p2.name as potential_dup_name,
       similarity(p1.name, p2.name) as name_similarity
FROM products p1
JOIN products p2 ON p1.category_id = p2.category_id AND p1.id != p2.id
WHERE similarity(p1.name, p2.name) > 0.9
  AND p1.created_at > NOW() - INTERVAL '24 hours';  -- Only check recent ingests
```

### Retry, Backfill, and Rollback Behavior

**Retry Strategy (Exponential Backoff):**

| Attempt | Delay | Max Retries | Failure Action |
|---------|-------|-------------|----------------|
| 1 | Immediate | - | - |
| 2 | 30 seconds | - | - |
| 3 | 2 minutes | - | - |
| 4 | 10 minutes | - | - |
| 5 | 1 hour | - | Move to dead-letter queue |

```typescript
// BullMQ retry configuration
const INGESTION_JOB_OPTIONS: JobsOptions = {
  attempts: 5,
  backoff: {
    type: 'exponential',
    delay: 30000  // 30 seconds base delay
  },
  removeOnComplete: { count: 1000 },
  removeOnFail: false  // Keep failed jobs for analysis
};

// Dead letter queue handling
@Processor('ingestion-dlq')
class IngestionDLQProcessor {
  @Process()
  async handleFailedJob(job: Job) {
    await this.alertService.notify({
      channel: 'ops-alerts',
      severity: 'HIGH',
      message: `Ingestion job failed after retries: ${job.name}`,
      data: { jobId: job.id, error: job.failedReason }
    });

    // Log for manual intervention
    await this.auditLog.record({
      type: 'INGESTION_FAILURE',
      jobId: job.id,
      data: job.data,
      error: job.failedReason
    });
  }
}
```

**Backfill Operations:**

| Trigger | Scope | Process |
|---------|-------|---------|
| New category added | All products missing category assignment | Batch re-categorization job |
| Schema change | All affected records | Migration job with checkpoint |
| Data quality fix | Records matching criteria | Targeted update job |
| Embedding model update | All products | Full re-embedding with progress tracking |

```typescript
// Backfill job with checkpointing
interface BackfillJob {
  type: 'backfill';
  scope: 'full' | 'incremental';
  filter?: Record<string, any>;
  checkpoint?: {
    lastProcessedId: string;
    processedCount: number;
  };
  batchSize: number;
}

async function runBackfill(job: BackfillJob): Promise<void> {
  const batchSize = job.batchSize || 1000;
  let lastId = job.checkpoint?.lastProcessedId || '00000000-0000-0000-0000-000000000000';
  let processed = job.checkpoint?.processedCount || 0;

  while (true) {
    const batch = await this.productRepo.findBatch({
      afterId: lastId,
      limit: batchSize,
      filter: job.filter
    });

    if (batch.length === 0) break;

    await this.processBatch(batch);
    lastId = batch[batch.length - 1].id;
    processed += batch.length;

    // Save checkpoint for resumability
    await this.checkpointService.save(job.id, { lastProcessedId: lastId, processedCount: processed });
  }
}
```

**Rollback Procedures:**

| Scenario | Rollback Method | Recovery Time |
|----------|-----------------|---------------|
| Bad batch import | Soft delete by `ingestion_batch_id` | < 5 minutes |
| Corrupted sync | Restore from audit log | 15-30 minutes |
| Full catalog corruption | Point-in-time database restore | 1-2 hours |

```sql
-- Every ingested record tagged with batch ID for rollback
ALTER TABLE products ADD COLUMN ingestion_batch_id UUID;
ALTER TABLE supplier_products ADD COLUMN ingestion_batch_id UUID;

-- Soft delete rollback
UPDATE products
SET deleted_at = NOW(), deletion_reason = 'BATCH_ROLLBACK'
WHERE ingestion_batch_id = :batch_id;

-- Hard rollback via audit log reconstruction
CREATE OR REPLACE FUNCTION rollback_to_timestamp(target_time TIMESTAMPTZ)
RETURNS void AS $$
BEGIN
    -- Reconstruct state from audit log
    -- This is a simplified example; production would use proper event sourcing
    INSERT INTO products (SELECT ... FROM product_audit_log WHERE created_at <= target_time);
END;
$$ LANGUAGE plpgsql;
```

### Schema Drift and Data Quality Monitoring

| Metric | Threshold | Alert | Dashboard |
|--------|-----------|-------|-----------|
| Validation failure rate | > 5% of batch | Slack + PagerDuty | Real-time |
| New unknown fields in source | Any | Slack notification | Daily summary |
| Duplicate detection rate | > 2% of batch | Slack warning | Real-time |
| Missing required fields | > 1% of batch | Slack + email | Real-time |
| Category assignment failures | > 10% | Slack warning | Daily summary |
| Embedding generation lag | > 1 hour | PagerDuty | Real-time |
| Source API error rate | > 10% over 1 hour | PagerDuty | Real-time |

```typescript
// Data quality metrics collection
class IngestionMetrics {
  private readonly metrics = new PrometheusMetrics();

  recordValidation(result: ValidationResult, source: string): void {
    this.metrics.counter('ingestion_records_total', { source, status: result.valid ? 'valid' : 'invalid' }).inc();

    for (const error of result.errors) {
      this.metrics.counter('ingestion_validation_errors', { source, rule: error.ruleId }).inc();
    }
  }

  recordBatchCompletion(source: string, duration: number, recordCount: number): void {
    this.metrics.histogram('ingestion_batch_duration_seconds', { source }).observe(duration);
    this.metrics.counter('ingestion_records_processed', { source }).inc(recordCount);
  }
}

// Schema drift detection
async function detectSchemaDrift(source: string, data: any[]): Promise<SchemaDriftReport> {
  const expectedFields = await this.schemaRegistry.getExpectedFields(source);
  const observedFields = new Set(data.flatMap(d => Object.keys(d)));

  const newFields = [...observedFields].filter(f => !expectedFields.has(f));
  const missingFields = [...expectedFields].filter(f => !observedFields.has(f));

  if (newFields.length > 0 || missingFields.length > 0) {
    await this.alertService.notify({
      channel: 'data-engineering',
      message: `Schema drift detected in ${source}`,
      data: { newFields, missingFields }
    });
  }

  return { newFields, missingFields };
}
```

### Open Questions (Resolved)

- **Q:** What monitoring will detect schema drift or data quality regressions?
  - **A:** A comprehensive monitoring system is implemented with three components:
    1. **Real-time validation metrics**: Every record passes through the validation pipeline with rule-level error tracking exposed via Prometheus metrics and visualized in Grafana dashboards.
    2. **Schema drift detection**: Before processing each batch, observed fields are compared against the schema registry. New or missing fields trigger immediate Slack notifications to the data engineering team.
    3. **Quality trend analysis**: Daily aggregated reports track validation failure rates, duplicate detection rates, and category assignment success rates. Anomaly detection alerts on deviations > 2 standard deviations from the 30-day moving average.

    Alerts route to Slack for warnings and PagerDuty for critical issues (> 5% failure rate or source API unavailability).

---

## References
- [IMPA MSG API Documentation](https://www.impa.net/msg-api/)
- [MESPAS MSG API Integration Case Study](https://mespas.com)
- [BullMQ Documentation](https://docs.bullmq.io)
