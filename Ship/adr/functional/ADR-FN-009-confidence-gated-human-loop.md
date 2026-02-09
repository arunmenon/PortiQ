# ADR-FN-009: Confidence-Gated Human-in-Loop

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

The document AI pipeline must balance automation efficiency with accuracy requirements, routing uncertain extractions to human reviewers while auto-approving high-confidence results.

### Business Context
Document AI reduces manual effort by 60-90% but cannot achieve 100% accuracy on all documents. Poor scans, handwritten notes, unusual formats, and ambiguous product descriptions require human judgment. A rigid approach (all-manual or all-automated) fails—either eliminating efficiency gains or introducing unacceptable error rates. The solution must dynamically route items based on extraction confidence.

### Technical Context
- LLM extraction outputs confidence scores (0-1) per line item
- SKU matching produces similarity scores for catalog matches
- Review interface needed for human operators
- Feedback loop to improve extraction over time
- Integration with async pipeline (ADR-FN-006)

### Assumptions
- Confidence scores from LLM and matching are calibrated and meaningful
- Human review capacity exists (operations team)
- Review latency of hours is acceptable for low-confidence items
- Feedback can be used for prompt improvement (not model fine-tuning)

---

## Decision Drivers

- Maximize automation while maintaining accuracy
- Efficient use of human review capacity
- Clear routing logic operators can understand
- Feedback loop for continuous improvement
- Audit trail for all decisions
- Scalable as volume grows

---

## Considered Options

### Option 1: Fixed Threshold Routing
**Description:** Simple threshold-based routing with fixed confidence levels.

**Pros:**
- Simple to implement and understand
- Predictable routing behavior
- Easy to adjust thresholds

**Cons:**
- No adaptation to item complexity
- Same thresholds for all categories
- May over/under route certain item types

### Option 2: Multi-Threshold Tiered Routing
**Description:** Three-tier system with auto-approve (>95%), quick review (80-95%), and full review (<80%) based on combined confidence scoring.

**Pros:**
- Graduated review intensity
- Balances automation and oversight
- Different review workflows per tier
- Optimizes reviewer time

**Cons:**
- More complex routing logic
- Requires multiple review interfaces
- Threshold tuning needed

### Option 3: ML-Based Dynamic Routing
**Description:** Machine learning model predicts review need based on multiple signals.

**Pros:**
- Adapts to patterns
- Multi-signal decision making
- Continuous improvement

**Cons:**
- Requires training data
- Black-box decisions
- Higher implementation complexity
- Cold start problem

---

## Decision

**Chosen Option:** Multi-Threshold Tiered Routing

We will implement a three-tier confidence-gated system: auto-approve (≥95%), quick review (80-94%), and full manual review (<80%), with category-specific threshold adjustments.

### Rationale
The tiered approach optimizes human review capacity by matching review intensity to confidence level. High-confidence items flow through automatically, moderate-confidence items get quick validation, and low-confidence items receive full attention. This is the pattern recommended in the technical blueprint and proven in production document AI systems.

---

## Consequences

### Positive
- 60-90% reduction in manual processing
- Graduated review matches effort to need
- Predictable routing operators understand
- Clear audit trail for all decisions
- Adaptable thresholds per category

### Negative
- Threshold tuning requires iteration
- **Mitigation:** Start conservative, adjust based on error rates
- Multiple review interfaces to build
- **Mitigation:** Start with single interface, add optimization later

### Risks
- Miscalibrated thresholds cause errors: Monitor error rates, adjust thresholds
- Review backlog during peaks: Prioritization logic, temporary threshold adjustment
- Reviewer fatigue affecting quality: Rotation, gamification, quality sampling

---

## Implementation Notes

### Confidence Scoring Model

```typescript
// confidence/scoring.service.ts
interface ConfidenceFactors {
  llmExtractionConfidence: number;  // From LLM output
  skuMatchSimilarity: number;       // From pgvector matching
  textQuality: number;              // Document clarity score
  fieldCompleteness: number;        // Required fields present
}

interface ConfidenceResult {
  overallScore: number;
  tier: 'auto-approve' | 'quick-review' | 'full-review';
  factors: ConfidenceFactors;
  reasoning: string;
}

class ConfidenceScoringService {
  private readonly WEIGHTS = {
    llmExtraction: 0.35,
    skuMatch: 0.35,
    textQuality: 0.15,
    fieldCompleteness: 0.15
  };

  calculateConfidence(factors: ConfidenceFactors): ConfidenceResult {
    const overallScore =
      factors.llmExtractionConfidence * this.WEIGHTS.llmExtraction +
      factors.skuMatchSimilarity * this.WEIGHTS.skuMatch +
      factors.textQuality * this.WEIGHTS.textQuality +
      factors.fieldCompleteness * this.WEIGHTS.fieldCompleteness;

    return {
      overallScore,
      tier: this.determineTier(overallScore),
      factors,
      reasoning: this.generateReasoning(factors, overallScore)
    };
  }

  private determineTier(score: number): ConfidenceResult['tier'] {
    if (score >= 0.95) return 'auto-approve';
    if (score >= 0.80) return 'quick-review';
    return 'full-review';
  }
}
```

### Threshold Configuration

