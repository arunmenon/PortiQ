# ADR-FN-010: Large Table Processing

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

Maritime requisitions often contain tables with 150+ line items that exceed LLM context windows when processed as a whole, requiring specialized extraction strategies.

### Business Context
A typical ship requisition document contains 150-300 line items across multiple tables. Standard LLM processing of entire tables causes significant accuracy degradation due to attention limitations—studies show document-level extraction can miss 80% of entities in large tables. Reliable extraction of every line item is critical for order accuracy and customer trust.

### Technical Context
- LLM context windows: GPT-4o (128K), Claude 3.5 (200K)
- Even with large windows, attention degrades over long sequences
- LlamaIndex's PER_TABLE_ROW extraction target addresses this issue
- Processing time and cost scale with document size
- Need to maintain row context while processing incrementally

### Assumptions
- Table structures are consistent within a document
- Row-level processing maintains sufficient context
- Batch processing overhead is acceptable
- Column headers provide necessary context for each row

---

## Decision Drivers

- Extraction accuracy for all line items
- Processing reliability at scale
- Cost efficiency (tokens processed)
- Handling of complex table structures
- Maintaining row relationships and context
- Error isolation and recovery

---

## Considered Options

### Option 1: Full Table Processing
**Description:** Send entire tables to LLM for extraction, regardless of size.

**Pros:**
- Simple implementation
- Full context available
- Maintains relationships

**Cons:**
- 80% entity miss rate on large tables
- Context window limits
- High cost for large documents
- All-or-nothing failure mode

### Option 2: Per-Row Extraction (Recommended)
**Description:** Extract each row individually with headers as context, then aggregate results.

**Pros:**
- Consistent accuracy across table sizes
- Isolated failures per row
- Predictable cost scaling
- Parallelizable processing

**Cons:**
- More API calls
- Header must be repeated
- Cross-row context lost

### Option 3: Chunked Table Processing
**Description:** Split tables into chunks of 20-30 rows, process each chunk.

**Pros:**
- Fewer API calls than per-row
- Maintains some cross-row context
- Balanced approach

**Cons:**
- Chunk boundary issues
- Complex chunking logic
- Inconsistent extraction quality

### Option 4: Sliding Window with Overlap
**Description:** Process overlapping windows of rows, merge results.

**Pros:**
- Maintains local context
- Handles relationships near boundaries

**Cons:**
- Duplicate processing overhead
- Complex merge logic
- Higher cost

---

## Decision

**Chosen Option:** Per-Row Extraction with Batched API Calls

We will implement per-row extraction where each table row is processed individually with column headers as context, using batched API calls for efficiency.

### Rationale
Per-row extraction eliminates the accuracy degradation caused by LLM attention limitations on large tables. This approach, documented by LlamaIndex as PER_TABLE_ROW extraction target, prevents the 80% entity miss rate observed in document-level extraction. While it increases API calls, the cost increase is marginal compared to the accuracy improvement, and batching mitigates latency concerns.

---

## Consequences

### Positive
- Consistent accuracy regardless of table size
- Isolated failures don't affect entire table
- Predictable and parallelizable processing
- Better error recovery and retry logic

### Negative
- Increased API call count
- **Mitigation:** Batch rows in single API call where supported
- Loss of cross-row context
- **Mitigation:** Include surrounding rows as optional context

### Risks
- API rate limiting: Implement backoff, queue management
- Increased costs: Monitor closely, optimize prompts
- Header misalignment: Validate header-row mapping

---

## Implementation Notes

### Per-Row Extraction Architecture

