# ADR-FN-006: Document AI Pipeline Architecture

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

The platform must automatically process maritime requisition documents (Excel, PDF, Word) containing 150+ line items, extracting product information and matching it to the IMPA catalog to enable digital ordering.

### Business Context
Maritime procurement remains paper-intensive, with chandlers manually processing requisitions via phone calls and Excel sheets. A typical requisition contains 150+ line items in various formats. Manual processing is error-prone, slow, and expensive. Document AI can reduce manual effort by 60-90% while maintaining accuracy for edge cases. Estimated cost for 5,000 pages monthly is $75-100—less than one hour of manual data entry labor.

### Technical Context
- Azure Document Intelligence v4.0 (Nov 2024) natively supports DOCX, XLSX, PPTX, PDF
- LLMs (GPT-4o, Claude 3.5) achieve 97-98% accuracy on invoice extraction
- pgvector enables semantic similarity matching between extracted items and catalog
- BullMQ provides queue-based async processing (ADR-NF-008)
- S3 for document storage (ADR-NF-013)

### Assumptions
- Documents will be in English or have translatable content
- Most line items reference standard IMPA products
- Processing latency of minutes (not seconds) is acceptable
- Human review capacity exists for low-confidence extractions

---

## Decision Drivers

- Processing accuracy for complex maritime requisitions
- Support for multiple document formats
- Scalability for concurrent document processing
- Cost efficiency at projected volumes
- Human-in-loop capability for quality assurance
- Integration with product catalog matching

---

## Considered Options

### Option 1: Single-Service Processing
**Description:** Send documents directly to LLM (e.g., GPT-4 Vision) for end-to-end extraction.

**Pros:**
- Simple architecture
- Single API integration
- Handles layout understanding

**Cons:**
- Poor accuracy on complex tables
- High cost per document
- No specialized table extraction
- Limited format support

### Option 2: Queue-Based Multi-Stage Pipeline
**Description:** Asynchronous pipeline: Upload → Storage → Document AI → LLM Normalization → SKU Matching → Human Review.

**Pros:**
- Best-of-breed components for each stage
- Scalable worker pool
- Retry and failure handling
- Visibility into pipeline stages
- Cost-optimized per stage

**Cons:**
- More complex architecture
- Multiple service dependencies
- Longer end-to-end latency

### Option 3: Real-Time Streaming
**Description:** Synchronous processing with real-time feedback to user.

**Pros:**
- Immediate results
- Interactive correction

**Cons:**
- Blocks user during processing
- No batching efficiency
- Poor UX for large documents
- Complex error handling

---

## Decision

**Chosen Option:** Queue-Based Multi-Stage Pipeline

We will implement an asynchronous, queue-based document processing pipeline with distinct stages for document parsing, LLM extraction, SKU matching, and human review.

### Rationale
The queue-based architecture provides optimal accuracy by using specialized components for each stage (Azure Document Intelligence for table extraction, LLM for normalization, pgvector for semantic matching). Async processing enables efficient batching, retry handling, and scalability while providing transparency into processing status. This mirrors the proven architecture described in the technical blueprint.

---

## Consequences

### Positive
- Highest accuracy through specialized components
- Scalable worker pool for concurrent processing
- Clear visibility into processing stages
- Resilient with automatic retries
- Cost-efficient through batching

### Negative
- Multiple service dependencies
- **Mitigation:** Circuit breakers, fallback mechanisms
- Latency measured in minutes not seconds
- **Mitigation:** Status updates, webhook notifications

### Risks
- Azure Document Intelligence service disruption: Implement fallback to alternative parser
- LLM API rate limits: Implement backoff, queue management
- Cost overrun on high volume: Monitor usage, implement budgets

---

## Implementation Notes

### Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Document AI Pipeline                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────┐    ┌───────────┐    ┌─────────────────────────────────┐  │
│   │  Upload  │───▶│    S3     │───▶│         BullMQ Queues           │  │
│   │   API    │    │  Storage  │    │                                 │  │
│   └──────────┘    └───────────┘    │  ┌─────────┐    ┌───────────┐  │  │
│                                     │  │ parsing │───▶│ normalize │  │  │
│                                     │  └─────────┘    └───────────┘  │  │
│                                     │                       │        │  │
│                                     │  ┌─────────┐    ┌─────▼─────┐  │  │
│                                     │  │ review  │◀───│  matching │  │  │
│                                     │  └─────────┘    └───────────┘  │  │
│                                     └─────────────────────────────────┘  │
│                                                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                        Worker Pool                               │   │
│   │                                                                  │   │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │   │
│   │  │   Document   │  │     LLM      │  │    SKU Matching      │  │   │
│   │  │ Intelligence │  │  Extraction  │  │  (pgvector + LLM)    │  │   │
│   │  │   Worker     │  │   Worker     │  │      Worker          │  │   │
│   │  └──────────────┘  └──────────────┘  └──────────────────────┘  │   │
│   │                                                                  │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Queue Configuration

```typescript
// queue-config.ts
export const DOCUMENT_QUEUES = {
  PARSING: 'document-parsing',
  NORMALIZATION: 'line-item-normalization',
  MATCHING: 'sku-matching',
  REVIEW: 'human-review'
};

export const queueOptions = {
  [DOCUMENT_QUEUES.PARSING]: {
    concurrency: 5,
    attempts: 3,
    backoff: { type: 'exponential', delay: 5000 }
  },
  [DOCUMENT_QUEUES.NORMALIZATION]: {
    concurrency: 10,
    attempts: 3,
    backoff: { type: 'exponential', delay: 2000 }
  },
  [DOCUMENT_QUEUES.MATCHING]: {
    concurrency: 20,
    attempts: 3,
    backoff: { type: 'fixed', delay: 1000 }
  }
};
```

### Processing Stages

```typescript
// Stage 1: Document Parsing
interface ParsingJob {
  documentId: string;
  s3Key: string;
  format: 'pdf' | 'xlsx' | 'docx';
}

interface ParsingResult {
  documentId: string;
  tables: ExtractedTable[];
  metadata: DocumentMetadata;
}

// Stage 2: LLM Normalization
interface NormalizationJob {
  documentId: string;
  lineItems: RawLineItem[];
  batchIndex: number;
}

interface NormalizedLineItem {
  originalText: string;
  productName: string;
  quantity: number;
  unit: string;
  specifications: Record<string, any>;
  confidence: number;
}

// Stage 3: SKU Matching
interface MatchingJob {
  documentId: string;
  lineItem: NormalizedLineItem;
  lineIndex: number;
}

interface MatchResult {
  lineIndex: number;
  matches: {
    impaCode: string;
    productName: string;
    similarity: number;
    confidence: number;
  }[];
  requiresReview: boolean;
}
```

### Confidence-Based Routing

```typescript
const CONFIDENCE_THRESHOLDS = {
  AUTO_APPROVE: 0.95,
  QUICK_REVIEW: 0.80,
  FULL_REVIEW: 0.0
};

function routeByConfidence(result: MatchResult): ReviewAction {
  const confidence = result.matches[0]?.confidence ?? 0;

  if (confidence >= CONFIDENCE_THRESHOLDS.AUTO_APPROVE) {
    return { action: 'auto-approve', queue: null };
  } else if (confidence >= CONFIDENCE_THRESHOLDS.QUICK_REVIEW) {
    return { action: 'quick-review', queue: 'review-quick' };
  } else {
    return { action: 'full-review', queue: 'review-manual' };
  }
}
```

### Cost Estimation

| Component | Unit Cost | Monthly (5K pages) |
|-----------|-----------|-------------------|
| Azure Document Intelligence | $1.50/1K pages | $7.50 |
| LLM API (GPT-4o) | ~$0.01/page | $50 |
| pgvector queries | Negligible | $0 |
| **Total** | | **~$60-100** |

### Dependencies
- ADR-FN-007: Document Parsing Service
- ADR-FN-008: LLM Provider for Normalization
- ADR-FN-009: Confidence-Gated Human-in-Loop
- ADR-NF-002: Vector Search with pgvector
- ADR-NF-008: Async Processing (BullMQ)
- ADR-NF-013: Object Storage (S3)

### Migration Strategy
1. Set up S3 bucket for document storage
2. Implement BullMQ queues and workers
3. Integrate Azure Document Intelligence
4. Build LLM extraction service
5. Implement SKU matching with pgvector
6. Create review UI for human-in-loop
7. Add monitoring and alerting

