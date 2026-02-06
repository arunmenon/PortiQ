# ADR-FN-011: RFQ Workflow State Machine

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

The marketplace requires a robust Request for Quotation (RFQ) workflow to manage the complete procurement lifecycle from requisition creation to order fulfillment.

### Business Context
Maritime procurement follows a structured process: buyers submit requisitions, suppliers provide quotes, buyers evaluate and select, orders are placed and fulfilled. This process involves multiple stakeholders, time-sensitive bidding windows, and complex evaluation criteria. A well-defined state machine ensures process integrity, auditability, and consistent user experience.

### Technical Context
- NestJS backend with modular architecture (ADR-NF-006)
- PostgreSQL for state persistence (ADR-NF-001)
- Event-driven communication for state transitions (ADR-NF-009)
- Real-time notifications for stakeholders (ADR-UI-012)
- Integration with auction types (ADR-FN-012) and order lifecycle (ADR-FN-022)

### Assumptions
- RFQ states are sequential with defined transitions
- Cancellation is possible at most stages
- State transitions trigger notifications and events
- Audit trail required for compliance

---

## Decision Drivers

- Clear, predictable procurement workflow
- Support for various auction types
- Audit trail for all state changes
- Integration with notification system
- Extensibility for future workflow variations
- Error handling and recovery

---

## Considered Options

### Option 1: Simple Status Field
**Description:** Single status column with application-level validation of transitions.

**Pros:**
- Simple implementation
- Flexible status values
- Easy to query

**Cons:**
- No transition enforcement
- Complex validation logic scattered
- No built-in history
- Prone to invalid states

### Option 2: State Machine Library (XState)
**Description:** Use XState library for formal state machine with guards and actions.

**Pros:**
- Formal state machine semantics
- Visualization tools
- Guards for transition validation
- Action hooks for side effects

**Cons:**
- Additional dependency
- Learning curve
- Serialization complexity
- Overkill for straightforward workflow

### Option 3: Database-Enforced State Machine
**Description:** PostgreSQL-backed state machine with transition table and triggers.

**Pros:**
- Database-level enforcement
- Built-in audit trail
- Transaction safety
- No additional dependencies

**Cons:**
- Business logic in database
- Harder to test
- Less flexible for complex conditions

### Option 4: Custom Service with Event Sourcing
**Description:** Build custom state machine service with event-sourced history.

**Pros:**
- Full control over implementation
- Event sourcing for audit trail
- Flexible transition logic
- Domain-specific optimizations

**Cons:**
- More implementation effort
- Event store infrastructure
- Replay complexity

---

## Decision

**Chosen Option:** Custom Service with Database State and Event Log

We will implement a custom RFQ state machine service backed by PostgreSQL for current state and an event log for transition history, using TypeScript enums for type safety.

### Rationale
A custom implementation provides the right balance of control, simplicity, and auditability for our specific RFQ workflow. PostgreSQL handles state persistence reliably, while an event log captures all transitions for audit purposes. This approach avoids external dependencies while maintaining full type safety and testability.

---

## Consequences

### Positive
- Full control over workflow logic
- Type-safe state and transitions
- Complete audit trail
- Testable business logic
- No external dependencies

### Negative
- Custom implementation requires thorough testing
- **Mitigation:** Comprehensive unit and integration tests
- No visual state machine tools
- **Mitigation:** Document state diagram in ADR

### Risks
- Invalid state transitions: Strict validation, database constraints
- Lost transitions: Event log with transaction safety
- Complex conditional logic: Guard functions, clear documentation

---

## Implementation Notes

### State Diagram