```typescript
// config/confidence-thresholds.ts
interface CategoryThresholds {
  autoApprove: number;
  quickReview: number;
}

const DEFAULT_THRESHOLDS: CategoryThresholds = {
  autoApprove: 0.95,
  quickReview: 0.80
};

// Category-specific overrides
const CATEGORY_THRESHOLDS: Record<string, CategoryThresholds> = {
  // Safety equipment requires higher confidence
  '31': { autoApprove: 0.98, quickReview: 0.90 },  // Protective gear
  '33': { autoApprove: 0.98, quickReview: 0.90 },  // Safety equipment
  '39': { autoApprove: 0.98, quickReview: 0.90 },  // Medicine

  // Commodities can have lower thresholds
  '55': { autoApprove: 0.92, quickReview: 0.75 },  // Cleaning chemicals
  '00': { autoApprove: 0.92, quickReview: 0.75 },  // Provisions
};

export function getThresholds(categoryCode: string): CategoryThresholds {
  return CATEGORY_THRESHOLDS[categoryCode] ?? DEFAULT_THRESHOLDS;
}
```

### Review Queue Management

```typescript
// review/queue.service.ts
interface ReviewItem {
  id: string;
  documentId: string;
  lineIndex: number;
  originalText: string;
  extractedData: ExtractedLineItem;
  matchResults: MatchResult[];
  confidenceResult: ConfidenceResult;
  tier: 'quick-review' | 'full-review';
  priority: number;
  createdAt: Date;
  assignedTo?: string;
  status: 'pending' | 'in-progress' | 'completed' | 'escalated';
}

class ReviewQueueService {
  async addToQueue(item: ReviewItem): Promise<void> {
    const priority = this.calculatePriority(item);

    await this.db.reviewQueue.insert({
      ...item,
      priority,
      status: 'pending'
    });

    // Notify reviewers if high priority
    if (priority >= 8) {
      await this.notificationService.notifyReviewers(item);
    }
  }

  private calculatePriority(item: ReviewItem): number {
    let priority = 5; // Base priority

    // Urgent documents get higher priority
    if (item.documentMetadata?.urgent) priority += 3;

    // Older items get higher priority (prevent starvation)
    const ageHours = (Date.now() - item.createdAt.getTime()) / 3600000;
    priority += Math.min(ageHours / 2, 3);

    // Full review items slightly higher than quick review
    if (item.tier === 'full-review') priority += 1;

    return Math.min(priority, 10);
  }

  async assignNextItem(reviewerId: string, tier?: string): Promise<ReviewItem | null> {
    const item = await this.db.reviewQueue.findFirst({
      where: {
        status: 'pending',
        tier: tier ?? undefined
      },
      orderBy: [
        { priority: 'desc' },
        { createdAt: 'asc' }
      ]
    });

    if (item) {
      await this.db.reviewQueue.update({
        where: { id: item.id },
        data: {
          status: 'in-progress',
          assignedTo: reviewerId
        }
      });
    }

    return item;
  }
}
```

### Review Decision Recording

```typescript
// review/decision.service.ts
interface ReviewDecision {
  reviewItemId: string;
  reviewerId: string;
  decision: 'approve' | 'correct' | 'reject';
  corrections?: {
    field: string;
    original: any;
    corrected: any;
  }[];
  selectedMatch?: string;  // IMPA code if different from suggested
  notes?: string;
  duration: number;  // Time spent in seconds
}

class ReviewDecisionService {
  async recordDecision(decision: ReviewDecision): Promise<void> {
    // Store decision
    await this.db.reviewDecisions.insert(decision);

    // Update extraction record
    await this.updateExtraction(decision);

    // Record for analytics and threshold tuning
    await this.recordAnalytics(decision);

    // Trigger downstream processing
    if (decision.decision !== 'reject') {
      await this.continueProcessing(decision);
    }
  }

  private async recordAnalytics(decision: ReviewDecision): Promise<void> {
    const reviewItem = await this.db.reviewQueue.findById(decision.reviewItemId);

    await this.analytics.record({
      event: 'review_completed',
      tier: reviewItem.tier,
      originalConfidence: reviewItem.confidenceResult.overallScore,
      decision: decision.decision,
      hadCorrections: (decision.corrections?.length ?? 0) > 0,
      duration: decision.duration
    });
  }
}
```

### Feedback Loop

```typescript
// feedback/confidence-tuning.service.ts
class ConfidenceTuningService {
  async analyzeReviewOutcomes(): Promise<ThresholdRecommendations> {
    const recentDecisions = await this.db.reviewDecisions.findMany({
      where: {
        createdAt: { gte: subDays(new Date(), 30) }
      },
      include: { reviewItem: true }
    });

    const byTier = groupBy(recentDecisions, d => d.reviewItem.tier);

    // Calculate false positive rate (auto-approved but had errors)
    const autoApproveErrors = await this.calculateAutoApproveErrorRate();

    // Calculate unnecessary reviews (high confidence but still reviewed correctly)
    const unnecessaryReviews = byTier['quick-review']?.filter(
      d => d.decision === 'approve' && !d.corrections?.length
    ).length ?? 0;

    return {
      currentAutoApproveThreshold: 0.95,
      suggestedAutoApproveThreshold: this.calculateSuggestedThreshold(autoApproveErrors),
      unnecessaryReviewRate: unnecessaryReviews / (byTier['quick-review']?.length ?? 1),
      recommendations: this.generateRecommendations(autoApproveErrors, unnecessaryReviews)
    };
  }
}
```

### Dependencies
- ADR-FN-006: Document AI Pipeline Architecture
- ADR-FN-008: LLM Provider for Normalization
- ADR-NF-002: Vector Search with pgvector
- ADR-NF-008: Async Processing (BullMQ)

### Migration Strategy
1. Implement confidence scoring service
2. Create review queue infrastructure
3. Build review UI (quick and full modes)
4. Set initial thresholds (conservative)
5. Launch with 100% review, gradually reduce
6. Implement analytics and threshold tuning
7. Add category-specific thresholds

---

## Operational Considerations

### Confidence Threshold Tuning and Review Process

#### Initial Threshold Calibration

