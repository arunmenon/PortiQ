# ADR-NF-006: Modular Monolith vs Microservices

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

The platform architecture must balance development velocity, operational simplicity, and scalability for a growing B2B marketplace.

### Business Context
As a startup platform, priorities are:
- Fast time-to-market for MVP
- Ability to iterate quickly on features
- Manageable operational complexity
- Clear path to scale when needed

Premature microservices adoption is a leading cause of B2B platform failures due to operational complexity.

### Technical Context
- NestJS as backend framework (TypeScript/Node.js)
- PostgreSQL as primary database
- Team size: small to medium
- Initial traffic: moderate, growing
- Integration complexity: multiple external services

### Assumptions
- Team can manage single deployment
- Traffic can be handled by vertical scaling initially
- Modular code structure allows future extraction
- NestJS modules provide logical separation

---

## Decision Drivers

- Development velocity
- Operational simplicity
- Team size and expertise
- Deployment complexity
- Scalability path
- Code organization and maintainability

---

## Considered Options

### Option 1: Modular Monolith
**Description:** Single deployable with well-defined NestJS modules and clear boundaries.

**Pros:**
- Simple deployment
- Easy local development
- No distributed transaction complexity
- Faster development
- Refactoring is straightforward
- Single debugging context

**Cons:**
- All components scale together
- Larger deployment artifact
- Coupling risks if boundaries not maintained

### Option 2: Microservices from Start
**Description:** Separate services per domain (catalog, orders, users, etc.).

**Pros:**
- Independent scaling
- Technology flexibility
- Team autonomy
- Fault isolation

**Cons:**
- Distributed system complexity
- Network latency overhead
- Distributed transactions
- Complex local development
- Operational overhead
- Premature optimization

### Option 3: Serverless Functions
**Description:** AWS Lambda functions per capability.

**Pros:**
- Pay per use
- Auto-scaling
- No server management

**Cons:**
- Cold start latency
- State management complexity
- Debugging challenges
- Vendor lock-in
- Cost unpredictability at scale

---

## Decision

**Chosen Option:** Modular Monolith

We will build a modular monolith using NestJS, with clear module boundaries that enable future extraction to microservices if needed.

### Rationale
A modular monolith provides the development velocity needed for a startup while maintaining clear boundaries for future decomposition. NestJS's module system naturally supports this pattern. The complexity of distributed systems is avoided until it's actually necessary, following the principle of "microservices as the destination, not the starting point."

---

## Consequences

### Positive
- Fast development and iteration
- Simple deployment and operations
- Easy debugging and testing
- No distributed transaction complexity
- Lower infrastructure costs

### Negative
- All components must scale together
- **Mitigation:** Horizontal scaling with load balancer; extract hot paths if needed
- Risk of tight coupling
- **Mitigation:** Strict module boundaries, code reviews

### Risks
- Module boundaries erode: Architectural reviews, linting rules
- Performance bottlenecks: Profiling, extract critical paths
- Deployment coupling: Feature flags, blue-green deployments

---

## Implementation Notes

### Module Structure

```
src/
├── main.ts
├── app.module.ts
├── common/                    # Shared utilities, decorators, guards
│   ├── decorators/
│   ├── guards/
│   ├── filters/
│   ├── interceptors/
│   └── pipes/
│
├── config/                    # Configuration module
│   ├── config.module.ts
│   └── configuration.ts
│
├── modules/
│   ├── auth/                  # Authentication module
│   │   ├── auth.module.ts
│   │   ├── auth.controller.ts
│   │   ├── auth.service.ts
│   │   ├── strategies/
│   │   ├── guards/
│   │   └── dto/
│   │
│   ├── users/                 # User management module
│   │   ├── users.module.ts
│   │   ├── users.controller.ts
│   │   ├── users.service.ts
│   │   ├── entities/
│   │   └── dto/
│   │
│   ├── organizations/         # Organization/tenant module
│   │   ├── organizations.module.ts
│   │   └── ...
│   │
│   ├── catalog/               # Product catalog module
│   │   ├── catalog.module.ts
│   │   ├── products/
│   │   │   ├── products.controller.ts
│   │   │   ├── products.service.ts
│   │   │   └── ...
│   │   ├── categories/
│   │   └── suppliers/
│   │
│   ├── procurement/           # RFQ and bidding module
│   │   ├── procurement.module.ts
│   │   ├── rfq/
│   │   ├── quotes/
│   │   └── auctions/
│   │
│   ├── orders/                # Order management module
│   │   ├── orders.module.ts
│   │   ├── orders/
│   │   └── fulfillment/
│   │
│   ├── document-ai/           # Document processing module
│   │   ├── document-ai.module.ts
│   │   ├── parsing/
│   │   ├── extraction/
│   │   └── matching/
│   │
│   ├── finance/               # Invoice financing module
│   │   ├── finance.module.ts
│   │   ├── invoices/
│   │   └── financing/
│   │
│   ├── maritime/              # AIS and port data module
│   │   ├── maritime.module.ts
│   │   ├── vessels/
│   │   └── ports/
│   │
│   └── notifications/         # Notifications module
│       ├── notifications.module.ts
│       ├── email/
│       ├── sms/
│       └── push/
│
└── database/                  # Database configuration
    ├── database.module.ts
    ├── migrations/
    └── seeds/
```