```
                                    ┌─────────────┐
                                    │             │
                           ┌───────▶│  CANCELLED  │
                           │        │             │
                           │        └─────────────┘
                           │              ▲
    ┌─────────┐     ┌──────┴──────┐      │      ┌──────────────┐
    │         │     │             │      │      │              │
    │  DRAFT  ├────▶│  PUBLISHED  ├──────┼─────▶│ BIDDING_OPEN │
    │         │     │             │      │      │              │
    └─────────┘     └─────────────┘      │      └──────┬───────┘
         │                               │             │
         │                               │             ▼
         │                               │      ┌──────────────┐
         │                               │      │              │
         │                               ├─────▶│BIDDING_CLOSED│
         │                               │      │              │
         │                               │      └──────┬───────┘
         │                               │             │
         │                               │             ▼
         │                               │      ┌──────────────┐
         │                               │      │              │
         └───────────────────────────────┼─────▶│  EVALUATION  │
                                         │      │              │
                                         │      └──────┬───────┘
                                         │             │
                                         │             ▼
                                         │      ┌──────────────┐
                                         │      │              │
                                         └─────▶│   AWARDED    │
                                                │              │
                                                └──────┬───────┘
                                                       │
                                                       ▼
                                                ┌──────────────┐
                                                │              │
                                                │  COMPLETED   │
                                                │              │
                                                └──────────────┘
```

### State Definitions

```typescript
// rfq/enums/rfq-status.enum.ts
export enum RfqStatus {
  DRAFT = 'DRAFT',
  PUBLISHED = 'PUBLISHED',
  BIDDING_OPEN = 'BIDDING_OPEN',
  BIDDING_CLOSED = 'BIDDING_CLOSED',
  EVALUATION = 'EVALUATION',
  AWARDED = 'AWARDED',
  COMPLETED = 'COMPLETED',
  CANCELLED = 'CANCELLED'
}

export enum RfqTransition {
  PUBLISH = 'PUBLISH',
  OPEN_BIDDING = 'OPEN_BIDDING',
  CLOSE_BIDDING = 'CLOSE_BIDDING',
  START_EVALUATION = 'START_EVALUATION',
  AWARD = 'AWARD',
  COMPLETE = 'COMPLETE',
  CANCEL = 'CANCEL'
}

// Valid transitions map
export const VALID_TRANSITIONS: Record<RfqStatus, RfqTransition[]> = {
  [RfqStatus.DRAFT]: [RfqTransition.PUBLISH, RfqTransition.CANCEL],
  [RfqStatus.PUBLISHED]: [RfqTransition.OPEN_BIDDING, RfqTransition.CANCEL],
  [RfqStatus.BIDDING_OPEN]: [RfqTransition.CLOSE_BIDDING, RfqTransition.CANCEL],
  [RfqStatus.BIDDING_CLOSED]: [RfqTransition.START_EVALUATION, RfqTransition.CANCEL],
  [RfqStatus.EVALUATION]: [RfqTransition.AWARD, RfqTransition.CANCEL],
  [RfqStatus.AWARDED]: [RfqTransition.COMPLETE, RfqTransition.CANCEL],
  [RfqStatus.COMPLETED]: [],
  [RfqStatus.CANCELLED]: []
};

// Transition result states
export const TRANSITION_TARGETS: Record<RfqTransition, RfqStatus> = {
  [RfqTransition.PUBLISH]: RfqStatus.PUBLISHED,
  [RfqTransition.OPEN_BIDDING]: RfqStatus.BIDDING_OPEN,
  [RfqTransition.CLOSE_BIDDING]: RfqStatus.BIDDING_CLOSED,
  [RfqTransition.START_EVALUATION]: RfqStatus.EVALUATION,
  [RfqTransition.AWARD]: RfqStatus.AWARDED,
  [RfqTransition.COMPLETE]: RfqStatus.COMPLETED,
  [RfqTransition.CANCEL]: RfqStatus.CANCELLED
};
```

### State Machine Service