| Phase | Duration | Auto-Approve Threshold | Review Threshold | Approach |
|-------|----------|------------------------|------------------|----------|
| Launch (Week 1-2) | 14 days | 100% review | N/A | All items reviewed to establish baseline |
| Calibration (Week 3-4) | 14 days | 0.98 | 0.90 | Conservative thresholds, measure error rates |
| Optimization (Month 2) | 30 days | 0.95 | 0.80 | Standard thresholds, track corrections |
| Steady State (Month 3+) | Ongoing | Dynamic | Dynamic | Data-driven adjustment |

#### Threshold Adjustment Algorithm

```typescript
// Automatic threshold tuning based on review outcomes
interface ThresholdTuningConfig {
  evaluationPeriodDays: 7;
  minSampleSize: 100;
  targetAutoApproveErrorRate: 0.01;   // 1% max errors in auto-approved
  targetUnnecessaryReviewRate: 0.15;  // 15% max unnecessary reviews
}

@Injectable()
export class ThresholdTuningService {
  @Cron('0 0 * * 0')  // Weekly on Sunday
  async evaluateAndAdjustThresholds(): Promise<ThresholdAdjustment> {
    const metrics = await this.calculateWeeklyMetrics();

    const adjustment: ThresholdAdjustment = {
      previousAutoApprove: this.currentThresholds.autoApprove,
      previousQuickReview: this.currentThresholds.quickReview,
      newAutoApprove: this.currentThresholds.autoApprove,
      newQuickReview: this.currentThresholds.quickReview,
      reason: []
    };

    // Check auto-approve error rate
    if (metrics.autoApproveErrorRate > 0.01) {
      // Too many errors slipping through - raise threshold
      adjustment.newAutoApprove = Math.min(0.99, this.currentThresholds.autoApprove + 0.01);
      adjustment.reason.push(`Auto-approve error rate ${(metrics.autoApproveErrorRate * 100).toFixed(1)}% > 1% target`);
    } else if (metrics.autoApproveErrorRate < 0.005 && metrics.unnecessaryReviewRate > 0.15) {
      // Very few errors but many unnecessary reviews - lower threshold
      adjustment.newAutoApprove = Math.max(0.90, this.currentThresholds.autoApprove - 0.01);
      adjustment.reason.push(`Low error rate with ${(metrics.unnecessaryReviewRate * 100).toFixed(1)}% unnecessary reviews`);
    }

    // Check review efficiency
    if (metrics.quickReviewCorrectionRate > 0.5) {
      // Too many corrections in quick review - widen the band
      adjustment.newQuickReview = Math.max(0.70, this.currentThresholds.quickReview - 0.02);
      adjustment.reason.push(`Quick review correction rate too high`);
    }

    await this.applyAdjustment(adjustment);
    return adjustment;
  }

  private async calculateWeeklyMetrics(): Promise<ThresholdMetrics> {
    const weekAgo = subDays(new Date(), 7);

    // Sample auto-approved items for quality check
    const autoApprovedSample = await this.reviewQueueRepository.sampleAutoApproved({
      since: weekAgo,
      sampleSize: 100
    });
    const autoApproveErrors = await this.qualityCheckService.findErrors(autoApprovedSample);

    // Analyze review decisions
    const reviewDecisions = await this.reviewDecisionRepository.findSince(weekAgo);
    const unnecessaryReviews = reviewDecisions.filter(d =>
      d.tier === 'quick-review' &&
      d.decision === 'approve' &&
      !d.corrections?.length
    );

    return {
      autoApproveErrorRate: autoApproveErrors.length / autoApprovedSample.length,
      unnecessaryReviewRate: unnecessaryReviews.length / reviewDecisions.length,
      quickReviewCorrectionRate: reviewDecisions
        .filter(d => d.tier === 'quick-review' && d.corrections?.length)
        .length / reviewDecisions.filter(d => d.tier === 'quick-review').length,
      avgReviewTime: this.calculateAvgReviewTime(reviewDecisions),
      sampleSize: autoApprovedSample.length
    };
  }
}
```

#### Category-Specific Threshold Review

| Category | Risk Level | Auto-Approve | Quick Review | Full Review | Review Frequency |
|----------|------------|--------------|--------------|-------------|------------------|
| Safety equipment (31, 33) | High | 0.98 | 0.92 | < 0.92 | Monthly |
| Medical supplies (39) | Critical | 0.99 | 0.95 | < 0.95 | Bi-weekly |
| Provisions (00) | Low | 0.92 | 0.75 | < 0.75 | Quarterly |
| Cleaning supplies (55) | Low | 0.92 | 0.75 | < 0.75 | Quarterly |
| Engine parts (43-47) | Medium | 0.95 | 0.85 | < 0.85 | Monthly |
| Electrical (35-36) | Medium | 0.95 | 0.85 | < 0.85 | Monthly |

### Audit Trails for Manual Overrides and Feedback

#### Comprehensive Audit Log Schema