```typescript
// extraction/per-row-extractor.ts
interface TableExtractionConfig {
  batchSize: number;          // Rows per API call
  includeContext: boolean;    // Include surrounding rows
  contextRows: number;        // Number of surrounding rows
  parallelBatches: number;    // Concurrent API calls
}

const DEFAULT_CONFIG: TableExtractionConfig = {
  batchSize: 10,
  includeContext: true,
  contextRows: 2,
  parallelBatches: 3
};

class PerRowExtractor {
  constructor(
    private llmProvider: LLMProvider,
    private config: TableExtractionConfig = DEFAULT_CONFIG
  ) {}

  async extractTable(table: ParsedTable): Promise<ExtractedLineItem[]> {
    const { headers, rows } = table;
    const batches = this.createBatches(rows);

    const results: ExtractedLineItem[] = [];

    // Process batches with controlled parallelism
    for (let i = 0; i < batches.length; i += this.config.parallelBatches) {
      const batchPromises = batches
        .slice(i, i + this.config.parallelBatches)
        .map((batch, idx) => this.extractBatch(
          headers,
          batch,
          rows,
          i + idx
        ));

      const batchResults = await Promise.all(batchPromises);
      results.push(...batchResults.flat());
    }

    return results;
  }

  private createBatches(rows: TableRow[]): TableRow[][] {
    const batches: TableRow[][] = [];
    for (let i = 0; i < rows.length; i += this.config.batchSize) {
      batches.push(rows.slice(i, i + this.config.batchSize));
    }
    return batches;
  }

  private async extractBatch(
    headers: string[],
    batch: TableRow[],
    allRows: TableRow[],
    batchIndex: number
  ): Promise<ExtractedLineItem[]> {
    const startIndex = batchIndex * this.config.batchSize;

    // Build context with surrounding rows if enabled
    const context = this.config.includeContext
      ? this.buildContext(allRows, startIndex, batch.length)
      : null;

    const prompt = this.buildPrompt(headers, batch, context);

    try {
      const result = await this.llmProvider.extractLineItems(prompt, LINE_ITEM_SCHEMA);
      return result.map((item, idx) => ({
        ...item,
        rowIndex: startIndex + idx,
        batchIndex
      }));
    } catch (error) {
      // Fallback to single-row processing on batch failure
      return this.extractRowsIndividually(headers, batch, startIndex);
    }
  }

  private buildPrompt(
    headers: string[],
    rows: TableRow[],
    context?: ContextInfo
  ): string {
    let prompt = `Extract line items from the following table rows.\n\n`;
    prompt += `Headers: ${headers.join(' | ')}\n\n`;

    if (context?.before) {
      prompt += `[Previous rows for context]\n${context.before}\n\n`;
    }

    prompt += `[Rows to extract]\n`;
    rows.forEach((row, idx) => {
      prompt += `Row ${idx + 1}: ${row.cells.join(' | ')}\n`;
    });

    if (context?.after) {
      prompt += `\n[Following rows for context]\n${context.after}`;
    }

    return prompt;
  }

  private async extractRowsIndividually(
    headers: string[],
    rows: TableRow[],
    startIndex: number
  ): Promise<ExtractedLineItem[]> {
    const results: ExtractedLineItem[] = [];

    for (let i = 0; i < rows.length; i++) {
      try {
        const prompt = this.buildSingleRowPrompt(headers, rows[i]);
        const [item] = await this.llmProvider.extractLineItems(prompt, LINE_ITEM_SCHEMA);
        results.push({
          ...item,
          rowIndex: startIndex + i,
          extractedIndividually: true
        });
      } catch (error) {
        results.push({
          originalText: rows[i].cells.join(' | '),
          rowIndex: startIndex + i,
          extractionFailed: true,
          error: error.message,
          confidence: 0
        });
      }
    }

    return results;
  }
}
```

### Batch Processing Configuration

```typescript
// config/extraction.config.ts
export const extractionConfig = {
  // Batch sizes by table complexity
  batchSizes: {
    simple: 15,      // Standard product listings
    moderate: 10,    // Mixed content tables
    complex: 5       // Technical specs, nested data
  },

  // Determine complexity from table structure
  getComplexity(table: ParsedTable): 'simple' | 'moderate' | 'complex' {
    const avgCellLength = this.calculateAvgCellLength(table);
    const hasNestedData = this.detectNestedData(table);
    const columnCount = table.columnCount;

    if (hasNestedData || columnCount > 10 || avgCellLength > 100) {
      return 'complex';
    }
    if (columnCount > 6 || avgCellLength > 50) {
      return 'moderate';
    }
    return 'simple';
  },

  // Rate limiting
  rateLimits: {
    maxConcurrentBatches: 5,
    requestsPerMinute: 60,
    tokensPerMinute: 90000
  },

  // Retry configuration
  retry: {
    maxRetries: 3,
    baseDelay: 1000,
    maxDelay: 30000
  }
};
```