```typescript
// rfq/services/rfq-state-machine.service.ts
@Injectable()
export class RfqStateMachineService {
  constructor(
    private readonly rfqRepository: RfqRepository,
    private readonly eventEmitter: EventEmitter2,
    private readonly transitionLogRepository: TransitionLogRepository
  ) {}

  async transition(
    rfqId: string,
    transition: RfqTransition,
    userId: string,
    metadata?: Record<string, any>
  ): Promise<Rfq> {
    const rfq = await this.rfqRepository.findById(rfqId);

    if (!rfq) {
      throw new NotFoundException(`RFQ ${rfqId} not found`);
    }

    // Validate transition is allowed
    this.validateTransition(rfq, transition);

    // Execute guard conditions
    await this.executeGuards(rfq, transition, metadata);

    const previousStatus = rfq.status;
    const newStatus = TRANSITION_TARGETS[transition];

    // Perform transition in transaction
    const updatedRfq = await this.rfqRepository.transaction(async (tx) => {
      // Update RFQ status
      const updated = await tx.rfq.update({
        where: { id: rfqId },
        data: {
          status: newStatus,
          updatedAt: new Date(),
          ...(this.getStatusSpecificUpdates(transition, metadata))
        }
      });

      // Log transition
      await tx.transitionLog.create({
        data: {
          rfqId,
          fromStatus: previousStatus,
          toStatus: newStatus,
          transition,
          userId,
          metadata: metadata ?? {},
          timestamp: new Date()
        }
      });

      return updated;
    });

    // Emit event for side effects
    this.eventEmitter.emit(`rfq.${transition.toLowerCase()}`, {
      rfq: updatedRfq,
      previousStatus,
      userId,
      metadata
    });

    return updatedRfq;
  }

  private validateTransition(rfq: Rfq, transition: RfqTransition): void {
    const allowedTransitions = VALID_TRANSITIONS[rfq.status];

    if (!allowedTransitions.includes(transition)) {
      throw new BadRequestException(
        `Transition ${transition} not allowed from status ${rfq.status}`
      );
    }
  }

  private async executeGuards(
    rfq: Rfq,
    transition: RfqTransition,
    metadata?: Record<string, any>
  ): Promise<void> {
    const guards = this.getGuards(transition);

    for (const guard of guards) {
      const result = await guard(rfq, metadata);
      if (!result.allowed) {
        throw new BadRequestException(result.reason);
      }
    }
  }

  private getGuards(transition: RfqTransition): GuardFunction[] {
    const guards: Record<RfqTransition, GuardFunction[]> = {
      [RfqTransition.PUBLISH]: [
        this.hasLineItems,
        this.hasValidDeadline
      ],
      [RfqTransition.OPEN_BIDDING]: [
        this.hasInvitedSuppliers
      ],
      [RfqTransition.CLOSE_BIDDING]: [
        this.biddingDeadlinePassed
      ],
      [RfqTransition.AWARD]: [
        this.hasSelectedQuote
      ],
      [RfqTransition.COMPLETE]: [
        this.allOrdersFulfilled
      ],
      [RfqTransition.CANCEL]: [],
      [RfqTransition.START_EVALUATION]: []
    };

    return guards[transition] ?? [];
  }

  // Guard implementations
  private hasLineItems: GuardFunction = async (rfq) => ({
    allowed: rfq.lineItems?.length > 0,
    reason: 'RFQ must have at least one line item'
  });

  private hasValidDeadline: GuardFunction = async (rfq) => ({
    allowed: rfq.biddingDeadline > new Date(),
    reason: 'Bidding deadline must be in the future'
  });

  private hasInvitedSuppliers: GuardFunction = async (rfq) => ({
    allowed: rfq.invitedSuppliers?.length > 0,
    reason: 'At least one supplier must be invited'
  });

  private hasSelectedQuote: GuardFunction = async (rfq, metadata) => ({
    allowed: !!metadata?.selectedQuoteId,
    reason: 'A quote must be selected for award'
  });
}

type GuardFunction = (
  rfq: Rfq,
  metadata?: Record<string, any>
) => Promise<{ allowed: boolean; reason?: string }>;
```

### Database Schema

