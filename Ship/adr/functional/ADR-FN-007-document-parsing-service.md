# ADR-FN-007: Document Parsing Service

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

The document AI pipeline requires a robust parsing service to extract structured data from maritime requisition documents in various formats (PDF, Excel, Word) with complex table layouts.

### Business Context
Maritime requisitions arrive in diverse formats: Excel spreadsheets with merged cells, PDFs generated from various systems, and Word documents with embedded tables. A typical requisition contains 150+ line items across multiple tables with varying column structures. Accurate table extraction is critical—errors propagate through the entire processing pipeline.

### Technical Context
- Need to support PDF, XLSX, DOCX, and potentially image-based documents
- Complex table layouts: merged cells, multi-row headers, nested tables
- Output must be suitable for LLM consumption (structured text/JSON)
- Integration with async processing pipeline (ADR-FN-006)
- Azure Document Intelligence v4.0 released November 2024 with native Office format support

### Assumptions
- Most documents are digitally created (not scanned)
- Table structures vary but follow general requisition patterns
- Processing accuracy is more important than speed
- Azure services are acceptable from compliance perspective

---

## Decision Drivers

- Extraction accuracy for complex table layouts
- Support for multiple document formats natively
- Output quality for downstream LLM processing
- Cost efficiency at projected volumes
- Maintenance and operational simplicity
- Handling of edge cases (handwriting, poor scans)

---

## Considered Options

### Option 1: Azure Document Intelligence v4.0
**Description:** Microsoft's cloud document AI service with native support for PDF, Office formats, and advanced table extraction.

**Pros:**
- Native DOCX, XLSX, PPTX support (no conversion needed)
- Superior table extraction with cell relationship preservation
- Markdown output ideal for LLM consumption
- Handles complex layouts (merged cells, multi-row headers)
- Pre-trained models, no ML expertise required
- $1.50/1K pages pricing

**Cons:**
- Cloud dependency (Azure)
- Potential latency for large documents
- Limited customization options

### Option 2: AWS Textract
**Description:** Amazon's document analysis service with table and form extraction.

**Pros:**
- Native AWS integration
- Good table extraction
- Pay-per-use pricing

**Cons:**
- No native Office format support (requires conversion)
- Less sophisticated table relationship handling
- Output less suitable for LLM consumption

### Option 3: Open Source Stack (Apache Tika + Tabula)
**Description:** Self-hosted combination of Tika for format handling and Tabula for PDF tables.

**Pros:**
- No per-page costs
- Full control over processing
- No cloud dependency

**Cons:**
- Poor handling of complex tables
- No Office format table extraction
- Significant maintenance burden
- Lower accuracy on real-world documents

### Option 4: LlamaParse
**Description:** LlamaIndex's document parsing service optimized for LLM consumption.

**Pros:**
- Designed for LLM pipelines
- Good markdown output
- Handles complex documents

**Cons:**
- Newer service, less proven
- Limited format support compared to Azure
- Higher cost per page

---

## Decision

**Chosen Option:** Azure Document Intelligence v4.0

We will use Azure Document Intelligence v4.0 as the primary document parsing service, leveraging its native Office format support and advanced table extraction capabilities.

### Rationale
Azure Document Intelligence v4.0 (November 2024) represents the most capable document parsing service for our use case. Its native support for DOCX and XLSX eliminates format conversion complexity, while its table extraction handles the complex layouts common in maritime requisitions. The Markdown output format is ideal for LLM consumption in subsequent pipeline stages. At $1.50/1K pages, costs are negligible relative to the value delivered.

---

## Consequences

### Positive
- High accuracy on complex table structures
- Native support for all common requisition formats
- Markdown output optimized for LLM processing
- Minimal preprocessing required
- Proven enterprise-grade reliability

### Negative
- Azure cloud dependency
- **Mitigation:** Abstract behind service interface for future portability
- Per-page costs accumulate at scale
- **Mitigation:** Costs remain low; monitor and optimize batch sizes

### Risks
- Azure service disruption: Implement circuit breaker, queue retry logic
- Format not supported: Fallback to conversion + resubmission
- Accuracy issues on specific formats: Human review queue, feedback loop

---

## Implementation Notes

### Service Architecture