### Module Boundaries

```typescript
// catalog/catalog.module.ts
@Module({
  imports: [
    DatabaseModule,
    CacheModule,
    // Only import what's needed
  ],
  controllers: [
    ProductsController,
    CategoriesController
  ],
  providers: [
    ProductsService,
    CategoriesService,
    ProductRepository,
    CategoryRepository
  ],
  exports: [
    // Public API for other modules
    ProductsService,
    CategoriesService
  ]
})
export class CatalogModule {}

// procurement/procurement.module.ts
@Module({
  imports: [
    DatabaseModule,
    CacheModule,
    CatalogModule,  // Depends on catalog
    UsersModule,    // Depends on users
    EventEmitterModule.forFeature()
  ],
  controllers: [
    RfqController,
    QuotesController,
    AuctionController
  ],
  providers: [
    RfqService,
    QuotesService,
    AuctionService,
    RfqStateMachine,
    RfqRepository,
    QuoteRepository
  ],
  exports: [
    RfqService,
    QuotesService
  ]
})
export class ProcurementModule {}
```

### Inter-Module Communication

```typescript
// Option 1: Direct service injection (simple cases)
@Injectable()
export class OrdersService {
  constructor(
    private readonly productsService: ProductsService,
    private readonly usersService: UsersService
  ) {}

  async createOrder(dto: CreateOrderDto): Promise<Order> {
    // Validate products exist
    const products = await this.productsService.findByIds(dto.productIds);
    // ...
  }
}

// Option 2: Event-driven (loose coupling)
@Injectable()
export class OrdersService {
  constructor(private readonly eventEmitter: EventEmitter2) {}

  async completeOrder(orderId: string): Promise<void> {
    const order = await this.updateStatus(orderId, 'COMPLETED');

    // Emit event for other modules to react
    this.eventEmitter.emit('order.completed', {
      orderId: order.id,
      buyerOrgId: order.buyerOrgId,
      total: order.total
    });
  }
}

// In notifications module
@Injectable()
export class OrderNotificationHandler {
  @OnEvent('order.completed')
  async handleOrderCompleted(event: OrderCompletedEvent): Promise<void> {
    await this.notificationService.sendOrderConfirmation(event.orderId);
  }
}
```

### Module Interface Contract

```typescript
// catalog/interfaces/catalog-service.interface.ts
// Define interface for external consumers
export interface ICatalogService {
  findProductById(id: string): Promise<Product>;
  findProductsByIds(ids: string[]): Promise<Product[]>;
  searchProducts(query: string, filters: ProductFilters): Promise<Product[]>;
  validateProductAvailability(productId: string, quantity: number): Promise<boolean>;
}

// This interface acts as a contract - changes require coordination
// If this module were extracted to a service, the interface stays the same
```

### Avoiding Module Coupling

```typescript
// BAD: Direct database access across modules
@Injectable()
export class OrdersService {
  constructor(
    @InjectRepository(Product) // Don't inject other module's entities!
    private productRepo: Repository<Product>
  ) {}
}

// GOOD: Use exported services
@Injectable()
export class OrdersService {
  constructor(
    private readonly catalogService: CatalogService // Use the public API
  ) {}
}

// BAD: Importing internal module classes
import { ProductRepository } from '../catalog/repositories/product.repository';

// GOOD: Import from module index
import { CatalogService } from '../catalog';
```

### Scaling Strategy (When Needed)

```
Phase 1: Single Instance
└── Modular Monolith on ECS Fargate

Phase 2: Horizontal Scaling
└── Multiple Monolith instances behind ALB
└── Stateless design, Redis for session

Phase 3: Selective Extraction (if needed)
└── Extract high-traffic modules (Search, Document AI)
└── Keep core modules together
└── API Gateway for routing

Phase 4: Full Microservices (if justified)
└── Each module becomes a service
└── Event-driven communication
└── Service mesh
```

### Dependencies
- ADR-NF-007: API Design Principles
- ADR-NF-008: Async Processing (BullMQ)
- ADR-NF-009: Event-Driven Communication