```sql
-- RFQ table
CREATE TABLE rfqs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reference_number VARCHAR(50) UNIQUE NOT NULL,
    buyer_org_id UUID REFERENCES organizations(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',

    -- Bidding configuration
    auction_type VARCHAR(20) NOT NULL DEFAULT 'SEALED_BID',
    bidding_start TIMESTAMPTZ,
    bidding_deadline TIMESTAMPTZ,

    -- Award info
    awarded_quote_id UUID REFERENCES quotes(id),
    awarded_at TIMESTAMPTZ,

    -- Audit
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_status CHECK (status IN (
        'DRAFT', 'PUBLISHED', 'BIDDING_OPEN', 'BIDDING_CLOSED',
        'EVALUATION', 'AWARDED', 'COMPLETED', 'CANCELLED'
    ))
);

-- Transition log for audit trail
CREATE TABLE rfq_transitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rfq_id UUID REFERENCES rfqs(id),
    from_status VARCHAR(20) NOT NULL,
    to_status VARCHAR(20) NOT NULL,
    transition VARCHAR(30) NOT NULL,
    user_id UUID REFERENCES users(id),
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rfq_transitions_rfq ON rfq_transitions(rfq_id);
CREATE INDEX idx_rfq_transitions_timestamp ON rfq_transitions(timestamp);
```

### Event Handlers

```typescript
// rfq/handlers/rfq-transition.handler.ts
@Injectable()
export class RfqTransitionHandler {
  constructor(
    private readonly notificationService: NotificationService,
    private readonly emailService: EmailService
  ) {}

  @OnEvent('rfq.publish')
  async handlePublish(event: RfqTransitionEvent): Promise<void> {
    // Notify invited suppliers
    await this.notificationService.notifySuppliers(
      event.rfq.invitedSuppliers,
      {
        type: 'RFQ_PUBLISHED',
        rfqId: event.rfq.id,
        title: event.rfq.title,
        deadline: event.rfq.biddingDeadline
      }
    );
  }

  @OnEvent('rfq.close_bidding')
  async handleBiddingClosed(event: RfqTransitionEvent): Promise<void> {
    // Notify buyer that bidding is closed
    await this.notificationService.notifyUser(
      event.rfq.createdBy,
      {
        type: 'BIDDING_CLOSED',
        rfqId: event.rfq.id,
        quotesReceived: event.metadata?.quotesCount
      }
    );
  }

  @OnEvent('rfq.award')
  async handleAward(event: RfqTransitionEvent): Promise<void> {
    // Notify winning supplier
    await this.notificationService.notifySupplier(
      event.metadata.winningSupplier,
      {
        type: 'QUOTE_AWARDED',
        rfqId: event.rfq.id,
        quoteId: event.metadata.selectedQuoteId
      }
    );

    // Notify other suppliers
    await this.notificationService.notifySuppliers(
      event.rfq.invitedSuppliers.filter(
        s => s.id !== event.metadata.winningSupplier
      ),
      {
        type: 'QUOTE_NOT_SELECTED',
        rfqId: event.rfq.id
      }
    );
  }
}
```

### Dependencies
- ADR-FN-012: Auction Types
- ADR-FN-013: Quote Comparison & TCO Engine
- ADR-FN-022: Order Lifecycle & Fulfillment
- ADR-NF-001: PostgreSQL as Unified Data Store
- ADR-NF-009: Event-Driven Communication

### Migration Strategy
1. Create RFQ and transition log tables
2. Implement state machine service with guards
3. Add event handlers for notifications
4. Create admin API for manual state corrections
5. Build status timeline UI component
6. Implement automated transitions (deadline-based)

---

## Operational Considerations

### Edge Cases and Transition Handling

#### Cancellation Scenarios

| Scenario | Current State | Action | Target State | Side Effects |
|----------|---------------|--------|--------------|--------------|
| Buyer cancels before publishing | DRAFT | CANCEL | CANCELLED | Notify creator, archive |
| Buyer cancels after publishing | PUBLISHED | CANCEL | CANCELLED | Notify invited suppliers, archive |
| Buyer cancels during bidding | BIDDING_OPEN | CANCEL | CANCELLED | Notify all bidders, archive quotes |
| Buyer cancels during evaluation | EVALUATION | CANCEL | CANCELLED | Notify all bidders, reason required |
| Buyer cancels after award | AWARDED | CANCEL | CANCELLED | Notify winner, compensation review |
| System cancels (deadline missed) | Any | AUTO_CANCEL | CANCELLED | Notify all parties, log reason |