---

## Operational Considerations

### Accuracy Targets, Human Review SLAs, and PII Handling

#### Accuracy Targets by Pipeline Stage

| Stage | Metric | Target | Acceptable | Critical Threshold |
|-------|--------|--------|------------|-------------------|
| **Document Parsing** | Table detection rate | >= 98% | >= 95% | < 90% triggers alert |
| **Document Parsing** | Cell extraction accuracy | >= 95% | >= 92% | < 88% triggers fallback |
| **LLM Normalization** | Field extraction accuracy | >= 97% | >= 94% | < 90% triggers review |
| **LLM Normalization** | Unit standardization | >= 99% | >= 97% | < 95% |
| **SKU Matching** | Correct IMPA match (top-1) | >= 85% | >= 80% | < 75% |
| **SKU Matching** | Correct in top-3 | >= 95% | >= 92% | < 88% |
| **End-to-End** | Auto-approved accuracy | >= 99% | >= 98% | < 97% stops auto-approve |
| **End-to-End** | Overall accuracy (with review) | >= 99.5% | >= 99% | < 98.5% |

#### Human Review SLAs

| Review Type | Queue Priority | Target SLA | Escalation Trigger | Staffing Requirement |
|-------------|----------------|------------|-------------------|---------------------|
| **Quick Review** (80-94% confidence) | Normal | 4 hours | > 8 hours in queue | 1 FTE per 200 items/day |
| **Full Review** (< 80% confidence) | Normal | 8 hours | > 16 hours in queue | 1 FTE per 80 items/day |
| **Urgent Documents** (flagged) | High | 1 hour | > 2 hours | Dedicated reviewer on-call |
| **Escalated Items** | Critical | 30 minutes | > 1 hour | Senior staff / manager |

```typescript
// Queue SLA monitoring
interface ReviewSLAConfig {
  quickReview: {
    targetMinutes: 240,      // 4 hours
    warningMinutes: 360,     // 6 hours - yellow alert
    criticalMinutes: 480,    // 8 hours - red alert + escalation
    autoEscalateAfter: 600   // 10 hours - route to senior
  },
  fullReview: {
    targetMinutes: 480,      // 8 hours
    warningMinutes: 720,     // 12 hours
    criticalMinutes: 960,    // 16 hours
    autoEscalateAfter: 1200  // 20 hours
  },
  urgent: {
    targetMinutes: 60,
    warningMinutes: 90,
    criticalMinutes: 120,
    autoEscalateAfter: 150
  }
}

// SLA breach alerting
@Cron('*/5 * * * *')
async checkSLABreaches(): Promise<void> {
  const breaches = await this.reviewQueueRepository.findSLABreaches();

  for (const item of breaches) {
    if (item.ageMinutes > item.config.criticalMinutes) {
      await this.alertService.sendCritical('review_sla_breach', {
        itemId: item.id,
        documentId: item.documentId,
        ageHours: (item.ageMinutes / 60).toFixed(1),
        tier: item.tier
      });
      await this.escalateToSenior(item);
    }
  }
}
```

#### Data Privacy and PII Handling

| Pipeline Stage | PII Risk | Handling Approach | Retention |
|----------------|----------|-------------------|-----------|
| **Document Upload** | High (may contain crew names, contact info) | Store in encrypted S3, access logging | 90 days post-processing |
| **Document Parsing** | Medium (extracted text) | Process in memory, no persistent PII storage | Transient only |
| **LLM Processing** | Medium (sent to external API) | Redact before sending, use enterprise agreements | No retention at provider |
| **SKU Matching** | Low (product data only) | No PII in matching stage | N/A |
| **Review Interface** | Medium (reviewers see original) | Role-based access, audit logging | Session-based |
| **Extracted Data** | Low (normalized products) | No PII in final output | Per data retention policy |