```sql
-- Extraction audit log
CREATE TABLE extraction_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id),
    line_item_index INTEGER NOT NULL,

    -- Original extraction
    original_extraction JSONB NOT NULL,
    original_confidence DECIMAL(4, 3) NOT NULL,
    auto_approved BOOLEAN NOT NULL,

    -- Review details (if reviewed)
    review_id UUID REFERENCES review_decisions(id),
    reviewer_id UUID REFERENCES users(id),
    review_tier VARCHAR(20),
    review_decision VARCHAR(20),

    -- Corrections applied
    corrections JSONB,  -- Array of {field, original, corrected, reason}
    final_extraction JSONB NOT NULL,

    -- SKU matching
    original_sku_match VARCHAR(10),
    original_match_confidence DECIMAL(4, 3),
    final_sku_match VARCHAR(10),
    sku_override_reason TEXT,

    -- Timestamps
    extracted_at TIMESTAMPTZ NOT NULL,
    reviewed_at TIMESTAMPTZ,
    finalized_at TIMESTAMPTZ NOT NULL,

    -- Metadata
    extraction_model VARCHAR(50),
    prompt_version VARCHAR(20),
    processing_time_ms INTEGER,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_document ON extraction_audit_log(document_id);
CREATE INDEX idx_audit_reviewer ON extraction_audit_log(reviewer_id);
CREATE INDEX idx_audit_corrections ON extraction_audit_log USING GIN (corrections);
CREATE INDEX idx_audit_sku_override ON extraction_audit_log(final_sku_match)
  WHERE original_sku_match != final_sku_match;
```

#### Audit Event Recording

```typescript
// Audit service implementation
@Injectable()
export class ExtractionAuditService {
  async recordExtraction(extraction: LineItemExtraction): Promise<void> {
    await this.auditRepository.insert({
      documentId: extraction.documentId,
      lineItemIndex: extraction.lineIndex,
      originalExtraction: extraction.data,
      originalConfidence: extraction.confidence,
      autoApproved: extraction.tier === 'auto-approve',
      finalExtraction: extraction.data,
      extractedAt: new Date(),
      finalizedAt: extraction.tier === 'auto-approve' ? new Date() : null,
      extractionModel: extraction.metadata.model,
      promptVersion: extraction.metadata.promptVersion,
      processingTimeMs: extraction.metadata.processingTimeMs
    });
  }

  async recordReviewDecision(decision: ReviewDecision): Promise<void> {
    const auditRecord = await this.auditRepository.findByDocumentAndLine(
      decision.documentId,
      decision.lineItemIndex
    );

    const corrections = this.calculateCorrections(
      auditRecord.originalExtraction,
      decision.correctedData
    );

    await this.auditRepository.update(auditRecord.id, {
      reviewId: decision.id,
      reviewerId: decision.reviewerId,
      reviewTier: decision.tier,
      reviewDecision: decision.decision,
      corrections,
      finalExtraction: decision.correctedData || auditRecord.originalExtraction,
      finalSkuMatch: decision.selectedSku || auditRecord.originalSkuMatch,
      skuOverrideReason: decision.skuOverrideReason,
      reviewedAt: new Date(),
      finalizedAt: new Date()
    });

    // Record for model feedback
    if (corrections.length > 0) {
      await this.feedbackService.recordCorrection({
        originalExtraction: auditRecord.originalExtraction,
        corrections,
        documentType: auditRecord.documentMetadata?.type,
        promptVersion: auditRecord.promptVersion
      });
    }
  }

  private calculateCorrections(original: any, corrected: any): Correction[] {
    const corrections: Correction[] = [];
    const fields = ['productName', 'quantity', 'unit', 'specifications'];

    for (const field of fields) {
      if (JSON.stringify(original[field]) !== JSON.stringify(corrected[field])) {
        corrections.push({
          field,
          original: original[field],
          corrected: corrected[field],
          timestamp: new Date()
        });
      }
    }

    return corrections;
  }
}
```

#### Feedback Injection Pipeline

```typescript
// Feedback aggregation for model improvement
@Injectable()
export class FeedbackAggregationService {
  @Cron('0 0 * * 1')  // Weekly on Monday
  async aggregateFeedbackForTraining(): Promise<FeedbackReport> {
    const weekAgo = subDays(new Date(), 7);

    // Collect corrections by type
    const corrections = await this.auditRepository.findCorrections({
      since: weekAgo,
      minSampleSize: 10
    });

    const aggregated = this.aggregateByPattern(corrections);

    // Generate prompt improvement suggestions
    const suggestions = await this.generatePromptSuggestions(aggregated);

    // Store for data team review
    const report: FeedbackReport = {
      period: { start: weekAgo, end: new Date() },
      totalCorrections: corrections.length,
      correctionsByField: this.groupByField(corrections),
      correctionsByCategory: this.groupByCategory(corrections),
      topPatterns: aggregated.slice(0, 20),
      promptSuggestions: suggestions,
      skuOverrides: await this.analyzeSkuOverrides(weekAgo)
    };

    await this.reportRepository.save(report);

    // Alert if correction rate is concerning
    if (report.totalCorrections / await this.getTotalProcessed(weekAgo) > 0.1) {
      await this.alertService.sendWarning('high_correction_rate', report);
    }

    return report;
  }

  private aggregateByPattern(corrections: Correction[]): CorrectionPattern[] {
    const patterns: Map<string, CorrectionPattern> = new Map();

    for (const correction of corrections) {
      const patternKey = this.extractPattern(correction);

      if (!patterns.has(patternKey)) {
        patterns.set(patternKey, {
          pattern: patternKey,
          field: correction.field,
          examples: [],
          count: 0
        });
      }

      const pattern = patterns.get(patternKey)!;
      pattern.count++;
      if (pattern.examples.length < 5) {
        pattern.examples.push({
          original: correction.original,
          corrected: correction.corrected
        });
      }
    }

    return Array.from(patterns.values())
      .sort((a, b) => b.count - a.count);
  }
}
```

### Open Questions

