# ADR-NF-009: Event-Driven Communication

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

The modular monolith requires a communication pattern for loose coupling between modules while maintaining transactional integrity.

### Business Context
Cross-module interactions occur frequently:
- Order placed → Notify supplier, Update inventory, Trigger financing eligibility
- RFQ published → Notify invited suppliers, Start deadline timer
- Document processed → Update RFQ line items, Trigger matching

Tight coupling between modules would defeat the purpose of modular architecture.

### Technical Context
- NestJS modular monolith (ADR-NF-006)
- BullMQ for async job processing (ADR-NF-008)
- PostgreSQL for data persistence
- Future potential for service extraction

### Assumptions
- In-process events sufficient for monolith
- Eventual consistency acceptable for some workflows
- Critical paths need transactional consistency
- Event patterns prepare for future service extraction

---

## Decision Drivers

- Loose coupling between modules
- Transactional consistency where needed
- Debugging and traceability
- Future microservices compatibility
- Developer experience

---

## Considered Options

### Option 1: NestJS EventEmitter2
**Description:** In-process event emitter with async support.

**Pros:**
- Simple in-process events
- Async/await support
- Wildcard listeners
- No infrastructure needed
- Synchronous option available

**Cons:**
- In-memory, not persistent
- Lost on crash
- No distributed support

### Option 2: Redis Pub/Sub
**Description:** Distributed pub/sub via Redis.

**Pros:**
- Cross-instance communication
- Already have Redis
- Simple pub/sub model

**Cons:**
- At-most-once delivery
- No persistence
- No replay capability

### Option 3: Full Event Sourcing
**Description:** Persist all events, rebuild state from events.

**Pros:**
- Complete audit trail
- Replay capability
- Temporal queries

**Cons:**
- High complexity
- Storage requirements
- CQRS often needed
- Overkill for current needs

### Option 4: Hybrid (EventEmitter + Outbox)
**Description:** In-process events with outbox pattern for critical workflows.

**Pros:**
- Simple for most cases
- Guaranteed delivery for critical events
- Prepares for extraction
- Transactional consistency

**Cons:**
- Two patterns to understand
- Outbox adds complexity

---

## Decision

**Chosen Option:** Hybrid (EventEmitter2 + Outbox Pattern)

We will use NestJS EventEmitter2 for in-process events within the monolith, with an outbox pattern for critical events requiring guaranteed delivery and transactional consistency.

### Rationale
EventEmitter2 provides simple, effective loose coupling for the majority of inter-module communication. The outbox pattern handles critical events that must be processed reliably (e.g., order creation, payment events). This hybrid approach balances simplicity with reliability.

---

## Consequences

### Positive
- Simple events for most cases
- Guaranteed delivery for critical events
- Transactional consistency with outbox
- Prepares for service extraction

### Negative
- Two patterns to understand
- **Mitigation:** Clear guidelines on when to use each
- Outbox adds processing complexity
- **Mitigation:** Generic outbox processor

### Risks
- Event loss on crash (EventEmitter): Use outbox for critical events
- Outbox processing delays: Monitor, tune processor frequency
- Event ordering issues: Include correlation IDs, idempotent handlers

---

## Implementation Notes

### EventEmitter2 Setup

```typescript
// events/events.module.ts
import { EventEmitterModule } from '@nestjs/event-emitter';

@Module({
  imports: [
    EventEmitterModule.forRoot({
      wildcard: true,
      delimiter: '.',
      newListener: false,
      removeListener: false,
      maxListeners: 20,
      verboseMemoryLeak: true,
      ignoreErrors: false
    })
  ],
  exports: [EventEmitterModule]
})
export class EventsModule {}
```

### Event Definitions

