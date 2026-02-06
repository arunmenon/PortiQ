# ADR-NF-010: Saga Pattern for Transactions

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

Complex business operations span multiple steps that must be coordinated with appropriate compensation handling on failures.

### Business Context
Multi-step workflows requiring saga orchestration:
- **Order placement**: Payment → Inventory reservation → Supplier notification → Confirmation
- **Quote acceptance**: Validate → Create order → Split payment → Notify parties
- **Invoice financing**: Submit → Credit check → Offer selection → Disbursement
- **RFQ award**: Select winner → Create order → Notify suppliers → Update RFQ status

Each step may fail, requiring rollback of previous steps.

### Technical Context
- Modular monolith with PostgreSQL (ADR-NF-006, NF-001)
- Local database transactions available
- Medusa workflow engine for marketplace (ADR-FN-015)
- External service calls may fail
- Need visibility into long-running workflows

### Assumptions
- Local transactions sufficient for most operations
- External service failures need compensation handling
- Workflow state persistence needed for long-running operations
- Operations team needs visibility into stuck workflows

---

## Decision Drivers

- Reliable multi-step operations
- Compensation for failures
- Visibility into workflow state
- Integration with existing tools
- Developer experience
- Operational monitoring

---

## Considered Options

### Option 1: Database Transactions Only
**Description:** Wrap all operations in PostgreSQL transactions.

**Pros:**
- Simple and reliable
- ACID guarantees
- Built-in rollback

**Cons:**
- Can't include external calls
- Long transactions problematic
- No async support

### Option 2: Manual Saga Implementation
**Description:** Custom saga orchestrator with compensation logic.

**Pros:**
- Full control
- Custom to our needs
- No dependencies

**Cons:**
- Significant development effort
- Need to handle edge cases
- No built-in tooling

### Option 3: Medusa Workflows
**Description:** Use Medusa's built-in workflow engine with saga support.

**Pros:**
- Already using Medusa
- Built-in saga support
- Step compensation
- Async support
- Retry logic

**Cons:**
- Medusa-specific
- Learning curve

### Option 4: Temporal.io
**Description:** Dedicated workflow orchestration platform.

**Pros:**
- Purpose-built for workflows
- Excellent reliability
- Great debugging tools
- Language support

**Cons:**
- Additional infrastructure
- Operational overhead
- May be overkill

---

## Decision

**Chosen Option:** Medusa Workflows + Custom Saga Service

We will use Medusa's workflow engine for marketplace-related sagas and implement a custom saga service for other complex operations, following similar patterns.

### Rationale
Medusa's workflow engine already provides saga capabilities for marketplace operations (order creation, payment processing). Extending this pattern with a compatible custom saga service maintains consistency. This avoids the complexity of Temporal while providing necessary reliability.

---

## Consequences

### Positive
- Reliable multi-step operations
- Automatic compensation on failures
- Workflow visibility
- Consistent patterns across codebase

### Negative
- Two saga implementations
- **Mitigation:** Aligned patterns, shared utilities
- Learning curve for Medusa workflows
- **Mitigation:** Documentation, examples

### Risks
- Stuck workflows: Monitoring, manual intervention tools
- Compensation failures: Idempotent compensations, dead letter handling
- State inconsistency: Periodic reconciliation, alerts

---

## Implementation Notes

### Saga Definition Interface

```typescript
// sagas/interfaces/saga.interface.ts
export interface SagaStep<TInput, TOutput> {
  name: string;
  execute: (input: TInput, context: SagaContext) => Promise<TOutput>;
  compensate?: (input: TInput, context: SagaContext) => Promise<void>;
}

export interface SagaDefinition<TInput, TOutput> {
  name: string;
  steps: SagaStep<any, any>[];
  onComplete?: (result: TOutput, context: SagaContext) => Promise<void>;
  onFail?: (error: Error, context: SagaContext) => Promise<void>;
}

export interface SagaContext {
  sagaId: string;
  correlationId: string;
  startedAt: Date;
  currentStep: number;
  stepResults: Map<string, any>;
  metadata: Record<string, any>;
}

export enum SagaStatus {
  PENDING = 'PENDING',
  RUNNING = 'RUNNING',
  COMPLETED = 'COMPLETED',
  COMPENSATING = 'COMPENSATING',
  FAILED = 'FAILED',
  COMPENSATION_FAILED = 'COMPENSATION_FAILED'
}
```