```typescript
// Cancellation handler with compensation logic
interface CancellationRequest {
  rfqId: string;
  requestedBy: string;
  reason: CancellationReason;
  compensationOffered?: number;
  notificationTemplate: string;
}

type CancellationReason =
  | 'buyer_changed_requirements'
  | 'budget_withdrawn'
  | 'vessel_schedule_changed'
  | 'duplicate_rfq'
  | 'supplier_issue'
  | 'system_policy';

// Post-award cancellation requires special handling
async function handlePostAwardCancellation(
  rfq: Rfq,
  request: CancellationRequest
): Promise<CancellationResult> {
  const awardedQuote = await quoteRepository.findById(rfq.awardedQuoteId);

  // Check if supplier has incurred costs
  const supplierCosts = await calculateSupplierCosts(awardedQuote);

  if (supplierCosts.totalCost > 0) {
    // Offer compensation or require acknowledgment
    return {
      status: 'pending_compensation',
      supplierCosts,
      recommendedCompensation: supplierCosts.totalCost * 0.1, // 10% of order value
      requiresSupplierAcknowledgment: true
    };
  }

  return { status: 'approved', compensationRequired: false };
}
```

#### Partial Quote Handling

| Scenario | Handling | Evaluation Impact |
|----------|----------|-------------------|
| Supplier quotes subset of line items | Accept with `partial: true` flag | Excluded from "complete quote" comparisons |
| Supplier quotes 0 quantity for some items | Treat as unavailable for those items | Line-item comparison only |
| Multiple suppliers complete different parts | Enable split-award evaluation | TCO engine calculates optimal split |
| No supplier quotes all items | Alert buyer, extend deadline or proceed with split | Require explicit buyer decision |

```typescript
// Partial quote validation
interface QuoteValidation {
  quoteId: string;
  rfqId: string;
  isComplete: boolean;
  coverage: {
    totalLineItems: number;
    quotedLineItems: number;
    coveragePercentage: number;
  };
  missingItems: {
    lineItemId: string;
    productName: string;
    reason?: 'out_of_stock' | 'not_carried' | 'lead_time_exceeded';
  }[];
  splitAwardEligible: boolean;
}

// Guard for award transition with partial quotes
const validateAwardWithPartialQuotes: GuardFunction = async (rfq, metadata) => {
  const selectedQuote = await quoteRepository.findById(metadata.selectedQuoteId);
  const validation = await validateQuoteCoverage(selectedQuote, rfq);

  if (!validation.isComplete) {
    // Check if split award or explicit acknowledgment
    if (!metadata.acknowledgePartialAward && !metadata.splitAwardPlan) {
      return {
        allowed: false,
        reason: `Selected quote covers only ${validation.coverage.coveragePercentage}% of line items. ` +
                `Acknowledge partial award or provide split award plan.`
      };
    }
  }

  return { allowed: true };
};
```

#### Supplier Drop-Off Scenarios

| Scenario | Detection | Handling |
|----------|-----------|----------|
| Invited supplier doesn't bid | Bidding deadline | Mark as "declined", exclude from future similar RFQs |
| Supplier withdraws quote | Explicit action | Archive quote, notify buyer, adjust rankings |
| Awarded supplier defaults | Post-award | Trigger backup award process, performance penalty |
| Supplier account suspended | System event | Invalidate active quotes, notify affected buyers |