```typescript
// events/definitions/order.events.ts
export class OrderCreatedEvent {
  static readonly eventName = 'order.created';

  constructor(
    public readonly orderId: string,
    public readonly buyerOrgId: string,
    public readonly supplierOrgs: string[],
    public readonly total: number,
    public readonly timestamp: Date = new Date()
  ) {}
}

export class OrderCompletedEvent {
  static readonly eventName = 'order.completed';

  constructor(
    public readonly orderId: string,
    public readonly buyerOrgId: string,
    public readonly total: number,
    public readonly timestamp: Date = new Date()
  ) {}
}

// events/definitions/rfq.events.ts
export class RfqPublishedEvent {
  static readonly eventName = 'rfq.published';

  constructor(
    public readonly rfqId: string,
    public readonly buyerOrgId: string,
    public readonly invitedSuppliers: string[],
    public readonly biddingDeadline: Date,
    public readonly timestamp: Date = new Date()
  ) {}
}

export class QuoteSubmittedEvent {
  static readonly eventName = 'quote.submitted';

  constructor(
    public readonly quoteId: string,
    public readonly rfqId: string,
    public readonly supplierId: string,
    public readonly total: number,
    public readonly timestamp: Date = new Date()
  ) {}
}
```

### Event Publisher

```typescript
// orders/services/order.service.ts
import { EventEmitter2 } from '@nestjs/event-emitter';

@Injectable()
export class OrderService {
  constructor(
    private readonly orderRepository: OrderRepository,
    private readonly eventEmitter: EventEmitter2
  ) {}

  async createOrder(dto: CreateOrderDto): Promise<Order> {
    const order = await this.orderRepository.create(dto);

    // Emit event for other modules to react
    this.eventEmitter.emit(
      OrderCreatedEvent.eventName,
      new OrderCreatedEvent(
        order.id,
        order.buyerOrgId,
        order.vendorOrders.map(vo => vo.supplierId),
        order.total
      )
    );

    return order;
  }
}
```

### Event Handlers

```typescript
// notifications/handlers/order-notification.handler.ts
import { OnEvent } from '@nestjs/event-emitter';

@Injectable()
export class OrderNotificationHandler {
  constructor(
    private readonly notificationService: NotificationService,
    private readonly emailQueue: Queue
  ) {}

  @OnEvent(OrderCreatedEvent.eventName)
  async handleOrderCreated(event: OrderCreatedEvent): Promise<void> {
    // Send notifications to suppliers
    for (const supplierId of event.supplierOrgs) {
      await this.notificationService.send(supplierId, {
        type: 'ORDER_RECEIVED',
        data: {
          orderId: event.orderId,
          total: event.total
        }
      });
    }

    // Queue email
    await this.emailQueue.add('send-email', {
      template: 'order-confirmation',
      data: { orderId: event.orderId }
    });
  }

  @OnEvent(OrderCompletedEvent.eventName)
  async handleOrderCompleted(event: OrderCompletedEvent): Promise<void> {
    await this.notificationService.send(event.buyerOrgId, {
      type: 'ORDER_COMPLETED',
      data: { orderId: event.orderId }
    });
  }
}

// inventory/handlers/order-inventory.handler.ts
@Injectable()
export class OrderInventoryHandler {
  @OnEvent(OrderCreatedEvent.eventName)
  async handleOrderCreated(event: OrderCreatedEvent): Promise<void> {
    // Reserve inventory
    await this.inventoryService.reserveForOrder(event.orderId);
  }

  @OnEvent('order.cancelled')
  async handleOrderCancelled(event: OrderCancelledEvent): Promise<void> {
    // Release reserved inventory
    await this.inventoryService.releaseReservation(event.orderId);
  }
}
```

### Outbox Pattern for Critical Events

```typescript
// events/outbox/outbox.entity.ts
@Entity('event_outbox')
export class OutboxEvent {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  eventType: string;

  @Column('jsonb')
  payload: Record<string, any>;

  @Column()
  aggregateType: string;

  @Column()
  aggregateId: string;

  @Column({ default: 'PENDING' })
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

  @Column({ nullable: true })
  processedAt: Date;

  @Column({ default: 0 })
  attempts: number;

  @Column({ nullable: true })
  error: string;

  @CreateDateColumn()
  createdAt: Date;
}
```

### Outbox Service