```typescript
// PII redaction before LLM processing
interface PIIRedactionConfig {
  patterns: {
    email: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
    phone: /(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g,
    name: /(?:Capt\.|Captain|Chief|Mr\.|Mrs\.|Ms\.)\s+[A-Z][a-z]+\s+[A-Z][a-z]+/g,
    imoNumber: /IMO\s*\d{7}/gi  // Keep but anonymize
  },
  replacements: {
    email: '[EMAIL_REDACTED]',
    phone: '[PHONE_REDACTED]',
    name: '[NAME_REDACTED]',
    imoNumber: 'IMO XXXXXXX'
  }
}

async function redactPIIBeforeLLM(text: string): Promise<{ redacted: string; mapping: Map<string, string> }> {
  const mapping = new Map<string, string>();
  let redacted = text;

  for (const [type, pattern] of Object.entries(PIIRedactionConfig.patterns)) {
    const matches = text.matchAll(pattern);
    for (const match of matches) {
      const placeholder = `[${type.toUpperCase()}_${mapping.size}]`;
      mapping.set(placeholder, match[0]);
      redacted = redacted.replace(match[0], placeholder);
    }
  }

  return { redacted, mapping };
}
```

### Fallback Path for Low-Confidence Extraction

#### Fallback Decision Matrix

| Confidence Score | Primary Action | Fallback Action | Ultimate Fallback |
|------------------|----------------|-----------------|-------------------|
| >= 95% | Auto-approve | N/A | N/A |
| 80-94% | Quick review queue | Extended review if unresolved | Manual entry |
| 60-79% | Full review queue | Re-process with alternative model | Manual entry |
| 40-59% | Alternative extraction | Human transcription | Manual entry |
| < 40% | Human transcription | Skip item, flag for attention | Manual entry |

#### Fallback Pipeline Implementation

```typescript
// Fallback orchestrator
interface FallbackStrategy {
  stage: 'parsing' | 'normalization' | 'matching';
  trigger: ConfidenceThreshold;
  actions: FallbackAction[];
}

const FALLBACK_STRATEGIES: FallbackStrategy[] = [
  {
    stage: 'parsing',
    trigger: { below: 0.60 },
    actions: [
      { type: 'RETRY_WITH_ENHANCED', params: { model: 'prebuilt-document', dpi: 300 } },
      { type: 'FALLBACK_OCR', params: { provider: 'google-vision' } },
      { type: 'HUMAN_TRANSCRIPTION', params: { priority: 'high' } }
    ]
  },
  {
    stage: 'normalization',
    trigger: { below: 0.70 },
    actions: [
      { type: 'RETRY_WITH_DIFFERENT_PROMPT', params: { promptVersion: 'detailed' } },
      { type: 'FALLBACK_PROVIDER', params: { provider: 'anthropic' } },
      { type: 'MANUAL_NORMALIZATION', params: { includeOriginal: true } }
    ]
  },
  {
    stage: 'matching',
    trigger: { below: 0.75 },
    actions: [
      { type: 'EXPAND_SEARCH', params: { includeAliases: true, fuzzyThreshold: 0.6 } },
      { type: 'LLM_ASSISTED_MATCH', params: { includeContext: true } },
      { type: 'MANUAL_SKU_SELECTION', params: { showTop10: true } }
    ]
  }
];

class FallbackOrchestrator {
  async executeFallback(
    stage: string,
    item: ProcessingItem,
    currentConfidence: number
  ): Promise<FallbackResult> {
    const strategy = FALLBACK_STRATEGIES.find(s => s.stage === stage);

    for (const action of strategy.actions) {
      try {
        const result = await this.executeAction(action, item);

        if (result.confidence >= strategy.trigger.below + 0.15) {
          return { success: true, result, action: action.type };
        }
      } catch (error) {
        logger.warn(`Fallback action ${action.type} failed`, { error, itemId: item.id });
        continue;
      }
    }

    // All fallbacks exhausted - route to manual processing
    return {
      success: false,
      result: null,
      action: 'MANUAL_REQUIRED',
      metadata: { originalConfidence: currentConfidence, attemptsExhausted: strategy.actions.length }
    };
  }
}
```

#### Workflow Stall Prevention