```typescript
// document-parser.service.ts
import { DocumentAnalysisClient, AzureKeyCredential } from '@azure/ai-form-recognizer';

interface ParsedDocument {
  documentId: string;
  format: string;
  pages: number;
  tables: ParsedTable[];
  paragraphs: ParsedParagraph[];
  metadata: DocumentMetadata;
}

interface ParsedTable {
  pageNumber: number;
  rowCount: number;
  columnCount: number;
  headers: string[];
  rows: TableRow[];
  markdown: string;
}

class DocumentParserService {
  private client: DocumentAnalysisClient;

  constructor() {
    this.client = new DocumentAnalysisClient(
      process.env.AZURE_DI_ENDPOINT,
      new AzureKeyCredential(process.env.AZURE_DI_KEY)
    );
  }

  async parseDocument(s3Key: string): Promise<ParsedDocument> {
    const documentStream = await this.getDocumentFromS3(s3Key);

    const poller = await this.client.beginAnalyzeDocument(
      'prebuilt-layout',
      documentStream,
      {
        outputContentFormat: 'markdown'
      }
    );

    const result = await poller.pollUntilDone();
    return this.transformResult(result);
  }

  private transformResult(result: AnalyzeResult): ParsedDocument {
    return {
      documentId: result.modelId,
      format: this.detectFormat(result),
      pages: result.pages?.length ?? 0,
      tables: this.extractTables(result),
      paragraphs: this.extractParagraphs(result),
      metadata: this.extractMetadata(result)
    };
  }

  private extractTables(result: AnalyzeResult): ParsedTable[] {
    return (result.tables ?? []).map(table => ({
      pageNumber: table.boundingRegions?.[0]?.pageNumber ?? 1,
      rowCount: table.rowCount,
      columnCount: table.columnCount,
      headers: this.extractHeaders(table),
      rows: this.extractRows(table),
      markdown: this.tableToMarkdown(table)
    }));
  }

  private tableToMarkdown(table: DocumentTable): string {
    const headers = this.extractHeaders(table);
    const rows = this.extractRows(table);

    let md = '| ' + headers.join(' | ') + ' |\n';
    md += '| ' + headers.map(() => '---').join(' | ') + ' |\n';

    for (const row of rows) {
      md += '| ' + row.cells.join(' | ') + ' |\n';
    }

    return md;
  }
}
```

### Configuration

```typescript
// config/document-intelligence.ts
export const documentIntelligenceConfig = {
  endpoint: process.env.AZURE_DI_ENDPOINT,
  apiKey: process.env.AZURE_DI_KEY,

  // Model selection
  model: 'prebuilt-layout', // Best for tables

  // Processing options
  options: {
    outputContentFormat: 'markdown',
    pages: undefined, // All pages
    locale: 'en-US'
  },

  // Retry configuration
  retry: {
    maxRetries: 3,
    retryDelayMs: 1000,
    maxRetryDelayMs: 30000
  },

  // Supported formats
  supportedFormats: [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/jpeg',
    'image/png',
    'image/tiff'
  ]
};
```

### Error Handling

```typescript
// errors/document-parsing.errors.ts
class DocumentParsingError extends Error {
  constructor(
    message: string,
    public readonly documentId: string,
    public readonly stage: 'upload' | 'analysis' | 'extraction',
    public readonly retryable: boolean
  ) {
    super(message);
  }
}

class UnsupportedFormatError extends DocumentParsingError {
  constructor(documentId: string, format: string) {
    super(
      `Unsupported document format: ${format}`,
      documentId,
      'upload',
      false
    );
  }
}

class AnalysisTimeoutError extends DocumentParsingError {
  constructor(documentId: string) {
    super(
      'Document analysis timed out',
      documentId,
      'analysis',
      true
    );
  }
}
```

### Monitoring

```typescript
// metrics/document-parsing.metrics.ts
const documentParsingMetrics = {
  documentsProcessed: new Counter({
    name: 'document_parsing_total',
    help: 'Total documents processed',
    labelNames: ['format', 'status']
  }),

  processingDuration: new Histogram({
    name: 'document_parsing_duration_seconds',
    help: 'Document parsing duration',
    labelNames: ['format'],
    buckets: [1, 5, 10, 30, 60, 120]
  }),

  tablesExtracted: new Counter({
    name: 'document_tables_extracted_total',
    help: 'Total tables extracted from documents',
    labelNames: ['format']
  }),

  parsingErrors: new Counter({
    name: 'document_parsing_errors_total',
    help: 'Document parsing errors',
    labelNames: ['format', 'error_type']
  })
};
```

### Dependencies
- ADR-FN-006: Document AI Pipeline Architecture
- ADR-FN-008: LLM Provider for Normalization
- ADR-NF-008: Async Processing (BullMQ)
- ADR-NF-013: Object Storage (S3)

### Migration Strategy
1. Set up Azure Document Intelligence resource
2. Implement service wrapper with abstraction layer
3. Create BullMQ worker for parsing queue
4. Add format detection and validation
5. Implement monitoring and alerting
6. Create fallback handling for unsupported formats