### Migration Strategy
1. Set up NestJS project with module structure
2. Define module boundaries and interfaces
3. Implement core modules (auth, users, catalog)
4. Add business modules (procurement, orders)
5. Implement cross-cutting concerns (caching, events)
6. Monitor for extraction candidates

---

## Module Boundaries and Data Ownership

### Module Ownership Matrix

| Module | Owned Entities | Database Tables | External Dependencies |
|--------|----------------|-----------------|----------------------|
| **auth** | Session, Token | auth_sessions, refresh_tokens | JWT library |
| **users** | User, Role | users, roles, user_roles | - |
| **organizations** | Organization, Membership | organizations, org_members | - |
| **catalog** | Product, Category, Supplier | products, categories, suppliers | IMPA API |
| **procurement** | RFQ, Quote, Auction | rfqs, quotes, auctions, bids | - |
| **orders** | Order, LineItem, Fulfillment | orders, line_items, fulfillments | - |
| **document-ai** | Document, Extraction | documents, extractions | Azure DI, OpenAI |
| **finance** | Invoice, Payment | invoices, payments, financing | TReDS |
| **maritime** | Vessel, Port, Position | vessels, ports, positions | AIS Provider |
| **notifications** | Notification, Preference | notifications, preferences | Email/SMS providers |

### Boundary Rules

```typescript
// RULE 1: Modules own their database tables exclusively
// Only catalog module can write to products table
// Other modules read via CatalogService

// RULE 2: Cross-module communication via exported services only
@Module({
  exports: [CatalogService] // Public API
  // ProductRepository is NOT exported
})
export class CatalogModule {}

// RULE 3: Events for async, loose coupling
// procurement module emits events, orders module subscribes
@OnEvent('rfq.awarded')
handleRfqAwarded(event: RfqAwardedEvent) {}

// RULE 4: No circular dependencies
// Allowed: orders → catalog, procurement → catalog
// Not allowed: catalog → orders → catalog
```

### Coupling Prevention Checklist

- [ ] Each module has a clearly defined `index.ts` exporting only public API
- [ ] No direct entity imports across modules
- [ ] No shared mutable state between modules
- [ ] Cross-module calls go through service interfaces
- [ ] Database migrations scoped to single module
- [ ] ESLint rules enforce import boundaries

## Service Extraction Criteria

### Extraction Triggers

| Signal | Threshold | Candidate Module | Action |
|--------|-----------|------------------|--------|
| **CPU-bound operations** | >50% of request time | document-ai | Extract to separate service |
| **Different scaling needs** | 10x traffic difference | search, notifications | Consider extraction |
| **Team ownership** | Dedicated team (3+) | Any module | Evaluate extraction |
| **Release independence** | Blocked deploys >2x/month | High-change module | Extract for autonomy |
| **Technology mismatch** | Python ML requirements | prediction | Extract with different stack |

### Extraction Decision Matrix

```
                    Low Change Frequency    High Change Frequency
                    ┌──────────────────────┬──────────────────────┐
High Traffic/       │                      │                      │
Resource Usage      │  Consider Extract    │  Strong Extract      │
                    │  (Scale benefits)    │  (Scale + Autonomy)  │
                    ├──────────────────────┼──────────────────────┤
Low Traffic/        │                      │                      │
Resource Usage      │  Keep in Monolith    │  Weak Extract        │
                    │  (No benefit)        │  (Autonomy only)     │
                    └──────────────────────┴──────────────────────┘
```

### Operational Decomposition Signals

| Metric | Warning | Critical | Response |
|--------|---------|----------|----------|
| Deploy frequency blocked | >1x/week | >3x/week | Evaluate extraction |
| Module coupling score | >3 deps | >5 deps | Refactor boundaries |
| Build time | >5 min | >10 min | Split build |
| Test isolation failures | >5% flaky | >10% flaky | Isolate module tests |
| Incident blast radius | >2 modules | >4 modules | Strengthen boundaries |

### Pre-Extraction Checklist

Before extracting a module to a service:
- [ ] Module has clean interface (no leaky abstractions)
- [ ] All cross-module calls are async or can tolerate latency
- [ ] Data ownership is clear (no shared tables)
- [ ] Events defined for all cross-module state changes
- [ ] Monitoring and alerting in place for the module
- [ ] Team has distributed systems experience
- [ ] Infrastructure supports service discovery

---

## References
- [Modular Monolith Pattern](https://www.kamilgrzybek.com/design/modular-monolith-primer/)
- [NestJS Modules](https://docs.nestjs.com/modules)
- [Microservices Prerequisites](https://martinfowler.com/bliki/MicroservicePrerequisites.html)
- [Monolith First](https://martinfowler.com/bliki/MonolithFirst.html)