```typescript
// events/outbox/outbox.service.ts
@Injectable()
export class OutboxService {
  constructor(
    @InjectRepository(OutboxEvent)
    private readonly outboxRepository: Repository<OutboxEvent>,
    private readonly dataSource: DataSource
  ) {}

  // Use within transaction to ensure atomicity
  async publishWithTransaction<T>(
    eventType: string,
    payload: T,
    aggregateType: string,
    aggregateId: string,
    manager: EntityManager
  ): Promise<OutboxEvent> {
    const event = manager.create(OutboxEvent, {
      eventType,
      payload,
      aggregateType,
      aggregateId,
      status: 'PENDING'
    });

    return manager.save(event);
  }

  // Called by processor
  async processOutbox(): Promise<void> {
    const events = await this.outboxRepository.find({
      where: {
        status: 'PENDING',
        attempts: LessThan(5)
      },
      order: { createdAt: 'ASC' },
      take: 100
    });

    for (const event of events) {
      try {
        await this.outboxRepository.update(event.id, {
          status: 'PROCESSING',
          attempts: event.attempts + 1
        });

        // Emit the event
        this.eventEmitter.emit(event.eventType, event.payload);

        await this.outboxRepository.update(event.id, {
          status: 'COMPLETED',
          processedAt: new Date()
        });

      } catch (error) {
        await this.outboxRepository.update(event.id, {
          status: 'PENDING',
          error: error.message
        });
      }
    }
  }
}
```

### Transactional Event Publishing

```typescript
// orders/services/order.service.ts
@Injectable()
export class OrderService {
  async createOrderWithOutbox(dto: CreateOrderDto): Promise<Order> {
    return this.dataSource.transaction(async (manager) => {
      // Create order within transaction
      const order = manager.create(Order, dto);
      await manager.save(order);

      // Create outbox event within same transaction
      await this.outboxService.publishWithTransaction(
        OrderCreatedEvent.eventName,
        {
          orderId: order.id,
          buyerOrgId: order.buyerOrgId,
          total: order.total
        },
        'Order',
        order.id,
        manager
      );

      return order;
    });
  }
}
```

### Outbox Processor

```typescript
// events/outbox/outbox.processor.ts
@Injectable()
export class OutboxProcessor {
  private readonly logger = new Logger(OutboxProcessor.name);

  constructor(private readonly outboxService: OutboxService) {}

  @Cron('*/5 * * * * *')  // Every 5 seconds
  async processOutbox(): Promise<void> {
    try {
      await this.outboxService.processOutbox();
    } catch (error) {
      this.logger.error('Outbox processing failed', error.stack);
    }
  }
}
```

### Event Correlation

```typescript
// events/middleware/correlation.middleware.ts
@Injectable()
export class CorrelationMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction) {
    const correlationId = req.headers['x-correlation-id'] as string
      || crypto.randomUUID();

    req['correlationId'] = correlationId;
    res.setHeader('x-correlation-id', correlationId);

    // Store in async local storage for access in events
    correlationStorage.run({ correlationId }, () => {
      next();
    });
  }
}

// Include correlation ID in events
export class OrderCreatedEvent {
  constructor(
    public readonly orderId: string,
    // ... other fields
    public readonly correlationId: string = correlationStorage.getStore()?.correlationId
  ) {}
}
```

### Dependencies
- ADR-NF-006: Modular Monolith vs Microservices
- ADR-NF-008: Async Processing (BullMQ)
- ADR-NF-001: PostgreSQL as Unified Data Store

### Migration Strategy
1. Set up EventEmitter2 module
2. Define event classes for core domains
3. Implement event handlers in consumer modules
4. Create outbox table and service
5. Identify critical events for outbox
6. Set up outbox processor
7. Add correlation tracking

---

## Operational Considerations

### Event Contract Ownership

| Event Domain | Owner Team | Schema Location | Review Process |
|--------------|------------|-----------------|----------------|
| Order Events | Order Management | `events/schemas/order/*.json` | PR review + domain owner approval |
| RFQ Events | Procurement | `events/schemas/rfq/*.json` | PR review + domain owner approval |
| Document Events | Document AI | `events/schemas/document/*.json` | PR review + domain owner approval |
| Finance Events | Finance | `events/schemas/finance/*.json` | PR review + domain owner approval |
| User Events | Identity | `events/schemas/user/*.json` | PR review + domain owner approval |