- **Q:** What staffing and SLAs are required to keep human review from becoming a bottleneck?
  - **A:** Staffing model and SLA framework:

  **Volume Projections and Staffing Requirements:**

  | Scale Phase | Documents/Day | Items/Day | Review Rate | Items for Review | FTE Required |
  |-------------|---------------|-----------|-------------|------------------|--------------|
  | MVP (Month 1-3) | 50 | 7,500 | 25% | 1,875 | 1.5 |
  | Growth (Month 4-6) | 150 | 22,500 | 20% | 4,500 | 3.0 |
  | Scale (Month 7-12) | 400 | 60,000 | 15% | 9,000 | 5.5 |
  | Mature (Year 2+) | 800 | 120,000 | 10% | 12,000 | 7.0 |

  **Productivity Assumptions:**
  | Review Type | Items/Hour | Quality Target | Fatigue Factor |
  |-------------|------------|----------------|----------------|
  | Quick review | 40 | 99% accuracy | 0.85 (after 4 hrs) |
  | Full review | 15 | 99.5% accuracy | 0.80 (after 4 hrs) |
  | Escalated | 8 | 99.9% accuracy | 0.90 (high focus) |

  **SLA Framework:**
  ```typescript
  interface ReviewSLA {
    tier: string;
    targetResponse: number;      // Minutes
    maxResponse: number;         // Minutes
    escalationTrigger: number;   // Minutes
    priorityBoost: PriorityRule[];
  }

  const REVIEW_SLAS: ReviewSLA[] = [
    {
      tier: 'quick-review',
      targetResponse: 120,      // 2 hours
      maxResponse: 480,         // 8 hours
      escalationTrigger: 360,   // 6 hours
      priorityBoost: [
        { condition: 'document.urgent', boost: 2 },
        { condition: 'customer.premium', boost: 1.5 },
        { condition: 'age > 4h', boost: 0.5 }  // Incremental
      ]
    },
    {
      tier: 'full-review',
      targetResponse: 240,      // 4 hours
      maxResponse: 960,         // 16 hours
      escalationTrigger: 720,   // 12 hours
      priorityBoost: [
        { condition: 'document.urgent', boost: 2 },
        { condition: 'customer.premium', boost: 1.5 }
      ]
    },
    {
      tier: 'escalated',
      targetResponse: 60,       // 1 hour
      maxResponse: 180,         // 3 hours
      escalationTrigger: 120,   // 2 hours
      priorityBoost: []
    }
  ];
  ```

  **Bottleneck Prevention Measures:**

  | Situation | Trigger | Automatic Response | Human Response |
  |-----------|---------|-------------------|----------------|
  | Queue depth high | > 200 items | Alert + increase auto-approve threshold by 0.02 | Call in additional reviewers |
  | SLA breach rate high | > 10% breaching | Notify manager + redistribute queue | Prioritization meeting |
  | Peak period | Known busy times | Pre-scale reviewers | Flex scheduling |
  | Staff shortage | < 70% capacity | Lower auto-approve threshold | Overtime/temp staff |

  **Real-time Capacity Monitoring:**
  ```typescript
  @Injectable()
  export class ReviewCapacityMonitor {
    @Cron('*/10 * * * *')  // Every 10 minutes
    async checkCapacity(): Promise<void> {
      const currentQueue = await this.getQueueDepth();
      const activeReviewers = await this.getActiveReviewers();
      const avgThroughput = await this.getAvgThroughput(activeReviewers);

      const estimatedClearTime = currentQueue / avgThroughput;  // hours
      const newItemsPerHour = await this.getIncomingRate();
      const netRate = avgThroughput - newItemsPerHour;

      if (netRate < 0) {
        // Queue growing - capacity insufficient
        await this.alertService.sendWarning('review_capacity_insufficient', {
          queueDepth: currentQueue,
          reviewers: activeReviewers.length,
          throughput: avgThroughput,
          incomingRate: newItemsPerHour,
          estimatedBacklogGrowth: Math.abs(netRate) * 8  // 8-hour shift
        });

        // Temporary threshold adjustment
        await this.adjustThresholdsForCapacity();
      }
    }
  }
  ```

---

## PortiQ Conversational Review UX

The PortiQ conversation-first interface transforms the traditional review queue into an in-conversation experience. Reviewers interact with low-confidence extractions through natural dialogue, making decisions with quick approval patterns.

### In-Conversation Review Flow

Instead of a separate review interface, PortiQ presents review items within the conversation:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Conversational Review Flow                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ╭─────────────────────────────────────────────────────────╮   │
│  │ PortiQ                                                    │   │
│  │                                                           │   │
│  │ I need your help with 3 items from the MV Pacific Star   │   │
│  │ requisition. Let's go through them quickly:               │   │
│  │                                                           │   │
│  │ ┌─────────────────────────────────────────────────────┐  │   │
│  │ │ Item 1 of 3                         72% confident   │  │   │
│  │ │                                                      │  │   │
│  │ │ Original: "Synthetic rope 24mm x 200m"              │  │   │
│  │ │                                                      │  │   │
│  │ │ Best matches:                                        │  │   │
│  │ │ ① IMPA 210455 - PP Rope 24mm      78%              │  │   │
│  │ │ ② IMPA 210456 - Nylon Rope 24mm   65%              │  │   │
│  │ │ ③ IMPA 210457 - Polyester 24mm    62%              │  │   │
│  │ │                                                      │  │   │
│  │ │ [1] [2] [3] [None - specify]                        │  │   │
│  │ └─────────────────────────────────────────────────────┘  │   │
│  ╰─────────────────────────────────────────────────────────╯   │
│                                                                  │
│  ╭─────────────────────────────────────────────────────────╮   │
│  │ 👤 User: 1                                                │   │
│  ╰─────────────────────────────────────────────────────────╯   │
│                                                                  │
│  ╭─────────────────────────────────────────────────────────╮   │
│  │ PortiQ: Great! PP Rope 24mm it is.                       │   │
│  │                                                           │   │
│  │ ┌─────────────────────────────────────────────────────┐  │   │
│  │ │ Item 2 of 3                         68% confident   │  │   │
│  │ │ ...                                                  │  │   │
│  │ └─────────────────────────────────────────────────────┘  │   │
│  ╰─────────────────────────────────────────────────────────╯   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Quick Approval Pattern Components