### Result Aggregation

```typescript
// extraction/result-aggregator.ts
class ResultAggregator {
  aggregateResults(
    batchResults: ExtractedLineItem[][],
    originalTable: ParsedTable
  ): AggregatedExtractionResult {
    const allItems = batchResults.flat();

    // Sort by original row index
    allItems.sort((a, b) => a.rowIndex - b.rowIndex);

    // Validate completeness
    const expectedRows = originalTable.rowCount;
    const extractedRows = new Set(allItems.map(i => i.rowIndex));
    const missingRows = [];

    for (let i = 0; i < expectedRows; i++) {
      if (!extractedRows.has(i)) {
        missingRows.push(i);
      }
    }

    // Calculate aggregate confidence
    const avgConfidence = allItems.reduce((sum, i) => sum + i.confidence, 0) / allItems.length;
    const failedExtractions = allItems.filter(i => i.extractionFailed);

    return {
      items: allItems,
      totalRows: expectedRows,
      extractedRows: allItems.length,
      missingRows,
      failedExtractions: failedExtractions.length,
      averageConfidence: avgConfidence,
      completeness: allItems.length / expectedRows
    };
  }
}
```

### Monitoring

```typescript
// metrics/extraction-metrics.ts
const extractionMetrics = {
  tablesProcessed: new Counter({
    name: 'table_extraction_total',
    help: 'Tables processed',
    labelNames: ['complexity', 'status']
  }),

  rowsExtracted: new Counter({
    name: 'rows_extracted_total',
    help: 'Table rows extracted',
    labelNames: ['method'] // batch, individual, failed
  }),

  batchSize: new Histogram({
    name: 'extraction_batch_size',
    help: 'Batch sizes used',
    buckets: [1, 5, 10, 15, 20, 30]
  }),

  extractionDuration: new Histogram({
    name: 'table_extraction_duration_seconds',
    help: 'Time to extract entire table',
    labelNames: ['complexity'],
    buckets: [1, 5, 10, 30, 60, 120, 300]
  }),

  completenessRate: new Gauge({
    name: 'extraction_completeness_rate',
    help: 'Ratio of successfully extracted rows'
  })
};
```

### Dependencies
- ADR-FN-006: Document AI Pipeline Architecture
- ADR-FN-007: Document Parsing Service
- ADR-FN-008: LLM Provider for Normalization
- ADR-NF-008: Async Processing (BullMQ)

### Migration Strategy
1. Implement per-row extractor with batching
2. Add complexity detection for adaptive batch sizing
3. Create result aggregation service
4. Implement fallback to individual row extraction
5. Add comprehensive monitoring
6. Test with various table sizes and complexities

---

## Operational Considerations

### Partitioning, Batching, and Resource Limits

#### Partitioning Strategy

| Table Size | Partitioning Method | Batch Size | Max Parallel | Memory Budget |
|------------|---------------------|------------|--------------|---------------|
| < 50 rows | No partitioning | 50 | 1 | 256 MB |
| 50-150 rows | Fixed batches | 15 | 3 | 512 MB |
| 150-300 rows | Adaptive batches | 10-15 | 5 | 1 GB |
| 300-500 rows | Streaming + checkpoints | 10 | 5 | 1 GB |
| > 500 rows | Chunked files + streaming | 10 | 3 | 512 MB per chunk |