**Governance Rules:**
- Event schema changes require approval from the owning team
- Breaking changes require minimum 2-sprint deprecation period
- All events must include: `eventId`, `eventType`, `version`, `timestamp`, `correlationId`, `source`
- Consumer teams must subscribe to schema change notifications

### Schema Versioning Strategy

**Version Format:** `major.minor` (e.g., `1.0`, `1.1`, `2.0`)

| Change Type | Version Impact | Migration Required |
|-------------|----------------|-------------------|
| Add optional field | Minor bump (1.0 -> 1.1) | No |
| Add required field | Major bump (1.x -> 2.0) | Yes |
| Remove field | Major bump (1.x -> 2.0) | Yes |
| Change field type | Major bump (1.x -> 2.0) | Yes |
| Rename field | Major bump (1.x -> 2.0) | Yes |

**Schema Evolution Example:**

```typescript
// events/schemas/order/order-created.schema.ts
export const OrderCreatedSchemaV1 = {
  $schema: 'http://json-schema.org/draft-07/schema#',
  $id: 'order.created.v1',
  type: 'object',
  required: ['eventId', 'eventType', 'version', 'timestamp', 'correlationId', 'payload'],
  properties: {
    eventId: { type: 'string', format: 'uuid' },
    eventType: { const: 'order.created' },
    version: { const: '1.0' },
    timestamp: { type: 'string', format: 'date-time' },
    correlationId: { type: 'string' },
    source: { type: 'string' },
    payload: {
      type: 'object',
      required: ['orderId', 'buyerOrgId', 'total'],
      properties: {
        orderId: { type: 'string', format: 'uuid' },
        buyerOrgId: { type: 'string', format: 'uuid' },
        supplierOrgs: { type: 'array', items: { type: 'string', format: 'uuid' } },
        total: { type: 'number' },
        currency: { type: 'string', default: 'INR' }
      }
    }
  }
};

// Version registry for runtime validation
export const eventSchemas = {
  'order.created': {
    '1.0': OrderCreatedSchemaV1,
    '1.1': OrderCreatedSchemaV1_1, // Added optional 'deliveryDate' field
    '2.0': OrderCreatedSchemaV2,   // Changed 'total' to 'totalAmount'
  }
};
```

**Multi-Version Consumer Support:**

```typescript
@Injectable()
export class OrderEventHandler {
  @OnEvent('order.created')
  async handleOrderCreated(event: OrderEvent): Promise<void> {
    // Route to version-specific handler
    switch (event.version) {
      case '1.0':
      case '1.1':
        return this.handleV1(event as OrderCreatedV1);
      case '2.0':
        return this.handleV2(event as OrderCreatedV2);
      default:
        this.logger.warn(`Unknown event version: ${event.version}`);
        // Attempt to handle as latest version
        return this.handleV2(event as OrderCreatedV2);
    }
  }
}
```

### Replay Strategy

**Outbox Event Replay Process:**

| Scenario | Replay Method | Considerations |
|----------|---------------|----------------|
| Consumer failure/missed events | Query outbox by time range | Idempotent handlers required |
| New consumer onboarding | Full replay from beginning | Use snapshot + incremental |
| Data reconciliation | Selective replay by aggregate | Mark events as replay |
| Disaster recovery | Replay from backup | Point-in-time recovery |

**Replay Implementation:**