```typescript
// Stall detection and resolution
@Injectable()
export class WorkflowStallMonitor {
  private readonly STALL_THRESHOLDS = {
    parsing: 300,      // 5 minutes
    normalization: 180, // 3 minutes
    matching: 120,      // 2 minutes
    review: 86400       // 24 hours (human dependent)
  };

  @Cron('*/2 * * * *')  // Every 2 minutes
  async detectAndResolveStalls(): Promise<void> {
    const stalledItems = await this.findStalledItems();

    for (const item of stalledItems) {
      const resolution = this.determineResolution(item);

      switch (resolution) {
        case 'RETRY':
          await this.retryProcessing(item);
          break;
        case 'FALLBACK':
          await this.triggerFallback(item);
          break;
        case 'SKIP_AND_FLAG':
          await this.skipWithFlag(item);
          break;
        case 'ALERT':
          await this.alertOperations(item);
          break;
      }
    }
  }

  private determineResolution(item: StalledItem): Resolution {
    if (item.retryCount < 3) return 'RETRY';
    if (item.fallbackAttempts < 2) return 'FALLBACK';
    if (item.stage !== 'review') return 'SKIP_AND_FLAG';
    return 'ALERT';
  }
}
```

### Open Questions

- **Q:** How will model drift be detected and retraining scheduled?
  - **A:** Model drift detection and response follows this framework:

  **Drift Detection Metrics:**
  | Metric | Calculation | Drift Threshold | Check Frequency |
  |--------|-------------|-----------------|-----------------|
  | Confidence score distribution | Rolling 7-day mean vs baseline | > 5% shift | Daily |
  | Auto-approval rate | % items >= 95% confidence | > 10% decrease | Daily |
  | Review correction rate | % of reviewed items with changes | > 15% increase | Weekly |
  | SKU match accuracy | Sampled human validation | > 3% decrease | Weekly |
  | Processing time | P95 latency per stage | > 25% increase | Daily |

  **Detection Implementation:**
  ```typescript
  interface DriftMetrics {
    confidenceMean: number;
    confidenceStdDev: number;
    autoApprovalRate: number;
    reviewCorrectionRate: number;
    matchAccuracy: number;
  }

  @Cron('0 6 * * *')  // Daily at 6 AM
  async detectModelDrift(): Promise<DriftReport> {
    const current = await this.calculateMetrics(7);  // Last 7 days
    const baseline = await this.getBaseline();       // Established baseline

    const drifts: DriftIndicator[] = [];

    if (Math.abs(current.confidenceMean - baseline.confidenceMean) > 0.05) {
      drifts.push({
        metric: 'confidence_mean',
        baseline: baseline.confidenceMean,
        current: current.confidenceMean,
        severity: 'warning'
      });
    }

    if (current.reviewCorrectionRate > baseline.reviewCorrectionRate * 1.15) {
      drifts.push({
        metric: 'review_correction_rate',
        baseline: baseline.reviewCorrectionRate,
        current: current.reviewCorrectionRate,
        severity: 'critical'
      });
    }

    return { drifts, recommendation: this.getRecommendation(drifts) };
  }
  ```

  **Response Actions:**
  | Drift Severity | Automatic Response | Human Response |
  |----------------|-------------------|----------------|
  | Minor (< 5% shift) | Log and monitor | Review in weekly meeting |
  | Warning (5-10% shift) | Alert data team, increase sampling | Investigate root cause |
  | Critical (> 10% shift) | Lower auto-approval threshold, alert | Emergency review, consider rollback |

  **Retraining Schedule:**
  - **Prompt tuning**: Monthly review of extraction prompts based on correction patterns
  - **Few-shot examples**: Update quarterly with recent edge cases from review queue
  - **Full evaluation**: Quarterly benchmark against held-out test set
  - **Emergency update**: Within 48 hours if critical drift detected

  **Feedback Loop:**
  ```typescript
  // Collect corrections for prompt improvement
  async recordCorrectionForTraining(correction: ReviewCorrection): Promise<void> {
    await this.trainingDataRepository.insert({
      originalExtraction: correction.originalData,
      correctedExtraction: correction.correctedData,
      correctionType: correction.type,  // 'field_value', 'sku_match', 'quantity'
      documentType: correction.documentMetadata.type,
      createdAt: new Date()
    });

    // Trigger prompt review if pattern emerges
    const recentSimilar = await this.countSimilarCorrections(correction.type, 7);
    if (recentSimilar > 20) {
      await this.alertService.notify('prompt_review_needed', {
        correctionType: correction.type,
        count: recentSimilar
      });
    }
  }
  ```