```typescript
// Partitioning configuration
interface PartitionConfig {
  tableSizeThreshold: number;
  strategy: 'none' | 'fixed' | 'adaptive' | 'streaming';
  batchSize: number;
  maxParallel: number;
  memoryLimitMB: number;
  checkpointFrequency?: number;  // rows between checkpoints for streaming
}

const PARTITION_CONFIGS: PartitionConfig[] = [
  { tableSizeThreshold: 50, strategy: 'none', batchSize: 50, maxParallel: 1, memoryLimitMB: 256 },
  { tableSizeThreshold: 150, strategy: 'fixed', batchSize: 15, maxParallel: 3, memoryLimitMB: 512 },
  { tableSizeThreshold: 300, strategy: 'adaptive', batchSize: 12, maxParallel: 5, memoryLimitMB: 1024 },
  { tableSizeThreshold: 500, strategy: 'streaming', batchSize: 10, maxParallel: 5, memoryLimitMB: 1024, checkpointFrequency: 50 },
  { tableSizeThreshold: Infinity, strategy: 'streaming', batchSize: 10, maxParallel: 3, memoryLimitMB: 512, checkpointFrequency: 30 }
];

function selectPartitionConfig(rowCount: number): PartitionConfig {
  return PARTITION_CONFIGS.find(c => rowCount <= c.tableSizeThreshold)!;
}
```

#### Adaptive Batching Algorithm

```typescript
// Adaptive batch size based on content complexity
interface BatchSizeFactors {
  avgCellLength: number;      // Characters per cell
  columnCount: number;        // Number of columns
  hasNestedData: boolean;     // Embedded lists, JSON-like content
  hasSpecialChars: boolean;   // Non-ASCII, symbols
  estimatedTokens: number;    // Estimated LLM tokens
}

class AdaptiveBatcher {
  private readonly TOKEN_BUDGET = 4000;  // Leave room for response
  private readonly MIN_BATCH_SIZE = 3;
  private readonly MAX_BATCH_SIZE = 20;

  calculateOptimalBatchSize(table: ParsedTable): number {
    const factors = this.analyzeTable(table);

    // Estimate tokens per row
    const tokensPerRow = this.estimateTokensPerRow(factors);

    // Calculate batch size within token budget
    let batchSize = Math.floor(this.TOKEN_BUDGET / tokensPerRow);

    // Apply complexity adjustments
    if (factors.hasNestedData) batchSize = Math.floor(batchSize * 0.7);
    if (factors.columnCount > 10) batchSize = Math.floor(batchSize * 0.8);

    // Clamp to valid range
    return Math.max(this.MIN_BATCH_SIZE, Math.min(this.MAX_BATCH_SIZE, batchSize));
  }

  private estimateTokensPerRow(factors: BatchSizeFactors): number {
    // Rough estimation: 1 token ~ 4 characters + overhead
    const contentTokens = (factors.avgCellLength * factors.columnCount) / 4;
    const headerOverhead = 50;  // Headers repeated per batch
    const structureOverhead = factors.columnCount * 5;  // Field names, delimiters

    return contentTokens + headerOverhead + structureOverhead;
  }

  private analyzeTable(table: ParsedTable): BatchSizeFactors {
    const allCells = table.rows.flatMap(r => r.cells);
    const avgCellLength = allCells.reduce((sum, c) => sum + c.length, 0) / allCells.length;

    return {
      avgCellLength,
      columnCount: table.columnCount,
      hasNestedData: allCells.some(c => /[\[\{]/.test(c)),
      hasSpecialChars: allCells.some(c => /[^\x00-\x7F]/.test(c)),
      estimatedTokens: Math.ceil((avgCellLength * table.columnCount * table.rowCount) / 4)
    };
  }
}
```

#### Resource Limits and Enforcement