```typescript
// Supplier drop-off event handling
@OnEvent('supplier.quote.withdrawn')
async handleQuoteWithdrawal(event: QuoteWithdrawnEvent): Promise<void> {
  const { quoteId, rfqId, supplierId, reason } = event;

  // Archive the quote
  await quoteRepository.update(quoteId, {
    status: 'WITHDRAWN',
    withdrawnAt: new Date(),
    withdrawalReason: reason
  });

  // Recalculate rankings if in evaluation
  const rfq = await rfqRepository.findById(rfqId);
  if (rfq.status === RfqStatus.EVALUATION) {
    await tcoEngine.recalculateRankings(rfqId);
    await notificationService.notifyBuyer(rfq.createdBy, {
      type: 'QUOTE_WITHDRAWN',
      rfqId,
      supplierName: event.supplierName,
      rankingsUpdated: true
    });
  }

  // Track for supplier performance metrics
  await supplierMetrics.recordWithdrawal(supplierId, rfqId, reason);
}

// Awarded supplier default handling
@OnEvent('supplier.award.defaulted')
async handleAwardDefault(event: AwardDefaultEvent): Promise<void> {
  const { rfqId, originalQuoteId, reason } = event;

  // Get next best quote
  const rankings = await tcoEngine.getRankings(rfqId);
  const backupQuote = rankings.find(r => r.quoteId !== originalQuoteId);

  if (backupQuote) {
    // Offer to backup supplier
    await notificationService.notifySupplier(backupQuote.supplierId, {
      type: 'BACKUP_AWARD_OFFER',
      rfqId,
      originalPrice: backupQuote.quote.totalAmount,
      responseDeadline: addHours(new Date(), 24)
    });

    await rfqRepository.update(rfqId, {
      status: RfqStatus.EVALUATION, // Revert to evaluation
      awardedQuoteId: null,
      backupAwardOfferedTo: backupQuote.quoteId,
      backupAwardDeadline: addHours(new Date(), 24)
    });
  } else {
    // No backup available
    await notificationService.notifyBuyer(rfq.createdBy, {
      type: 'AWARD_DEFAULTED_NO_BACKUP',
      rfqId,
      options: ['extend_and_republish', 'cancel']
    });
  }

  // Apply supplier penalty
  await supplierService.applyPerformancePenalty(event.supplierId, {
    type: 'award_default',
    severity: 'high',
    rfqId
  });
}
```

### Event Contracts for Integrations

#### RFQ State Change Events

```typescript
// Base event structure
interface RfqStateChangeEvent {
  eventId: string;
  eventType: string;
  timestamp: Date;
  version: '1.0';
  source: 'rfq-service';
  rfqId: string;
  previousState: RfqStatus;
  newState: RfqStatus;
  triggeredBy: {
    type: 'user' | 'system' | 'scheduler';
    id: string;
  };
  metadata: Record<string, any>;
}

// Event type definitions
type RfqEventType =
  | 'rfq.created'
  | 'rfq.published'
  | 'rfq.bidding_opened'
  | 'rfq.bidding_closed'
  | 'rfq.evaluation_started'
  | 'rfq.awarded'
  | 'rfq.completed'
  | 'rfq.cancelled';

// Event payloads by type
interface RfqPublishedEvent extends RfqStateChangeEvent {
  eventType: 'rfq.published';
  payload: {
    rfqReference: string;
    title: string;
    buyerOrganizationId: string;
    biddingDeadline: Date;
    invitedSupplierIds: string[];
    lineItemCount: number;
    estimatedValue?: number;
    visibility: 'PRIVATE' | 'PUBLIC';
  };
}

interface RfqAwardedEvent extends RfqStateChangeEvent {
  eventType: 'rfq.awarded';
  payload: {
    rfqReference: string;
    awardedQuoteId: string;
    awardedSupplierId: string;
    totalAmount: number;
    currency: string;
    lineItems: {
      lineItemId: string;
      productId: string;
      quantity: number;
      unitPrice: number;
    }[];
    expectedDeliveryDate: Date;
    paymentTerms: string;
  };
}

interface RfqCancelledEvent extends RfqStateChangeEvent {
  eventType: 'rfq.cancelled';
  payload: {
    rfqReference: string;
    cancellationReason: CancellationReason;
    affectedSupplierIds: string[];
    quotesArchived: number;
    compensationOffered?: number;
  };
}
```

#### Integration Consumers