```tsx
// components/review/InConversationReview.tsx
interface InConversationReviewProps {
  items: ReviewItem[];
  onComplete: (decisions: ReviewDecision[]) => void;
}

export function InConversationReview({ items, onComplete }: InConversationReviewProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [decisions, setDecisions] = useState<ReviewDecision[]>([]);

  const currentItem = items[currentIndex];
  const isLast = currentIndex === items.length - 1;

  const handleSelect = (matchId: string | null, customValue?: string) => {
    const decision: ReviewDecision = {
      itemId: currentItem.id,
      selectedMatch: matchId,
      customValue,
      reviewedAt: new Date(),
    };

    setDecisions([...decisions, decision]);

    if (isLast) {
      onComplete([...decisions, decision]);
    } else {
      setCurrentIndex(currentIndex + 1);
    }
  };

  return (
    <ConversationBubble type="ai">
      <div className="space-y-4">
        {/* Progress indicator */}
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            Item {currentIndex + 1} of {items.length}
          </span>
          <ConfidenceIndicator level={currentItem.confidence} size="sm" />
        </div>

        {/* Original text */}
        <div className="p-3 bg-muted rounded-lg">
          <p className="text-sm text-muted-foreground mb-1">Original text:</p>
          <p className="font-medium">"{currentItem.originalText}"</p>
        </div>

        {/* Match options */}
        <div className="space-y-2">
          <p className="text-sm font-medium">Best matches:</p>
          {currentItem.matches.map((match, index) => (
            <QuickSelectOption
              key={match.id}
              index={index + 1}
              match={match}
              onSelect={() => handleSelect(match.id)}
            />
          ))}

          <button
            onClick={() => handleSelect(null)}
            className="w-full p-3 text-left border border-dashed rounded-lg hover:border-primary text-muted-foreground"
          >
            None of these - let me specify
          </button>
        </div>

        {/* Keyboard shortcuts hint */}
        <p className="text-xs text-muted-foreground">
          Press 1-{currentItem.matches.length} to quick select, or type to search
        </p>
      </div>
    </ConversationBubble>
  );
}

function QuickSelectOption({ index, match, onSelect }: QuickSelectOptionProps) {
  // Keyboard shortcut listener
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === String(index)) {
        onSelect();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [index, onSelect]);

  return (
    <button
      onClick={onSelect}
      className="w-full flex items-center gap-3 p-3 border rounded-lg hover:border-primary hover:bg-primary/5 transition-colors"
    >
      <kbd className="flex-shrink-0 w-6 h-6 rounded bg-muted flex items-center justify-center text-sm font-mono">
        {index}
      </kbd>
      <div className="flex-1 text-left">
        <p className="font-medium">{match.productName}</p>
        <p className="text-sm text-muted-foreground">IMPA {match.impaCode}</p>
      </div>
      <span className="text-sm text-muted-foreground">{Math.round(match.confidence * 100)}%</span>
    </button>
  );
}
```

### Batch Review Summary

After completing reviews, show a summary before finalizing:

```tsx
// components/review/ReviewSummary.tsx
interface ReviewSummaryProps {
  decisions: ReviewDecision[];
  originalItems: ReviewItem[];
  onConfirm: () => void;
  onRevise: (itemId: string) => void;
}

export function ReviewSummary({ decisions, originalItems, onConfirm, onRevise }: ReviewSummaryProps) {
  const matched = decisions.filter(d => d.selectedMatch !== null);
  const custom = decisions.filter(d => d.customValue !== undefined);
  const skipped = decisions.filter(d => d.selectedMatch === null && !d.customValue);

  return (
    <ConversationBubble type="ai">
      <div className="space-y-4">
        <p className="font-medium">Here's a summary of your review:</p>

        <div className="grid grid-cols-3 gap-4 text-center">
          <div className="p-3 bg-success/10 rounded-lg">
            <p className="text-2xl font-semibold text-success">{matched.length}</p>
            <p className="text-xs text-muted-foreground">Matched</p>
          </div>
          <div className="p-3 bg-info/10 rounded-lg">
            <p className="text-2xl font-semibold text-info">{custom.length}</p>
            <p className="text-xs text-muted-foreground">Custom</p>
          </div>
          <div className="p-3 bg-warning/10 rounded-lg">
            <p className="text-2xl font-semibold text-warning">{skipped.length}</p>
            <p className="text-xs text-muted-foreground">Skipped</p>
          </div>
        </div>

        {/* Decision list with edit option */}
        <div className="max-h-48 overflow-y-auto space-y-2">
          {decisions.map((decision, index) => {
            const original = originalItems.find(i => i.id === decision.itemId);
            const match = original?.matches.find(m => m.id === decision.selectedMatch);

            return (
              <div key={decision.itemId} className="flex items-center gap-2 text-sm p-2 rounded hover:bg-muted">
                <span className="text-muted-foreground">{index + 1}.</span>
                <span className="flex-1 truncate">
                  {match?.productName || decision.customValue || 'Skipped'}
                </span>
                <button
                  onClick={() => onRevise(decision.itemId)}
                  className="text-primary text-xs hover:underline"
                >
                  Edit
                </button>
              </div>
            );
          })}
        </div>

        <ActionCard
          type="confirm"
          title="Ready to proceed"
          primaryAction={{ label: 'Confirm All', onClick: onConfirm }}
        />
      </div>
    </ConversationBubble>
  );
}
```