### Saga State Persistence

```typescript
// sagas/entities/saga-execution.entity.ts
@Entity('saga_executions')
export class SagaExecution {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  sagaName: string;

  @Column()
  status: SagaStatus;

  @Column('jsonb')
  input: Record<string, any>;

  @Column('jsonb', { nullable: true })
  output: Record<string, any>;

  @Column()
  currentStep: number;

  @Column('jsonb')
  stepResults: Record<string, any>;

  @Column('jsonb')
  stepStatus: Record<string, 'PENDING' | 'COMPLETED' | 'FAILED' | 'COMPENSATED'>;

  @Column({ nullable: true })
  error: string;

  @Column({ nullable: true })
  correlationId: string;

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;

  @Column({ nullable: true })
  completedAt: Date;
}
```

### Saga Orchestrator

```typescript
// sagas/services/saga-orchestrator.service.ts
@Injectable()
export class SagaOrchestrator {
  private readonly logger = new Logger(SagaOrchestrator.name);

  constructor(
    @InjectRepository(SagaExecution)
    private readonly sagaRepository: Repository<SagaExecution>,
    private readonly eventEmitter: EventEmitter2
  ) {}

  async execute<TInput, TOutput>(
    definition: SagaDefinition<TInput, TOutput>,
    input: TInput,
    options: ExecuteOptions = {}
  ): Promise<SagaExecution> {
    // Create saga execution record
    const execution = await this.sagaRepository.save({
      sagaName: definition.name,
      status: SagaStatus.PENDING,
      input,
      currentStep: 0,
      stepResults: {},
      stepStatus: {},
      correlationId: options.correlationId
    });

    const context: SagaContext = {
      sagaId: execution.id,
      correlationId: options.correlationId || execution.id,
      startedAt: new Date(),
      currentStep: 0,
      stepResults: new Map(),
      metadata: options.metadata || {}
    };

    try {
      await this.sagaRepository.update(execution.id, {
        status: SagaStatus.RUNNING
      });

      let result: any = input;

      // Execute each step
      for (let i = 0; i < definition.steps.length; i++) {
        const step = definition.steps[i];
        context.currentStep = i;

        this.logger.log(`Executing step ${step.name} for saga ${execution.id}`);

        try {
          result = await step.execute(result, context);

          context.stepResults.set(step.name, result);

          await this.sagaRepository.update(execution.id, {
            currentStep: i,
            stepResults: Object.fromEntries(context.stepResults),
            stepStatus: {
              ...execution.stepStatus,
              [step.name]: 'COMPLETED'
            }
          });

        } catch (error) {
          this.logger.error(`Step ${step.name} failed: ${error.message}`);

          await this.sagaRepository.update(execution.id, {
            stepStatus: {
              ...execution.stepStatus,
              [step.name]: 'FAILED'
            },
            error: error.message
          });

          // Start compensation
          await this.compensate(execution.id, definition, context, i - 1);
          throw error;
        }
      }

      // All steps completed
      await this.sagaRepository.update(execution.id, {
        status: SagaStatus.COMPLETED,
        output: result,
        completedAt: new Date()
      });

      if (definition.onComplete) {
        await definition.onComplete(result, context);
      }

      this.eventEmitter.emit('saga.completed', {
        sagaId: execution.id,
        sagaName: definition.name,
        result
      });

      return this.sagaRepository.findOne({ where: { id: execution.id } });

    } catch (error) {
      if (definition.onFail) {
        await definition.onFail(error, context);
      }

      this.eventEmitter.emit('saga.failed', {
        sagaId: execution.id,
        sagaName: definition.name,
        error: error.message
      });

      throw error;
    }
  }

  private async compensate(
    sagaId: string,
    definition: SagaDefinition<any, any>,
    context: SagaContext,
    fromStep: number
  ): Promise<void> {
    await this.sagaRepository.update(sagaId, {
      status: SagaStatus.COMPENSATING
    });

    const execution = await this.sagaRepository.findOne({
      where: { id: sagaId }
    });

    // Compensate in reverse order
    for (let i = fromStep; i >= 0; i--) {
      const step = definition.steps[i];

      if (!step.compensate) {
        continue;
      }

      const stepResult = context.stepResults.get(step.name);

      try {
        this.logger.log(`Compensating step ${step.name}`);
        await step.compensate(stepResult, context);

        await this.sagaRepository.update(sagaId, {
          stepStatus: {
            ...execution.stepStatus,
            [step.name]: 'COMPENSATED'
          }
        });

      } catch (error) {
        this.logger.error(`Compensation for ${step.name} failed: ${error.message}`);

        await this.sagaRepository.update(sagaId, {
          status: SagaStatus.COMPENSATION_FAILED,
          error: `Compensation failed at ${step.name}: ${error.message}`
        });

        this.eventEmitter.emit('saga.compensation_failed', {
          sagaId,
          step: step.name,
          error: error.message
        });

        throw error;
      }
    }

    await this.sagaRepository.update(sagaId, {
      status: SagaStatus.FAILED
    });
  }

  async retry(sagaId: string): Promise<SagaExecution> {
    const execution = await this.sagaRepository.findOne({
      where: { id: sagaId }
    });

    if (!execution) {
      throw new NotFoundException(`Saga ${sagaId} not found`);
    }

    if (execution.status !== SagaStatus.FAILED) {
      throw new BadRequestException(`Can only retry failed sagas`);
    }

    // Re-execute from failed step
    // Implementation depends on saga definition registry
    throw new Error('Not implemented');
  }
}
```