```typescript
// events/services/event-replay.service.ts
@Injectable()
export class EventReplayService {
  constructor(
    @InjectRepository(OutboxEvent)
    private readonly outboxRepository: Repository<OutboxEvent>,
    private readonly eventEmitter: EventEmitter2,
  ) {}

  async replayEvents(options: ReplayOptions): Promise<ReplayResult> {
    const query = this.outboxRepository.createQueryBuilder('event')
      .where('event.createdAt >= :startTime', { startTime: options.startTime })
      .andWhere('event.createdAt <= :endTime', { endTime: options.endTime })
      .andWhere('event.status = :status', { status: 'COMPLETED' });

    if (options.eventTypes?.length) {
      query.andWhere('event.eventType IN (:...types)', { types: options.eventTypes });
    }

    if (options.aggregateId) {
      query.andWhere('event.aggregateId = :aggregateId', { aggregateId: options.aggregateId });
    }

    const events = await query.orderBy('event.createdAt', 'ASC').getMany();

    let replayed = 0;
    let failed = 0;

    for (const event of events) {
      try {
        // Mark as replay for idempotency checks
        const replayEvent = {
          ...event.payload,
          _isReplay: true,
          _originalTimestamp: event.createdAt,
        };
        await this.eventEmitter.emitAsync(event.eventType, replayEvent);
        replayed++;
      } catch (error) {
        failed++;
        this.logger.error(`Replay failed for event ${event.id}`, error);
      }
    }

    return { total: events.length, replayed, failed };
  }
}

interface ReplayOptions {
  startTime: Date;
  endTime: Date;
  eventTypes?: string[];
  aggregateId?: string;
}
```

### Ordering and De-duplication Guarantees

**Ordering Guarantees:**

| Scope | Guarantee | Implementation |
|-------|-----------|----------------|
| Same aggregate | Strict ordering | Outbox processes per-aggregate in sequence |
| Same event type | Best-effort ordering | Single processor thread per type |
| Cross-aggregate | No ordering guarantee | Use correlation ID for related events |
| Cross-service | No ordering guarantee | Design handlers to be order-independent |

**De-duplication Strategy:**

```typescript
// events/guards/idempotency.guard.ts
@Injectable()
export class IdempotencyGuard {
  constructor(
    @InjectRepository(ProcessedEvent)
    private readonly processedEventRepo: Repository<ProcessedEvent>,
  ) {}

  async isProcessed(eventId: string, handlerName: string): Promise<boolean> {
    const key = `${eventId}:${handlerName}`;
    const existing = await this.processedEventRepo.findOne({ where: { key } });
    return !!existing;
  }

  async markProcessed(eventId: string, handlerName: string): Promise<void> {
    await this.processedEventRepo.upsert(
      { key: `${eventId}:${handlerName}`, processedAt: new Date() },
      ['key']
    );
  }
}

// Usage in handler
@OnEvent('order.created')
async handleOrderCreated(event: OrderCreatedEvent): Promise<void> {
  if (await this.idempotencyGuard.isProcessed(event.eventId, 'OrderNotificationHandler')) {
    this.logger.debug(`Event ${event.eventId} already processed, skipping`);
    return;
  }

  // Process event...

  await this.idempotencyGuard.markProcessed(event.eventId, 'OrderNotificationHandler');
}
```

**Processed Events Table:**

```sql
CREATE TABLE processed_events (
    key VARCHAR(255) PRIMARY KEY,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Auto-cleanup old entries
    CONSTRAINT processed_events_ttl CHECK (processed_at > NOW() - INTERVAL '7 days')
);

CREATE INDEX idx_processed_events_time ON processed_events (processed_at);

-- Cleanup job (runs daily)
DELETE FROM processed_events WHERE processed_at < NOW() - INTERVAL '7 days';
```

### Open Questions - Answered

- **Q:** What broker or transport is assumed, and why?
  - **A:** The hybrid approach uses two transports:

    1. **NestJS EventEmitter2 (In-Process)**: Primary transport for the modular monolith
       - **Why:** Zero latency, no infrastructure overhead, sufficient for single-process deployment
       - **Use case:** Non-critical events, UI notifications, internal module communication

    2. **PostgreSQL Outbox + Polling (Persistent)**: For guaranteed delivery of critical events
       - **Why:** Transactional consistency with database writes, no additional infrastructure (uses existing PostgreSQL), reliable replay capability
       - **Use case:** Order lifecycle events, payment events, compliance-required audit events

    **Future Consideration:** If the system evolves to microservices, the outbox can be modified to publish to AWS SQS/SNS or Apache Kafka. The event schema and handler patterns remain unchanged, only the transport layer changes.

---

## References
- [NestJS Event Emitter](https://docs.nestjs.com/techniques/events)
- [Outbox Pattern](https://microservices.io/patterns/data/transactional-outbox.html)
- [Event-Driven Architecture](https://martinfowler.com/articles/201701-event-driven.html)