---

## Operational Considerations

### Throughput Targets, File Size Limits, and Idempotent Processing

#### Throughput Targets

| Metric | MVP Target | Scale Target | Burst Capacity |
|--------|------------|--------------|----------------|
| Documents per minute | 10 | 50 | 100 (15-min window) |
| Pages per minute | 100 | 500 | 1000 |
| Concurrent parsing jobs | 5 | 20 | 40 |
| Average latency (single doc) | < 30 seconds | < 20 seconds | < 45 seconds (P99) |
| Queue depth (healthy) | < 50 | < 200 | Alert at > 500 |

```typescript
// Throughput monitoring and auto-scaling
const THROUGHPUT_CONFIG = {
  mvp: {
    workerCount: 5,
    maxConcurrent: 5,
    rateLimit: { requests: 10, windowMs: 60000 }
  },
  scale: {
    workerCount: 20,
    maxConcurrent: 20,
    rateLimit: { requests: 50, windowMs: 60000 }
  },
  autoScale: {
    scaleUpThreshold: 0.8,    // 80% worker utilization
    scaleDownThreshold: 0.3,  // 30% worker utilization
    cooldownMinutes: 5
  }
};

// Queue depth monitoring
@Cron('*/30 * * * * *')  // Every 30 seconds
async monitorQueueHealth(): Promise<void> {
  const depth = await this.parsingQueue.count();
  const waitingTime = await this.getOldestJobAge();

  metrics.queueDepth.set({ queue: 'parsing' }, depth);
  metrics.oldestJobAge.set({ queue: 'parsing' }, waitingTime);

  if (depth > 500) {
    await this.alertService.sendWarning('parsing_queue_backlog', { depth, waitingTime });
  }
}
```

#### File Size Limits

| Document Type | Max File Size | Max Pages | Max Tables per Page | Handling for Oversize |
|---------------|---------------|-----------|---------------------|----------------------|
| PDF | 50 MB | 200 pages | 10 | Split into chunks |
| XLSX | 25 MB | 100 sheets | N/A (unlimited rows) | Process sheet by sheet |
| DOCX | 25 MB | 200 pages | 20 | Process section by section |
| Images (PNG/JPG) | 10 MB | 1 | N/A | Resize if > 4000px |
| Scanned PDF | 100 MB | 300 pages | 5 | OCR batch processing |

```typescript
// File validation and chunking
interface FileLimits {
  maxSizeBytes: number;
  maxPages: number;
  maxTablesPerPage: number;
  chunkingStrategy: 'split_pages' | 'split_sheets' | 'reject';
}

const FILE_LIMITS: Record<string, FileLimits> = {
  'application/pdf': {
    maxSizeBytes: 52428800,  // 50 MB
    maxPages: 200,
    maxTablesPerPage: 10,
    chunkingStrategy: 'split_pages'
  },
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': {
    maxSizeBytes: 26214400,  // 25 MB
    maxPages: 100,           // sheets
    maxTablesPerPage: -1,
    chunkingStrategy: 'split_sheets'
  }
};

async validateAndPrepare(file: UploadedFile): Promise<ProcessingPlan> {
  const limits = FILE_LIMITS[file.mimeType];

  if (file.size > limits.maxSizeBytes) {
    throw new FileTooLargeError(file.name, file.size, limits.maxSizeBytes);
  }

  const pageCount = await this.getPageCount(file);

  if (pageCount > limits.maxPages) {
    return {
      strategy: limits.chunkingStrategy,
      chunks: this.createChunks(file, limits.maxPages),
      estimatedTime: this.estimateProcessingTime(pageCount)
    };
  }

  return { strategy: 'single', chunks: [file], estimatedTime: this.estimateProcessingTime(pageCount) };
}
```

#### Idempotent Processing Guarantees