```typescript
// Resource limit enforcement
interface ResourceLimits {
  memory: {
    softLimitMB: number;
    hardLimitMB: number;
    gcThresholdMB: number;
  };
  time: {
    batchTimeoutMs: number;
    totalTimeoutMs: number;
    stallDetectionMs: number;
  };
  api: {
    maxConcurrentRequests: number;
    requestsPerMinute: number;
    tokensPerMinute: number;
  };
}

const RESOURCE_LIMITS: ResourceLimits = {
  memory: {
    softLimitMB: 800,       // Start aggressive GC
    hardLimitMB: 1200,      // Pause processing
    gcThresholdMB: 600      // Trigger manual GC
  },
  time: {
    batchTimeoutMs: 30000,  // 30 seconds per batch
    totalTimeoutMs: 600000, // 10 minutes per table
    stallDetectionMs: 60000 // 1 minute without progress
  },
  api: {
    maxConcurrentRequests: 5,
    requestsPerMinute: 50,
    tokensPerMinute: 80000
  }
};

@Injectable()
export class ResourceEnforcer {
  private memoryUsage = 0;
  private activeRequests = 0;

  async checkAndWait(): Promise<void> {
    // Memory check
    const memUsage = process.memoryUsage().heapUsed / 1024 / 1024;

    if (memUsage > RESOURCE_LIMITS.memory.hardLimitMB) {
      throw new ResourceExhaustedError('memory', memUsage);
    }

    if (memUsage > RESOURCE_LIMITS.memory.softLimitMB) {
      global.gc?.();  // Trigger GC if available
      await this.delay(1000);  // Brief pause
    }

    // Concurrency check
    while (this.activeRequests >= RESOURCE_LIMITS.api.maxConcurrentRequests) {
      await this.delay(100);
    }
  }

  async withResourceTracking<T>(fn: () => Promise<T>): Promise<T> {
    await this.checkAndWait();
    this.activeRequests++;

    try {
      return await fn();
    } finally {
      this.activeRequests--;
    }
  }
}
```

#### Streaming with Checkpoints

```typescript
// Checkpoint-based streaming for very large tables
interface ProcessingCheckpoint {
  documentId: string;
  tableIndex: number;
  lastProcessedRow: number;
  completedBatches: number[];
  intermediateResults: ExtractedLineItem[];
  createdAt: Date;
  expiresAt: Date;
}

@Injectable()
export class CheckpointedProcessor {
  async processLargeTable(
    documentId: string,
    table: ParsedTable
  ): Promise<ExtractedLineItem[]> {
    // Check for existing checkpoint
    let checkpoint = await this.loadCheckpoint(documentId, table.index);
    let startRow = checkpoint?.lastProcessedRow ?? 0;
    let results = checkpoint?.intermediateResults ?? [];

    const config = selectPartitionConfig(table.rowCount);
    const batches = this.createBatches(table.rows.slice(startRow), config.batchSize);

    for (let i = 0; i < batches.length; i++) {
      const batch = batches[i];

      try {
        const batchResults = await this.processBatch(batch, table.headers);
        results.push(...batchResults);

        // Checkpoint every N batches
        if ((i + 1) % config.checkpointFrequency! === 0) {
          await this.saveCheckpoint({
            documentId,
            tableIndex: table.index,
            lastProcessedRow: startRow + (i + 1) * config.batchSize,
            completedBatches: [...(checkpoint?.completedBatches ?? []), i],
            intermediateResults: results,
            createdAt: checkpoint?.createdAt ?? new Date(),
            expiresAt: addHours(new Date(), 24)
          });
        }
      } catch (error) {
        // Save checkpoint on failure for resume
        await this.saveCheckpoint({
          documentId,
          tableIndex: table.index,
          lastProcessedRow: startRow + i * config.batchSize,
          completedBatches: checkpoint?.completedBatches ?? [],
          intermediateResults: results,
          createdAt: checkpoint?.createdAt ?? new Date(),
          expiresAt: addHours(new Date(), 24)
        });
        throw error;
      }
    }

    // Clear checkpoint on completion
    await this.clearCheckpoint(documentId, table.index);
    return results;
  }
}
```

### Backfill and Reprocessing Plan

#### Reprocessing Triggers

| Trigger | Scope | Priority | Approach |
|---------|-------|----------|----------|
| Model/prompt update | All documents since last version | Low | Background batch |
| Bug fix | Affected documents | Medium | Targeted reprocess |
| Schema migration | All documents | Low | Offline migration job |
| Quality issue detected | Flagged documents | High | Immediate requeue |
| Customer request | Specific documents | Medium | On-demand |