### Order Creation Saga Example

```typescript
// orders/sagas/create-order.saga.ts
export const createOrderSaga: SagaDefinition<CreateOrderInput, Order> = {
  name: 'create-order',

  steps: [
    {
      name: 'validate-order',
      execute: async (input: CreateOrderInput, context) => {
        // Validate products exist and are available
        const validatedItems = await orderValidationService.validate(input.items);
        return { ...input, validatedItems };
      }
      // No compensation needed - validation doesn't change state
    },

    {
      name: 'reserve-inventory',
      execute: async (input, context) => {
        const reservations = await inventoryService.reserve(
          input.validatedItems,
          context.sagaId
        );
        return { ...input, reservations };
      },
      compensate: async (input, context) => {
        await inventoryService.releaseReservation(context.sagaId);
      }
    },

    {
      name: 'process-payment',
      execute: async (input, context) => {
        const payment = await paymentService.charge({
          amount: input.total,
          method: input.paymentMethod,
          orderId: context.sagaId
        });
        return { ...input, payment };
      },
      compensate: async (input, context) => {
        if (input.payment) {
          await paymentService.refund(input.payment.id);
        }
      }
    },

    {
      name: 'create-order-record',
      execute: async (input, context) => {
        const order = await orderRepository.create({
          ...input,
          paymentId: input.payment.id,
          status: 'CONFIRMED'
        });
        return order;
      },
      compensate: async (input, context) => {
        // Mark order as cancelled if partially created
        if (input.id) {
          await orderRepository.update(input.id, { status: 'CANCELLED' });
        }
      }
    },

    {
      name: 'notify-parties',
      execute: async (order, context) => {
        await notificationService.notifyOrderCreated(order);
        return order;
      }
      // Notifications are best-effort, no compensation
    }
  ],

  onComplete: async (order, context) => {
    logger.log(`Order ${order.id} created successfully`);
  },

  onFail: async (error, context) => {
    logger.error(`Order creation saga ${context.sagaId} failed: ${error.message}`);
    await alertService.notify('order-saga-failed', {
      sagaId: context.sagaId,
      error: error.message
    });
  }
};
```

### Saga Usage

```typescript
// orders/services/order.service.ts
@Injectable()
export class OrderService {
  constructor(private readonly sagaOrchestrator: SagaOrchestrator) {}

  async createOrder(dto: CreateOrderDto): Promise<Order> {
    const result = await this.sagaOrchestrator.execute(
      createOrderSaga,
      {
        items: dto.items,
        buyerOrgId: dto.buyerOrgId,
        total: dto.total,
        paymentMethod: dto.paymentMethod
      },
      {
        correlationId: dto.correlationId
      }
    );

    return result.output;
  }
}
```