---

## PortiQ Upload UX Integration

The PortiQ conversation-first interface integrates document upload as a seamless part of the AI-assisted requisition workflow. This section defines the UX components and interaction patterns.

### Document Drop Zone States

The DocumentDropZone component provides visual feedback throughout the upload and processing lifecycle:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Document Drop Zone States                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  DEFAULT                        DRAGOVER                        │
│  ┌─────────────────────┐       ┌─────────────────────┐         │
│  │    ╭─────╮          │       │    ╭─────╮          │         │
│  │    │  ☁  │          │       │    │  ☁  │ ← bounce │         │
│  │    ╰─────╯          │       │    ╰─────╯          │         │
│  │                     │       │                     │         │
│  │  Drop requisition   │       │   Drop to upload    │         │
│  │  documents here or  │       │                     │         │
│  │  [browse]           │       │  (scale: 1.02)      │         │
│  │                     │       │  border: primary    │         │
│  │  PDF, Excel, images │       │                     │         │
│  └─────────────────────┘       └─────────────────────┘         │
│  border: dashed gray           border: solid primary            │
│                                                                  │
│  UPLOADING                      PROCESSING                      │
│  ┌─────────────────────┐       ┌─────────────────────┐         │
│  │       ╭───╮         │       │      ╭─◯─╮         │         │
│  │       │67%│         │       │     ◯╭───╮◯        │         │
│  │       ╰───╯         │       │      ╰─◯─╯         │         │
│  │                     │       │                     │         │
│  │   Uploading...      │       │  PortiQ is         │         │
│  │   invoice.pdf       │       │  analyzing your    │         │
│  │                     │       │  document...       │         │
│  │   [Cancel]          │       │                     │         │
│  └─────────────────────┘       └─────────────────────┘         │
│  border: primary/50            border: secondary                │
│  progress ring animation       scanning animation               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Upload Component Implementation

```tsx
// components/upload/DocumentDropZone.tsx
interface DocumentDropZoneProps {
  onUpload: (files: File[]) => Promise<void>;
  onCancel?: () => void;
  maxSizeMB?: number;
  accept?: string[];
}

interface UploadState {
  status: 'idle' | 'dragover' | 'uploading' | 'processing' | 'error';
  progress: number;
  currentFile?: string;
  processingStep?: ProcessingStep;
  error?: string;
}

type ProcessingStep =
  | 'uploading'
  | 'parsing_document'
  | 'extracting_line_items'
  | 'matching_products'
  | 'generating_rfq';

const PROCESSING_MESSAGES: Record<ProcessingStep, string> = {
  uploading: 'Uploading document...',
  parsing_document: 'Reading document structure...',
  extracting_line_items: 'Extracting line items...',
  matching_products: 'Matching to IMPA catalog...',
  generating_rfq: 'Generating RFQ draft...',
};

export function DocumentDropZone({ onUpload, onCancel, maxSizeMB = 10, accept }: DocumentDropZoneProps) {
  const [state, setState] = useState<UploadState>({ status: 'idle', progress: 0 });

  const handleDrop = async (files: File[]) => {
    setState({ status: 'uploading', progress: 0, currentFile: files[0].name });

    try {
      await onUpload(files);
    } catch (error) {
      setState({ status: 'error', progress: 0, error: error.message });
    }
  };

  return (
    <div
      className={cn(
        'relative rounded-xl border-2 border-dashed p-8 text-center transition-all duration-200',
        state.status === 'idle' && 'border-border hover:border-primary/50 hover:bg-primary/5',
        state.status === 'dragover' && 'border-primary bg-primary/10 scale-[1.02]',
        state.status === 'uploading' && 'border-primary/50 bg-primary/5',
        state.status === 'processing' && 'border-secondary bg-secondary/5',
        state.status === 'error' && 'border-error bg-error/5'
      )}
      onDragOver={(e) => { e.preventDefault(); setState(s => ({ ...s, status: 'dragover' })); }}
      onDragLeave={() => setState(s => ({ ...s, status: 'idle' }))}
      onDrop={(e) => { e.preventDefault(); handleDrop(Array.from(e.dataTransfer.files)); }}
    >
      {/* State-specific content rendered here */}
    </div>
  );
}
```