```typescript
// Idempotency implementation
interface ProcessingRecord {
  documentId: string;
  contentHash: string;     // SHA-256 of file content
  processingId: string;    // Unique processing attempt ID
  status: 'processing' | 'completed' | 'failed';
  result?: ParsedDocument;
  createdAt: Date;
  completedAt?: Date;
}

@Injectable()
export class IdempotentParsingService {
  async parseDocument(documentId: string, s3Key: string): Promise<ParsedDocument> {
    // Calculate content hash
    const contentHash = await this.calculateContentHash(s3Key);

    // Check for existing completed processing
    const existing = await this.processingRepository.findByHash(contentHash);

    if (existing?.status === 'completed') {
      metrics.parsingCacheHit.inc();
      return existing.result;
    }

    // Check for in-progress processing (prevent duplicate work)
    if (existing?.status === 'processing') {
      const age = Date.now() - existing.createdAt.getTime();
      if (age < 600000) {  // 10 minutes
        // Wait for existing processing
        return this.waitForResult(existing.processingId);
      }
      // Stale processing, proceed with new attempt
    }

    // Create new processing record with lock
    const processingId = await this.acquireProcessingLock(contentHash);

    try {
      const result = await this.executeParsingWithRetry(s3Key);

      await this.processingRepository.complete(processingId, result);
      return result;
    } catch (error) {
      await this.processingRepository.fail(processingId, error);
      throw error;
    }
  }

  private async acquireProcessingLock(contentHash: string): Promise<string> {
    const processingId = crypto.randomUUID();

    const acquired = await this.redis.set(
      `parsing:lock:${contentHash}`,
      processingId,
      'NX',
      'EX',
      600  // 10 minute lock
    );

    if (!acquired) {
      throw new ProcessingInProgressError(contentHash);
    }

    return processingId;
  }
}
```

### Structured Error Taxonomy

#### Error Categories and Codes

| Category | Code Range | Description | Downstream Action |
|----------|------------|-------------|-------------------|
| **Validation Errors** | 1000-1099 | Input validation failures | Reject with user message |
| **Format Errors** | 1100-1199 | Unsupported or corrupt formats | Convert or reject |
| **Service Errors** | 2000-2099 | Azure DI API errors | Retry with backoff |
| **Resource Errors** | 2100-2199 | Memory, timeout, quota | Queue for retry |
| **Extraction Errors** | 3000-3099 | Content extraction failures | Fallback or review |
| **Quality Errors** | 3100-3199 | Low confidence extraction | Human review |

```typescript
// Error taxonomy implementation
enum ParsingErrorCode {
  // Validation Errors (1000-1099)
  INVALID_FILE_TYPE = 1001,
  FILE_TOO_LARGE = 1002,
  FILE_CORRUPTED = 1003,
  EMPTY_DOCUMENT = 1004,
  PASSWORD_PROTECTED = 1005,
  UNSUPPORTED_ENCODING = 1006,

  // Format Errors (1100-1199)
  FORMAT_CONVERSION_FAILED = 1101,
  MALFORMED_PDF = 1102,
  INVALID_XLSX_STRUCTURE = 1103,
  IMAGE_RESOLUTION_TOO_LOW = 1104,

  // Service Errors (2000-2099)
  AZURE_DI_UNAVAILABLE = 2001,
  AZURE_DI_RATE_LIMITED = 2002,
  AZURE_DI_QUOTA_EXCEEDED = 2003,
  AZURE_DI_TIMEOUT = 2004,
  AZURE_DI_INTERNAL_ERROR = 2005,

  // Resource Errors (2100-2199)
  MEMORY_LIMIT_EXCEEDED = 2101,
  PROCESSING_TIMEOUT = 2102,
  STORAGE_UNAVAILABLE = 2103,
  QUEUE_FULL = 2104,

  // Extraction Errors (3000-3099)
  NO_TABLES_FOUND = 3001,
  TABLE_STRUCTURE_UNCLEAR = 3002,
  HEADER_DETECTION_FAILED = 3003,
  CELL_MERGE_COMPLEX = 3004,
  TEXT_EXTRACTION_PARTIAL = 3005,

  // Quality Errors (3100-3199)
  LOW_CONFIDENCE_OVERALL = 3101,
  OCR_QUALITY_POOR = 3102,
  HANDWRITING_DETECTED = 3103,
  MULTIPLE_LANGUAGES = 3104
}

interface ParsingError {
  code: ParsingErrorCode;
  category: 'validation' | 'format' | 'service' | 'resource' | 'extraction' | 'quality';
  message: string;
  retryable: boolean;
  userMessage?: string;
  technicalDetails?: Record<string, any>;
  suggestedAction: 'reject' | 'retry' | 'fallback' | 'review' | 'alert';
  retryAfterMs?: number;
}

// Error factory with consistent handling
class ParsingErrorFactory {
  static create(code: ParsingErrorCode, details?: Record<string, any>): ParsingError {
    const definitions: Record<ParsingErrorCode, Omit<ParsingError, 'code' | 'technicalDetails'>> = {
      [ParsingErrorCode.FILE_TOO_LARGE]: {
        category: 'validation',
        message: 'File exceeds maximum size limit',
        retryable: false,
        userMessage: 'The uploaded file is too large. Please reduce file size or split into smaller documents.',
        suggestedAction: 'reject'
      },
      [ParsingErrorCode.AZURE_DI_RATE_LIMITED]: {
        category: 'service',
        message: 'Azure Document Intelligence rate limit exceeded',
        retryable: true,
        suggestedAction: 'retry',
        retryAfterMs: 60000
      },
      [ParsingErrorCode.NO_TABLES_FOUND]: {
        category: 'extraction',
        message: 'No tables detected in document',
        retryable: false,
        userMessage: 'We could not find any tables in this document. Please verify this is a requisition document.',
        suggestedAction: 'review'
      },
      [ParsingErrorCode.LOW_CONFIDENCE_OVERALL]: {
        category: 'quality',
        message: 'Extraction confidence below acceptable threshold',
        retryable: false,
        suggestedAction: 'review'
      },
      // ... additional definitions
    };

    return {
      code,
      ...definitions[code],
      technicalDetails: details
    };
  }
}

// Downstream error handling
function handleParsingError(error: ParsingError): HandlingDecision {
  switch (error.suggestedAction) {
    case 'reject':
      return { action: 'FAIL_JOB', notify: 'user', reason: error.userMessage };
    case 'retry':
      return { action: 'REQUEUE', delay: error.retryAfterMs, maxRetries: 3 };
    case 'fallback':
      return { action: 'TRIGGER_FALLBACK', fallbackType: determineFallback(error.code) };
    case 'review':
      return { action: 'ROUTE_TO_REVIEW', priority: getPriority(error.code) };
    case 'alert':
      return { action: 'ALERT_OPS', escalate: true };
  }
}
```