#### Backfill Job Configuration

```typescript
// Backfill job definition
interface BackfillJob {
  id: string;
  type: 'full' | 'targeted' | 'incremental';
  filter: BackfillFilter;
  config: BackfillConfig;
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed';
  progress: BackfillProgress;
}

interface BackfillFilter {
  documentIds?: string[];           // Specific documents
  dateRange?: { start: Date; end: Date };
  promptVersionBefore?: string;     // Reprocess old versions
  confidenceBelow?: number;         // Low confidence items
  hasCorrections?: boolean;         // Items that were corrected
  categories?: string[];            // Specific product categories
}

interface BackfillConfig {
  batchSize: number;
  parallelJobs: number;
  throttleRpm: number;              // Requests per minute
  skipIfUnchanged: boolean;         // Skip if result would be same
  preserveManualEdits: boolean;     // Don't overwrite human corrections
  dryRun: boolean;                  // Simulate without updating
}

// Backfill job executor
@Injectable()
export class BackfillExecutor {
  async executeBackfill(job: BackfillJob): Promise<BackfillResult> {
    const documents = await this.getDocumentsForBackfill(job.filter);

    const result: BackfillResult = {
      jobId: job.id,
      totalDocuments: documents.length,
      processed: 0,
      updated: 0,
      skipped: 0,
      errors: [],
      startedAt: new Date(),
      completedAt: null
    };

    for (const batch of this.chunk(documents, job.config.batchSize)) {
      // Throttle to avoid overwhelming system
      await this.throttle(job.config.throttleRpm);

      const batchResults = await Promise.allSettled(
        batch.map(doc => this.reprocessDocument(doc, job.config))
      );

      for (const [idx, batchResult] of batchResults.entries()) {
        result.processed++;

        if (batchResult.status === 'fulfilled') {
          if (batchResult.value.updated) {
            result.updated++;
          } else {
            result.skipped++;
          }
        } else {
          result.errors.push({
            documentId: batch[idx].id,
            error: batchResult.reason.message
          });
        }
      }

      // Update progress
      await this.updateJobProgress(job.id, result);

      // Check for pause/cancel
      const jobStatus = await this.getJobStatus(job.id);
      if (jobStatus === 'paused' || jobStatus === 'cancelled') {
        break;
      }
    }

    result.completedAt = new Date();
    return result;
  }

  private async reprocessDocument(
    doc: Document,
    config: BackfillConfig
  ): Promise<{ updated: boolean; changes: any }> {
    // Load existing extraction
    const existing = await this.extractionRepository.findByDocument(doc.id);

    // Skip if has manual edits and preserveManualEdits is true
    if (config.preserveManualEdits && existing.some(e => e.hasManualEdits)) {
      return { updated: false, changes: null };
    }

    // Re-extract
    const newExtraction = await this.extractionService.extractDocument(doc);

    // Compare results
    const hasChanges = this.detectChanges(existing, newExtraction);

    if (!hasChanges && config.skipIfUnchanged) {
      return { updated: false, changes: null };
    }

    if (!config.dryRun) {
      await this.extractionRepository.replaceExtraction(doc.id, newExtraction);
      await this.auditService.recordReprocessing(doc.id, {
        oldVersion: existing[0]?.promptVersion,
        newVersion: newExtraction[0]?.promptVersion,
        changesDetected: hasChanges
      });
    }

    return { updated: true, changes: this.summarizeChanges(existing, newExtraction) };
  }
}
```

#### Historical Data Correction Workflow