| Consumer | Events Subscribed | Purpose |
|----------|-------------------|---------|
| Notification Service | All state changes | User notifications |
| Order Service | `rfq.awarded` | Create order from awarded quote |
| Analytics Service | All events | Metrics and reporting |
| Supplier Portal | `rfq.published`, `rfq.cancelled` | Dashboard updates |
| Finance Service | `rfq.awarded`, `rfq.completed` | Revenue recognition |
| Search Service | `rfq.published`, `rfq.cancelled` | Index updates |

#### Event Delivery Guarantees

| Guarantee | Implementation |
|-----------|---------------|
| At-least-once delivery | BullMQ with retry |
| Ordering | Per-RFQ ordering via consistent hashing |
| Idempotency | Event ID + consumer-side deduplication |
| Dead letter | Failed events to DLQ after 5 retries |
| Replay | Event store supports replay by time range |

```typescript
// Event publishing with guarantees
@Injectable()
export class RfqEventPublisher {
  constructor(
    @InjectQueue('rfq-events') private eventQueue: Queue,
    private eventStore: EventStoreService
  ) {}

  async publishStateChange(event: RfqStateChangeEvent): Promise<void> {
    // Persist to event store first (for replay)
    await this.eventStore.append(event);

    // Publish to queue for consumers
    await this.eventQueue.add(event.eventType, event, {
      jobId: event.eventId, // Enables idempotency
      attempts: 5,
      backoff: {
        type: 'exponential',
        delay: 1000
      },
      removeOnComplete: { age: 86400 }, // Keep 24 hours
      removeOnFail: false // Keep failed for inspection
    });
  }
}

// Consumer-side idempotency
@Processor('rfq-events')
export class NotificationEventProcessor {
  private processedEvents = new Set<string>();

  @Process('rfq.published')
  async handlePublished(job: Job<RfqPublishedEvent>): Promise<void> {
    // Idempotency check
    if (this.processedEvents.has(job.data.eventId)) {
      return; // Already processed
    }

    // Process event
    await this.notificationService.notifySuppliers(
      job.data.payload.invitedSupplierIds,
      { type: 'NEW_RFQ', ...job.data.payload }
    );

    // Mark as processed
    this.processedEvents.add(job.data.eventId);
    await this.persistProcessedEventId(job.data.eventId);
  }
}
```

### State Timeouts and Escalation Rules

#### Timeout Configuration by State

| State | Default Timeout | Extension Allowed | Max Extensions | Auto-Action |
|-------|-----------------|-------------------|----------------|-------------|
| DRAFT | 30 days | N/A | N/A | Archive |
| PUBLISHED | 7 days | Yes (7 days) | 2 | Close bidding |
| BIDDING_OPEN | Per RFQ config | Yes (24-72 hrs) | 3 | Close bidding |
| BIDDING_CLOSED | 24 hours | No | 0 | Start evaluation |
| EVALUATION | 7 days | Yes (3 days) | 2 | Escalate |
| AWARDED | 14 days | Yes (7 days) | 1 | Escalate to complete or cancel |

```typescript
// Timeout configuration
interface StateTimeoutConfig {
  state: RfqStatus;
  defaultTimeout: Duration;
  extensionAllowed: boolean;
  maxExtensions: number;
  extensionDuration?: Duration;
  autoAction: TimeoutAction;
  escalationPath?: EscalationLevel[];
}

type TimeoutAction =
  | { type: 'transition'; targetState: RfqStatus }
  | { type: 'escalate'; level: EscalationLevel }
  | { type: 'archive' }
  | { type: 'notify_and_wait'; notifyRole: string; additionalWait: Duration };

const STATE_TIMEOUTS: Record<RfqStatus, StateTimeoutConfig> = {
  [RfqStatus.DRAFT]: {
    state: RfqStatus.DRAFT,
    defaultTimeout: { days: 30 },
    extensionAllowed: false,
    maxExtensions: 0,
    autoAction: { type: 'archive' }
  },
  [RfqStatus.EVALUATION]: {
    state: RfqStatus.EVALUATION,
    defaultTimeout: { days: 7 },
    extensionAllowed: true,
    maxExtensions: 2,
    extensionDuration: { days: 3 },
    autoAction: { type: 'escalate', level: 'procurement_manager' },
    escalationPath: [
      { level: 'procurement_manager', afterTimeout: { days: 7 } },
      { level: 'procurement_director', afterTimeout: { days: 10 } },
      { level: 'auto_cancel', afterTimeout: { days: 14 } }
    ]
  }
};
```