### Open Questions

- **Q:** How will parser output versions be managed to prevent breaking consumers?
  - **A:** Parser output versioning follows semantic versioning with backward compatibility guarantees:

  **Version Schema:**
  ```typescript
  interface ParserOutputSchema {
    schemaVersion: string;        // e.g., "2.1.0"
    backwardCompatibleWith: string[];  // e.g., ["2.0.0", "1.5.0"]
    deprecatedFields: string[];   // Fields to be removed in next major version
  }

  interface ParsedDocumentV2 {
    _meta: {
      schemaVersion: '2.1.0';
      parserId: string;
      parsedAt: Date;
      sourceFormat: string;
    };
    // ... document content
  }
  ```

  **Version Management Policy:**
  | Change Type | Version Bump | Consumer Impact | Notice Period |
  |-------------|--------------|-----------------|---------------|
  | New optional fields | Patch (x.x.1) | None | Changelog |
  | New required fields with defaults | Minor (x.1.0) | None if defaults used | 2 weeks |
  | Field type changes | Major (1.0.0) | Breaking | 3 months |
  | Field removal | Major (1.0.0) | Breaking | 3 months deprecation |
  | Semantic changes | Major (1.0.0) | Potentially breaking | 3 months |

  **Migration Support:**
  ```typescript
  // Schema migration service
  class OutputSchemaMigrator {
    private migrations: Map<string, Migration> = new Map([
      ['1.0.0->2.0.0', {
        transform: (v1: ParsedDocumentV1): ParsedDocumentV2 => ({
          _meta: { schemaVersion: '2.0.0', ...v1.metadata },
          tables: v1.extractedTables.map(t => this.migrateTable(t)),
          // ... transform logic
        })
      }]
    ]);

    migrateToLatest(document: any): ParsedDocumentLatest {
      let current = document;
      let version = document._meta?.schemaVersion || '1.0.0';

      while (version !== LATEST_SCHEMA_VERSION) {
        const migration = this.migrations.get(`${version}->${this.getNextVersion(version)}`);
        current = migration.transform(current);
        version = current._meta.schemaVersion;
      }

      return current;
    }
  }

  // Consumer configuration
  interface ConsumerConfig {
    acceptedVersions: string[];      // e.g., ['2.0.0', '2.1.0']
    autoMigrate: boolean;            // Auto-upgrade older versions
    strictMode: boolean;             // Fail on unknown fields
  }
  ```

  **Deprecation Communication:**
  - Schema changes announced in API changelog and developer newsletter
  - Deprecated fields include `@deprecated` in TypeScript definitions
  - Deprecation warnings logged when deprecated fields accessed
  - Migration guides published 3 months before breaking changes

---

## References
- [Azure Document Intelligence v4.0 Documentation](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/overview)
- [Azure Document Intelligence Pricing](https://azure.microsoft.com/en-us/pricing/details/ai-document-intelligence/)
- [Layout Model Capabilities](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept-layout)