### Saga Monitoring

```typescript
// sagas/controllers/saga-admin.controller.ts
@Controller('admin/sagas')
@UseGuards(AdminGuard)
export class SagaAdminController {
  constructor(
    @InjectRepository(SagaExecution)
    private readonly sagaRepository: Repository<SagaExecution>,
    private readonly sagaOrchestrator: SagaOrchestrator
  ) {}

  @Get()
  async list(
    @Query('status') status?: SagaStatus,
    @Query('name') name?: string,
    @Query('page') page = 1,
    @Query('limit') limit = 20
  ): Promise<PaginatedResponse<SagaExecution>> {
    const where: any = {};
    if (status) where.status = status;
    if (name) where.sagaName = name;

    const [items, total] = await this.sagaRepository.findAndCount({
      where,
      order: { createdAt: 'DESC' },
      skip: (page - 1) * limit,
      take: limit
    });

    return { items, total, page, limit };
  }

  @Get(':id')
  async get(@Param('id') id: string): Promise<SagaExecution> {
    return this.sagaRepository.findOneOrFail({ where: { id } });
  }

  @Post(':id/retry')
  async retry(@Param('id') id: string): Promise<SagaExecution> {
    return this.sagaOrchestrator.retry(id);
  }

  @Get('stats')
  async stats(): Promise<SagaStats> {
    const statusCounts = await this.sagaRepository
      .createQueryBuilder()
      .select('status, COUNT(*) as count')
      .groupBy('status')
      .getRawMany();

    return { statusCounts };
  }
}
```

### Dependencies
- ADR-NF-006: Modular Monolith vs Microservices
- ADR-NF-009: Event-Driven Communication
- ADR-FN-015: Marketplace Framework (Medusa workflows)

### Migration Strategy
1. Create saga execution table
2. Implement saga orchestrator
3. Define critical saga workflows
4. Add monitoring endpoints
5. Set up alerts for failed sagas
6. Create admin UI for saga management

---

## Operational Considerations

### Orchestration vs Choreography Decision

**Chosen Approach: Orchestration-First with Selective Choreography**

| Pattern | When to Use | Examples |
|---------|-------------|----------|
| **Orchestration** (Primary) | Multi-step transactions requiring strict ordering, compensation, and visibility | Order creation, quote acceptance, invoice financing |
| **Choreography** | Loosely coupled, fire-and-forget scenarios | Notifications, analytics events, cache invalidation |

**Rationale for Orchestration:**
- **Visibility:** Single point to observe workflow state and progress
- **Debugging:** Easy to trace failures to specific steps
- **Compensation:** Centralized logic for rollbacks
- **Maintainability:** Business logic in one place rather than scattered across handlers

**When Choreography is Acceptable:**
- Event handlers are idempotent and independent
- No compensation required (e.g., sending notifications)
- Failure of one handler should not affect others
- No strict ordering requirements

**Tooling Stack:**

| Tool | Purpose | Usage |
|------|---------|-------|
| Custom SagaOrchestrator | Core saga execution engine | All orchestrated workflows |
| Medusa Workflows | Marketplace-specific sagas | Cart, checkout, fulfillment |
| BullMQ | Async step execution | Long-running operations |
| PostgreSQL | Saga state persistence | saga_executions table |

### Compensation Steps by Workflow

#### Order Creation Saga

| Step | Action | Compensation | Timeout | Retry Policy |
|------|--------|--------------|---------|--------------|
| 1. Validate Order | Check product availability, pricing | None (read-only) | 5s | 3 retries |
| 2. Reserve Inventory | Lock inventory for order items | Release reservation | 10s | 3 retries |
| 3. Process Payment | Charge payment method | Refund payment | 30s | 2 retries |
| 4. Create Order Record | Persist order to database | Mark order as cancelled | 5s | 3 retries |
| 5. Notify Parties | Send notifications to buyer/supplier | None (best-effort) | 10s | No retry |