### Processing Animation Component

```tsx
// components/upload/ProcessingAnimation.tsx
interface ProcessingAnimationProps {
  step: ProcessingStep;
  progress?: number;
  itemsFound?: number;
  matchedItems?: number;
}

export function ProcessingAnimation({ step, progress, itemsFound, matchedItems }: ProcessingAnimationProps) {
  return (
    <div className="flex flex-col items-center gap-4">
      {/* Scanning animation */}
      <div className="relative h-16 w-16">
        <div className="absolute inset-0 rounded-full border-2 border-secondary/30" />
        <div className="absolute inset-0 rounded-full border-2 border-secondary border-t-transparent animate-spin" />
        <DocumentIcon className="absolute inset-0 m-auto h-8 w-8 text-secondary" />
      </div>

      {/* Step message */}
      <p className="text-sm font-medium text-secondary">
        {PROCESSING_MESSAGES[step]}
      </p>

      {/* Progress details */}
      {step === 'extracting_line_items' && itemsFound !== undefined && (
        <p className="text-xs text-muted-foreground">
          Found {itemsFound} line items
        </p>
      )}

      {step === 'matching_products' && matchedItems !== undefined && itemsFound !== undefined && (
        <div className="w-48">
          <ProgressBar value={(matchedItems / itemsFound) * 100} />
          <p className="text-xs text-muted-foreground mt-1 text-center">
            Matched {matchedItems} of {itemsFound} items
          </p>
        </div>
      )}

      {/* Processing steps indicator */}
      <ProcessingSteps currentStep={step} />
    </div>
  );
}

function ProcessingSteps({ currentStep }: { currentStep: ProcessingStep }) {
  const steps: ProcessingStep[] = [
    'parsing_document',
    'extracting_line_items',
    'matching_products',
    'generating_rfq',
  ];

  const currentIndex = steps.indexOf(currentStep);

  return (
    <div className="flex items-center gap-2">
      {steps.map((step, index) => (
        <div key={step} className="flex items-center gap-2">
          <div
            className={cn(
              'h-2 w-2 rounded-full',
              index < currentIndex && 'bg-success',
              index === currentIndex && 'bg-secondary animate-pulse',
              index > currentIndex && 'bg-muted'
            )}
          />
          {index < steps.length - 1 && (
            <div
              className={cn(
                'h-0.5 w-4',
                index < currentIndex ? 'bg-success' : 'bg-muted'
              )}
            />
          )}
        </div>
      ))}
    </div>
  );
}
```

### Confidence Visualization in Conversation

When document processing completes, results appear in the conversation with confidence indicators:

```tsx
// components/conversation/DocumentProcessingResult.tsx
interface DocumentProcessingResultProps {
  result: DocumentProcessingResult;
  onReview: (itemIds: string[]) => void;
  onConfirm: () => void;
}

export function DocumentProcessingResult({ result, onReview, onConfirm }: DocumentProcessingResultProps) {
  const highConfidence = result.lineItems.filter(item => item.confidence >= 0.95);
  const needsReview = result.lineItems.filter(item => item.confidence < 0.95);

  return (
    <ConversationBubble type="ai">
      <div className="space-y-4">
        <p>
          I've processed your requisition document. Here's what I found:
        </p>

        {/* Summary Card */}
        <div className="rounded-lg border p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-medium">Line Items Extracted</span>
            <span className="text-lg font-semibold">{result.lineItems.length}</span>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex items-center gap-2">
              <ConfidenceIndicator level="high" size="sm" showLabel={false} />
              <span>{highConfidence.length} ready to confirm</span>
            </div>
            <div className="flex items-center gap-2">
              <ConfidenceIndicator level="medium" size="sm" showLabel={false} />
              <span>{needsReview.length} need review</span>
            </div>
          </div>
        </div>

        {/* Items needing review */}
        {needsReview.length > 0 && (
          <ActionCard
            type="question"
            title={`${needsReview.length} items need your input`}
            description="I'm not 100% sure about these matches. Can you verify?"
            primaryAction={{ label: 'Review Items', onClick: () => onReview(needsReview.map(i => i.id)) }}
            secondaryAction={{ label: 'Skip for Now', onClick: onConfirm }}
          />
        )}

        {/* High confidence items */}
        {needsReview.length === 0 && (
          <ActionCard
            type="confirm"
            title="All items matched with high confidence"
            description="Ready to create RFQ draft"
            confidence={0.97}
            primaryAction={{ label: 'Create RFQ', onClick: onConfirm }}
          />
        )}
      </div>
    </ConversationBubble>
  );
}
```