### AI Confidence Display Patterns

```tsx
// components/review/ConfidenceExplanation.tsx
interface ConfidenceExplanationProps {
  item: ReviewItem;
  onRequestDetails: () => void;
}

export function ConfidenceExplanation({ item, onRequestDetails }: ConfidenceExplanationProps) {
  const factors = item.confidenceFactors;

  return (
    <div className="space-y-3">
      {/* Overall confidence */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Match Confidence</span>
        <ConfidenceIndicator level={item.confidence} />
      </div>

      {/* Factor breakdown */}
      <div className="space-y-2">
        <ConfidenceFactor
          label="Text similarity"
          value={factors.textSimilarity}
          description="How closely the text matches product names"
        />
        <ConfidenceFactor
          label="Specifications"
          value={factors.specMatch}
          description="Size, weight, material matches"
        />
        <ConfidenceFactor
          label="Category context"
          value={factors.categoryContext}
          description="Consistency with document category"
        />
        <ConfidenceFactor
          label="Historical patterns"
          value={factors.historicalMatch}
          description="Similar past orders from this buyer"
        />
      </div>

      {/* Why this confidence? */}
      {item.confidence < 0.8 && (
        <p className="text-xs text-muted-foreground italic">
          {item.lowConfidenceReason}
        </p>
      )}
    </div>
  );
}

function ConfidenceFactor({ label, value, description }: ConfidenceFactorProps) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1">
        <div className="flex items-center justify-between text-xs">
          <span>{label}</span>
          <span>{Math.round(value * 100)}%</span>
        </div>
        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
          <div
            className={cn(
              'h-full rounded-full transition-all',
              value >= 0.8 && 'bg-success',
              value >= 0.5 && value < 0.8 && 'bg-warning',
              value < 0.5 && 'bg-error'
            )}
            style={{ width: `${value * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
}
```

### Voice-Enabled Review

On mobile, reviewers can approve items via voice:

```tsx
// Voice commands for review
const REVIEW_VOICE_COMMANDS = {
  'one': () => selectOption(0),
  'two': () => selectOption(1),
  'three': () => selectOption(2),
  'first': () => selectOption(0),
  'second': () => selectOption(1),
  'third': () => selectOption(2),
  'confirm': () => confirmSelection(),
  'skip': () => skipItem(),
  'none': () => openCustomInput(),
  'go back': () => previousItem(),
};

function useVoiceReviewCommands(onCommand: (action: string) => void) {
  const { transcript, isListening } = useVoiceInput({
    onFinalTranscript: (text) => {
      const normalized = text.toLowerCase().trim();
      const command = Object.entries(REVIEW_VOICE_COMMANDS).find(
        ([key]) => normalized.includes(key)
      );
      if (command) {
        onCommand(command[0]);
      }
    },
  });

  return { transcript, isListening };
}
```

### Mobile Review Interface

```
┌─────────────────────────────────────────┐
│ ←  Review Items             2 of 5      │
├─────────────────────────────────────────┤
│                                          │
│  Original text:                          │
│  ┌────────────────────────────────────┐ │
│  │ "Synthetic rope 24mm x 200m"       │ │
│  └────────────────────────────────────┘ │
│                                          │
│  72% confident                           │
│  ━━━━━━━━━━━━━━━━░░░░░░               │
│                                          │
│  Select a match:                         │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │ ① PP Rope 24mm                     │ │
│  │    IMPA 210455           78%       │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │ ② Nylon Rope 24mm                  │ │
│  │    IMPA 210456           65%       │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │ ③ Polyester Rope 24mm              │ │
│  │    IMPA 210457           62%       │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐ │
│  │ + None of these                    │ │
│  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘ │
│                                          │
├─────────────────────────────────────────┤
│                                          │
│     [Skip]              🎤              │
│                                          │
│   "Say 'one', 'two', or 'three'"        │
│                                          │
└─────────────────────────────────────────┘
```

### Review Metrics Dashboard (For Managers)

```tsx
// components/review/ReviewMetricsDashboard.tsx
interface ReviewMetricsProps {
  period: 'today' | 'week' | 'month';
}