```typescript
// Correction workflow for historical data issues
interface CorrectionCampaign {
  id: string;
  name: string;
  description: string;
  correctionType: 'sku_remapping' | 'unit_standardization' | 'category_update';
  rules: CorrectionRule[];
  affectedDocuments: number;
  status: 'draft' | 'approved' | 'running' | 'completed';
}

interface CorrectionRule {
  condition: {
    field: string;
    operator: 'equals' | 'contains' | 'matches';
    value: string | RegExp;
  };
  action: {
    field: string;
    operation: 'set' | 'replace' | 'append';
    value: any;
  };
}

// Example: Fix unit standardization issue
const unitCorrectionCampaign: CorrectionCampaign = {
  id: 'unit-fix-2024-01',
  name: 'Standardize dozen units',
  description: 'Convert all "doz" and "dzn" to "dozen"',
  correctionType: 'unit_standardization',
  rules: [
    {
      condition: { field: 'unit', operator: 'matches', value: /^doz\.?$/i },
      action: { field: 'unit', operation: 'set', value: 'dozen' }
    },
    {
      condition: { field: 'unit', operator: 'matches', value: /^dzn\.?$/i },
      action: { field: 'unit', operation: 'set', value: 'dozen' }
    }
  ],
  affectedDocuments: 1250,
  status: 'draft'
};
```

### Open Questions

- **Q:** What data sizes and processing SLAs are assumed for MVP versus scale?
  - **A:** Detailed size and SLA specifications:

  **MVP Phase (Months 1-3):**
  | Metric | Target | Maximum | Notes |
  |--------|--------|---------|-------|
  | Documents per day | 50 | 100 | Peak during onboarding |
  | Rows per document (avg) | 150 | 300 | Typical requisition |
  | Total rows per day | 7,500 | 30,000 | Burst handling |
  | Document processing time | < 2 min | 5 min | End-to-end |
  | Table extraction time | < 30 sec | 90 sec | Per table |
  | Queue wait time (P95) | < 5 min | 15 min | Before processing starts |
  | Daily processing window | 8 hours | 16 hours | Business hours focus |

  **Scale Phase (Months 4-12):**
  | Metric | Target | Maximum | Notes |
  |--------|--------|---------|-------|
  | Documents per day | 400 | 800 | 8x MVP |
  | Rows per document (avg) | 150 | 500 | Larger customers |
  | Total rows per day | 60,000 | 200,000 | Peak handling |
  | Document processing time | < 90 sec | 3 min | Optimized pipeline |
  | Table extraction time | < 20 sec | 60 sec | Improved batching |
  | Queue wait time (P95) | < 2 min | 10 min | Better scaling |
  | Daily processing window | 24 hours | 24 hours | Global customers |

  **Infrastructure Scaling:**
  | Scale Level | Worker Pods | Redis Memory | Queue Depth Alert |
  |-------------|-------------|--------------|-------------------|
  | MVP | 2-4 | 1 GB | > 50 |
  | Growth | 4-8 | 2 GB | > 100 |
  | Scale | 8-16 | 4 GB | > 200 |
  | Peak | 16-32 | 8 GB | > 500 |

  **SLA Definitions:**
  ```typescript
  interface ProcessingSLA {
    documentSize: 'small' | 'medium' | 'large' | 'xlarge';
    rowCount: { min: number; max: number };
    processingTime: {
      target: number;   // seconds
      p95: number;
      max: number;
    };
    availability: number;  // percentage
  }

  const PROCESSING_SLAS: ProcessingSLA[] = [
    {
      documentSize: 'small',
      rowCount: { min: 0, max: 50 },
      processingTime: { target: 30, p95: 60, max: 120 },
      availability: 99.5
    },
    {
      documentSize: 'medium',
      rowCount: { min: 51, max: 150 },
      processingTime: { target: 60, p95: 120, max: 180 },
      availability: 99.5
    },
    {
      documentSize: 'large',
      rowCount: { min: 151, max: 300 },
      processingTime: { target: 120, p95: 180, max: 300 },
      availability: 99.0
    },
    {
      documentSize: 'xlarge',
      rowCount: { min: 301, max: Infinity },
      processingTime: { target: 180, p95: 300, max: 600 },
      availability: 98.0
    }
  ];
  ```

---

## References
- [LlamaIndex PER_TABLE_ROW Documentation](https://docs.llamaindex.ai/en/stable/examples/llama_parse/table_row_extraction/)
- [Long Context LLM Limitations](https://arxiv.org/abs/2307.03172)
- [Document AI Best Practices](https://cloud.google.com/document-ai/docs/best-practices)