### Disambiguation Conversation Flow

When low-confidence extractions occur, PortiQ initiates a conversational disambiguation:

```tsx
// components/conversation/DisambiguationMessage.tsx
interface DisambiguationMessageProps {
  item: LowConfidenceItem;
  options: ProductMatch[];
  onSelect: (productId: string) => void;
  onCustom: (description: string) => void;
}

export function DisambiguationMessage({ item, options, onSelect, onCustom }: DisambiguationMessageProps) {
  return (
    <ConversationBubble type="ai">
      <div className="space-y-4">
        <p>
          I found "{item.originalText}" but I'm not certain which product this refers to:
        </p>

        <div className="space-y-2">
          {options.map((option, index) => (
            <button
              key={option.id}
              onClick={() => onSelect(option.id)}
              className={cn(
                'w-full flex items-center gap-3 p-3 rounded-lg border text-left',
                'hover:border-primary hover:bg-primary/5 transition-colors'
              )}
            >
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-muted flex items-center justify-center text-sm font-medium">
                {index + 1}
              </span>
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{option.productName}</p>
                <p className="text-sm text-muted-foreground">IMPA {option.impaCode}</p>
              </div>
              <ConfidenceIndicator level={option.confidence} size="sm" />
            </button>
          ))}

          <button
            onClick={() => onCustom('')}
            className="w-full flex items-center gap-3 p-3 rounded-lg border border-dashed hover:border-primary text-left text-muted-foreground"
          >
            <PlusIcon className="h-5 w-5" />
            <span>None of these - add custom description</span>
          </button>
        </div>
      </div>
    </ConversationBubble>
  );
}
```

### Real-Time Processing Updates via WebSocket

```typescript
// lib/document-processing-socket.ts
interface ProcessingUpdate {
  documentId: string;
  status: 'processing' | 'complete' | 'error';
  step?: ProcessingStep;
  progress?: number;
  itemsFound?: number;
  matchedItems?: number;
  result?: DocumentProcessingResult;
  error?: string;
}

export function useDocumentProcessingUpdates(documentId: string) {
  const [updates, setUpdates] = useState<ProcessingUpdate | null>(null);

  useEffect(() => {
    const socket = portiqSocket;

    socket.on('document:processing_update', (update: ProcessingUpdate) => {
      if (update.documentId === documentId) {
        setUpdates(update);

        // Add to conversation when complete
        if (update.status === 'complete' && update.result) {
          usePortiQStore.getState().addSystemMessage({
            type: 'document_processed',
            data: update.result,
          });
        }
      }
    });

    return () => {
      socket.off('document:processing_update');
    };
  }, [documentId]);

  return updates;
}
```

### Mobile Voice-Initiated Upload

On mobile, users can initiate document upload via voice command:

```tsx
// Voice command: "Upload my requisition" triggers camera/file picker
function handleVoiceUploadCommand() {
  // Show bottom sheet with upload options
  showBottomSheet({
    title: 'Upload Requisition',
    options: [
      { label: 'Take Photo', icon: CameraIcon, action: openCamera },
      { label: 'Choose from Gallery', icon: ImageIcon, action: openGallery },
      { label: 'Select Document', icon: FileIcon, action: openFilePicker },
    ],
  });
}
```

---

## References
- [Azure Document Intelligence v4.0](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/)
- [BullMQ Documentation](https://docs.bullmq.io/)
- [LlamaIndex Document Processing](https://docs.llamaindex.ai/)
- [ADR-UI-013: PortiQ Buyer Experience](../ui/ADR-UI-013-portiq-buyer-experience.md)
- [ADR-UI-009: Design System (DocumentDropZone Component)](../ui/ADR-UI-009-design-system-theming.md)