export function ReviewMetricsDashboard({ period }: ReviewMetricsProps) {
  const metrics = useReviewMetrics(period);

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <MetricCard
        title="Items Reviewed"
        value={metrics.totalReviewed}
        trend={metrics.reviewedTrend}
      />
      <MetricCard
        title="Avg. Review Time"
        value={`${metrics.avgReviewTimeSeconds}s`}
        trend={metrics.timeTrend}
      />
      <MetricCard
        title="Accuracy Rate"
        value={`${metrics.accuracyRate}%`}
        trend={metrics.accuracyTrend}
      />
      <MetricCard
        title="SLA Compliance"
        value={`${metrics.slaCompliance}%`}
        trend={metrics.slaTrend}
      />
    </div>
  );
}
```

---

## Maritime Document Types & IMPA Matching Pipeline

*Added 2026-02-08 based on AI-native RFQ creation research*

### Document Types in Maritime Procurement

Ship captains and fleet managers handle 8 primary document types when creating RFQs. Each has different extraction characteristics:

| Document Type | Format | Expected Auto-Match Rate | Extraction Difficulty | Azure DI Model |
|---|---|---|---|---|
| System-generated requisitions (AMOS, SERTICA) | PDF/XLSX | 85-95% | Low | `prebuilt-layout` |
| Previous purchase orders | PDF/XLSX | 90-98% | Low | `prebuilt-layout` |
| Inventory/stock lists (below-threshold reports) | XLSX | 85-95% | Low | `prebuilt-layout` |
| PMS/maintenance exports | PDF/XLSX | 60-80% | Medium | `prebuilt-layout` |
| Handwritten requisition forms | Scanned PDF/Image | 40-65% | High | `prebuilt-read` |
| Marked vendor catalogs (circled/highlighted) | Scanned PDF/Image | 30-60% | High | `prebuilt-read` |
| Equipment nameplate photos | Image (JPEG/PNG) | 20-50% | Very High | `prebuilt-read` |
| Mixed typed/handwritten forms | Scanned PDF | 50-75% | High | `prebuilt-layout` |

**Model selection rationale:**
- `prebuilt-layout` — Primary workhorse. Detects tables with cell relationships (merged cells, multi-row headers), outputs Markdown format ideal for LLM consumption. Handles PDF, XLSX, DOCX natively. Cost: ~$1.50/1,000 pages.
- `prebuilt-read` — Optimized for OCR on photos and handwritten text. Better for equipment nameplates and handwritten annotations.

### Three-Stage IMPA Matching Pipeline

For each extracted line item, matching proceeds through three stages:

**Stage 1: Exact IMPA Code Detection**
```
Pattern: \b\d{6}\b (with context validation against known IMPA range)
```
If a valid 6-digit IMPA code is found in the document text, it is used directly. This handles system-generated requisitions that already contain IMPA codes. Expected hit rate: 40-60% of items in digital requisitions.

**Stage 2: pgvector Semantic Search**
For items without explicit IMPA codes, the normalized item description is embedded and nearest-neighbor searched:
```sql
SELECT id, impa_code, name, 1 - (embedding <=> query_embedding) AS similarity
FROM products
WHERE 1 - (embedding <=> query_embedding) > 0.6
ORDER BY embedding <=> query_embedding
LIMIT 5;
```
Leverages existing pgvector infrastructure (ADR-NF-002). Product catalog embeddings are pre-computed and indexed.

**Stage 3: LLM-Assisted Disambiguation**
When pgvector returns ambiguous results (top match < 0.8 similarity, or top-3 are close), an LLM call disambiguates using maritime domain context:
- "SS" typically means Stainless Steel
- Size "M12x50" means M12 thread, 50mm length
- "Bolt" in deck context likely refers to hex bolts

The LLM returns the best match with a confidence score and reasoning. Maritime synonym expansion (Phase 0.4) aids: "SS" → "stainless steel", "bolt" → "fastener".

### Quantity and Unit Normalization

Maritime documents use inconsistent unit abbreviations. The extraction pipeline normalizes to standard units:

| Detected Variants | Normalized Unit |
|---|---|
| pcs, pce, pieces, ea, each, nos | pcs |
| kg, kgs, kilos, kilogram | kg |
| m, mtr, mtrs, meters, metres | m |
| l, ltr, ltrs, liters, litres | L |
| sets, set | set |
| rolls, roll, rls | roll |
| drums, drum, drm | drum |
| boxes, box, bx | box |
| tins, tin, cans, can | tin |
| bottles, bottle, btl | bottle |

Implicit quantities ("as required", "sufficient") are flagged as `confidence < 0.5` and routed to full review.

### Multi-Document Deduplication

When multiple documents are uploaded simultaneously for a single RFQ:

1. **Parallel processing** — Each document enters the pipeline independently
2. **Progressive display** — Line items appear in the table as each document completes
3. **Source tagging** — Each line item shows which document it came from
4. **Deduplication logic** — Same IMPA code with similar quantities across documents flagged as potential duplicate. Presented to user: "Found IMPA 530215 in both 'mv-star-req.pdf' (qty: 50) and 'maintenance-report.xlsx' (qty: 30). Merge to 80 pcs?"
5. **Per-document summary** — Extraction results shown per document before consolidated view

### Integration with RFQ Creation

Extracted items map directly to `RfqLineItemCreate` schema:

| Extracted Field | RFQ Line Item Field | Mapping Logic |
|---|---|---|
| Detected line number | `line_number` | Use detected order, or auto-increment |
| IMPA code (if in document) | `impa_code` | Direct mapping if valid 6-digit code |
| Matched IMPA product | `product_id` | UUID from product catalog lookup |
| Normalized description | `description` | LLM-cleaned description (max 500 chars) |
| Detected quantity | `quantity` | Parsed number, validated > 0 |
| Detected unit | `unit_of_measure` | Normalized per table above |
| Detected specifications | `specifications` | JSON dict of key-value pairs |
| Original text / notes | `notes` | Raw extracted text for reference |

### Backend Pipeline (Celery)

The extraction pipeline runs as chained Celery tasks:

```
Task chain:
  1. parse_document       — Calls Azure DI, stores raw extraction result
  2. normalize_line_items — LLM normalization in batches of 20 items
  3. match_sku            — 3-stage IMPA matching per item
  4. route_by_confidence  — Sorts items into auto/quick/full tiers per thresholds above
```

WebSocket/SSE events push progress to the frontend at each stage transition:
1. "Reading document structure..."
2. "Found 85 line items"
3. "Matching to IMPA catalog... 72 of 85"
4. "Done! 80 matched, 5 need review"

---

## References
- [Human-in-the-Loop ML Patterns](https://cloud.google.com/architecture/human-in-the-loop-machine-learning)
- [Confidence Calibration in ML](https://arxiv.org/abs/1706.04599)
- [Active Learning for Document Processing](https://docs.aws.amazon.com/textract/latest/dg/human-in-the-loop.html)
- [ADR-UI-013: PortiQ Buyer Experience](../ui/ADR-UI-013-portiq-buyer-experience.md)
- [ADR-UI-009: Design System (ConfidenceIndicator Component)](../ui/ADR-UI-009-design-system-theming.md)