```typescript
// Compensation implementation example
const orderSagaCompensations: Record<string, CompensationStep> = {
  'reserve-inventory': {
    execute: async (context) => {
      await this.inventoryService.releaseReservation(context.sagaId);
      this.logger.log(`Released inventory reservation for saga ${context.sagaId}`);
    },
    retryPolicy: { maxAttempts: 5, backoff: 'exponential', initialDelay: 1000 },
  },
  'process-payment': {
    execute: async (context) => {
      const paymentId = context.stepResults.get('process-payment')?.paymentId;
      if (paymentId) {
        await this.paymentService.refund(paymentId, {
          reason: 'saga_compensation',
          sagaId: context.sagaId,
        });
        this.logger.log(`Refunded payment ${paymentId} for saga ${context.sagaId}`);
      }
    },
    retryPolicy: { maxAttempts: 10, backoff: 'exponential', initialDelay: 2000 },
  },
  'create-order-record': {
    execute: async (context) => {
      const orderId = context.stepResults.get('create-order-record')?.id;
      if (orderId) {
        await this.orderRepository.update(orderId, {
          status: OrderStatus.CANCELLED,
          cancelledAt: new Date(),
          cancellationReason: 'saga_compensation',
        });
      }
    },
    retryPolicy: { maxAttempts: 3, backoff: 'linear', initialDelay: 500 },
  },
};
```

#### Quote Acceptance Saga

| Step | Action | Compensation | Timeout | Retry Policy |
|------|--------|--------------|---------|--------------|
| 1. Validate Quote | Check quote validity, expiry | None (read-only) | 5s | 3 retries |
| 2. Lock Quote | Prevent concurrent acceptance | Unlock quote | 5s | 3 retries |
| 3. Create Order | Generate order from quote | Cancel order | 10s | 3 retries |
| 4. Split Payment | Handle multi-supplier payment | Reverse payment split | 30s | 2 retries |
| 5. Update RFQ Status | Mark RFQ as awarded | Revert RFQ status | 5s | 3 retries |
| 6. Notify Suppliers | Notify winner and losers | None (best-effort) | 10s | No retry |

#### Invoice Financing Saga

| Step | Action | Compensation | Timeout | Retry Policy |
|------|--------|--------------|---------|--------------|
| 1. Validate Invoice | Check invoice eligibility | None (read-only) | 5s | 3 retries |
| 2. Submit to Platform | Send to financing platform | Cancel submission | 30s | 2 retries |
| 3. Credit Assessment | Wait for credit decision | None (external) | 5 min | 1 retry |
| 4. Present Offers | Show financing offers to user | Expire offers | 24h | No retry |
| 5. Accept Offer | User accepts financing offer | Cancel acceptance | 30s | 2 retries |
| 6. Disburse Funds | Transfer funds to seller | Reverse disbursement | 60s | 1 retry |

### Observability Across Saga Steps

**Structured Logging for Each Step:**

```typescript
// Automatic logging in SagaOrchestrator
private async executeStep(
  step: SagaStep<any, any>,
  input: any,
  context: SagaContext,
): Promise<any> {
  const startTime = Date.now();

  this.logger.log({
    message: `Saga step started`,
    sagaId: context.sagaId,
    sagaName: context.sagaName,
    stepName: step.name,
    stepIndex: context.currentStep,
    correlationId: context.correlationId,
    input: this.sanitize(input), // Remove sensitive data
  });

  try {
    const result = await step.execute(input, context);
    const duration = Date.now() - startTime;

    this.logger.log({
      message: `Saga step completed`,
      sagaId: context.sagaId,
      stepName: step.name,
      duration,
      success: true,
    });

    this.metrics.recordSagaStepDuration(context.sagaName, step.name, duration);
    return result;

  } catch (error) {
    const duration = Date.now() - startTime;

    this.logger.error({
      message: `Saga step failed`,
      sagaId: context.sagaId,
      stepName: step.name,
      duration,
      error: error.message,
      stack: error.stack,
    });

    this.metrics.incrementSagaStepFailure(context.sagaName, step.name);
    throw error;
  }
}
```

**CloudWatch Metrics for Sagas:**