#### Escalation Rules

| Escalation Level | Triggered By | Notification | Authority |
|------------------|--------------|--------------|-----------|
| L1: Owner Reminder | 50% timeout elapsed | Email + In-app | None |
| L2: Team Lead Alert | 75% timeout elapsed | Email + SMS | Extend or reassign |
| L3: Manager Escalation | Timeout elapsed | Email + SMS + Dashboard | Force decision |
| L4: Director Override | L3 + 3 days | All channels | Cancel or auto-award |

```typescript
// Escalation handler
@Cron('*/15 * * * *') // Every 15 minutes
async checkTimeoutsAndEscalate(): Promise<void> {
  const rfqsNearingTimeout = await rfqRepository.findNearingTimeout();

  for (const rfq of rfqsNearingTimeout) {
    const config = STATE_TIMEOUTS[rfq.status];
    const elapsed = Date.now() - rfq.statusChangedAt.getTime();
    const timeoutMs = durationToMs(config.defaultTimeout);

    if (elapsed >= timeoutMs) {
      // Timeout reached - execute auto-action
      await this.executeTimeoutAction(rfq, config.autoAction);
    } else if (elapsed >= timeoutMs * 0.75) {
      // 75% - L2 escalation
      await this.escalate(rfq, 'L2', {
        reason: 'approaching_timeout',
        timeRemaining: timeoutMs - elapsed
      });
    } else if (elapsed >= timeoutMs * 0.5) {
      // 50% - L1 reminder
      await this.sendReminder(rfq, 'L1');
    }
  }
}

async escalate(rfq: Rfq, level: string, context: EscalationContext): Promise<void> {
  // Record escalation
  await escalationRepository.create({
    rfqId: rfq.id,
    level,
    context,
    escalatedAt: new Date()
  });

  // Notify appropriate parties
  const escalationConfig = ESCALATION_CONFIG[level];
  await notificationService.sendEscalation(
    escalationConfig.notifyRoles,
    {
      rfqId: rfq.id,
      rfqReference: rfq.referenceNumber,
      currentState: rfq.status,
      ...context
    }
  );

  // Update RFQ with escalation status
  await rfqRepository.update(rfq.id, {
    escalationLevel: level,
    lastEscalatedAt: new Date()
  });
}
```

### Open Questions - Resolved

- **Q:** Are escalation rules and timeouts per state explicitly defined?
  - **A:** Yes, each state has explicit timeout and escalation configurations:

    **Timeout Defaults:**
    - DRAFT: 30 days until archive
    - PUBLISHED: 7 days until bidding opens (or auto-close)
    - BIDDING_OPEN: Configured per RFQ (typically 3-7 days)
    - BIDDING_CLOSED: 24 hours automatic transition to EVALUATION
    - EVALUATION: 7 days with escalation path
    - AWARDED: 14 days to complete or escalate

    **Escalation Path (EVALUATION state example):**
    1. Day 3.5 (50%): L1 reminder to RFQ owner
    2. Day 5.25 (75%): L2 alert to team lead with extend/reassign options
    3. Day 7 (100%): L3 escalation to procurement manager
    4. Day 10: L4 escalation to director with auto-cancel warning
    5. Day 14: Auto-cancel with buyer notification

    Extensions are allowed for most states with limits (typically 2-3 extensions). Extension requests are logged and require justification. Auto-actions are executed via scheduled jobs running every 15 minutes.

---

## References
- [OroCommerce RFQ Management](https://doc.oroinc.com/user/back-office/sales/rfq/)
- [State Machine Patterns](https://martinfowler.com/eaaDev/State.html)
- [Event-Driven Architecture](https://docs.nestjs.com/techniques/events)