| Metric | Dimensions | Unit | Alert Threshold |
|--------|------------|------|-----------------|
| SagaExecutionStarted | sagaName | Count | N/A |
| SagaExecutionCompleted | sagaName | Count | N/A |
| SagaExecutionFailed | sagaName | Count | > 5 in 5 min |
| SagaCompensationTriggered | sagaName | Count | > 3 in 5 min |
| SagaCompensationFailed | sagaName | Count | > 0 (critical) |
| SagaStepDuration | sagaName, stepName | Milliseconds | p95 > timeout * 0.8 |
| SagaStuckCount | sagaName | Count | > 0 for 10 min |

**Grafana Dashboard Panels:**

1. **Saga Overview**
   - Active sagas by type (gauge)
   - Saga completion rate (time series)
   - Average saga duration by type (bar chart)

2. **Saga Health**
   - Failed sagas (time series, by type)
   - Compensation events (time series)
   - Stuck sagas (table with details)

3. **Step Performance**
   - Step duration heatmap
   - Step failure rate by saga type
   - Slowest steps ranking

**Admin API for Saga Debugging:**

```typescript
// GET /admin/sagas/:id - Full saga details
{
  "id": "saga-uuid",
  "name": "create-order",
  "status": "FAILED",
  "input": { /* sanitized input */ },
  "currentStep": 2,
  "startedAt": "2025-01-20T10:00:00Z",
  "failedAt": "2025-01-20T10:00:15Z",
  "error": "Payment processing failed: insufficient funds",
  "steps": [
    { "name": "validate-order", "status": "COMPLETED", "duration": 120, "completedAt": "..." },
    { "name": "reserve-inventory", "status": "COMPLETED", "duration": 450, "completedAt": "..." },
    { "name": "process-payment", "status": "FAILED", "duration": 5000, "error": "insufficient funds" }
  ],
  "compensations": [
    { "step": "reserve-inventory", "status": "COMPLETED", "completedAt": "..." }
  ],
  "correlationId": "req-uuid",
  "userId": "user-uuid",
  "organizationId": "org-uuid"
}
```

### Open Questions - Answered

- **Q:** How will saga state be persisted and queried for debugging?
  - **A:** Saga state is persisted in PostgreSQL using the `saga_executions` table:

    **Schema:**
    ```sql
    CREATE TABLE saga_executions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        saga_name VARCHAR(100) NOT NULL,
        status VARCHAR(30) NOT NULL,
        input JSONB NOT NULL,
        output JSONB,
        current_step INTEGER NOT NULL DEFAULT 0,
        step_results JSONB NOT NULL DEFAULT '{}',
        step_status JSONB NOT NULL DEFAULT '{}',
        error TEXT,
        correlation_id VARCHAR(100),
        user_id UUID,
        organization_id UUID,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        completed_at TIMESTAMPTZ,

        -- Indexes for common queries
        CONSTRAINT saga_executions_status_check
          CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'COMPENSATING', 'FAILED', 'COMPENSATION_FAILED'))
    );

    CREATE INDEX idx_saga_executions_status ON saga_executions (status, created_at);
    CREATE INDEX idx_saga_executions_name ON saga_executions (saga_name, status);
    CREATE INDEX idx_saga_executions_correlation ON saga_executions (correlation_id);
    CREATE INDEX idx_saga_executions_org ON saga_executions (organization_id, created_at);
    ```

    **Query Patterns:**
    - Find stuck sagas: `WHERE status IN ('RUNNING', 'COMPENSATING') AND updated_at < NOW() - INTERVAL '10 minutes'`
    - Find failed sagas for retry: `WHERE status = 'FAILED' AND created_at > NOW() - INTERVAL '24 hours'`
    - Audit trail by order: `WHERE correlation_id = ? OR input->>'orderId' = ?`
    - Debug by user: `WHERE user_id = ? ORDER BY created_at DESC LIMIT 50`

    **Retention:** Saga records are retained for 90 days in PostgreSQL, then archived to S3 for compliance (7 years).

---

## References
- [Saga Pattern](https://microservices.io/patterns/data/saga.html)
- [Medusa Workflows](https://docs.medusajs.com/development/workflows/overview)
- [Compensating Transactions](https://docs.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction)
