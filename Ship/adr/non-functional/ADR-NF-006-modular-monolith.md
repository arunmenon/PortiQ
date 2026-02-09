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
- FastAPI as backend framework (Python/asyncio)
- SQLAlchemy 2.0 as ORM with async support
- PostgreSQL as primary database
- Team size: small to medium
- Initial traffic: moderate, growing
- Integration complexity: multiple external services

### Assumptions
- Team can manage single deployment
- Traffic can be handled by vertical scaling initially
- Modular code structure allows future extraction
- Python package/module system provides logical separation

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
**Description:** Single deployable with well-defined Python modules and clear boundaries.

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

We will build a modular monolith using FastAPI with Python package modules, with clear module boundaries that enable future extraction to microservices if needed.

### Rationale
A modular monolith provides the development velocity needed for a startup while maintaining clear boundaries for future decomposition. FastAPI's router system and Python's package structure naturally support this pattern. The complexity of distributed systems is avoided until it's actually necessary, following the principle of "microservices as the destination, not the starting point."

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
├── app.py                     # FastAPI app factory, lifespan, middleware
├── config.py                  # Pydantic Settings for environment
├── database/                  # Database configuration
│   ├── __init__.py
│   ├── engine.py              # Async SQLAlchemy engine & session
│   ├── base.py                # DeclarativeBase with common columns
│   ├── session.py             # get_db dependency
│   └── tenant.py              # Tenant context (set_config)
│
├── models/                    # SQLAlchemy models (shared, single source of truth)
│   ├── __init__.py
│   ├── enums.py
│   ├── organization.py
│   ├── user.py
│   ├── category.py
│   ├── product.py
│   └── ...
│
├── modules/
│   ├── auth/                  # Authentication module
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── schemas.py
│   │   └── dependencies.py
│   │
│   ├── users/                 # User management module
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── service.py
│   │   └── schemas.py
│   │
│   ├── catalog/               # Product catalog module
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── service.py
│   │   └── schemas.py
│   │
│   ├── search/                # Vector search module
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── embedding.py
│   │   ├── reranking.py
│   │   └── tasks.py           # Celery tasks
│   │
│   ├── tenancy/               # Multi-tenant RLS module
│   │   ├── __init__.py
│   │   ├── middleware.py
│   │   ├── dependencies.py
│   │   ├── service.py
│   │   └── admin.py
│   │
│   ├── procurement/           # RFQ and bidding module
│   ├── orders/                # Order management module
│   ├── document_ai/           # Document processing module
│   ├── finance/               # Invoice financing module
│   ├── maritime/              # AIS and port data module
│   └── notifications/         # Notifications module
│
├── seed.py                    # Database seeder
celery_app.py                  # Celery configuration
alembic/                       # Alembic migrations
tests/                         # pytest test suite
```

### Module Boundaries

```python
# src/modules/catalog/__init__.py
# Public API for other modules — import only from here
from .service import CatalogService, CategoryService

# src/modules/catalog/router.py
from fastapi import APIRouter, Depends
from src.database.session import get_db

router = APIRouter(prefix="/api/v1/products", tags=["Products"])

@router.get("/")
async def list_products(db=Depends(get_db)):
    ...

# src/app.py — Register module routers
from src.modules.catalog.router import router as catalog_router
from src.modules.search.router import router as search_router

app.include_router(catalog_router)
app.include_router(search_router)
```

### Inter-Module Communication

```python
# Option 1: Direct service import (simple cases)
# src/modules/orders/service.py
from src.modules.catalog import CatalogService

class OrdersService:
    def __init__(self, db: AsyncSession, catalog: CatalogService):
        self.db = db
        self.catalog = catalog

    async def create_order(self, dto):
        products = await self.catalog.find_by_ids(dto.product_ids)
        ...

# Option 2: Event-driven via Celery (loose coupling)
# src/modules/orders/service.py
from src.modules.notifications.tasks import send_order_confirmation

class OrdersService:
    async def complete_order(self, order_id: str):
        order = await self._update_status(order_id, "COMPLETED")
        # Dispatch async task for other modules
        send_order_confirmation.delay(order.id)
```

### Module Interface Contract

```python
# src/modules/catalog/__init__.py
# Define public API for external consumers via __init__.py exports
# This acts as a contract — changes require coordination
# If this module were extracted to a service, the interface stays the same

from .service import CatalogService  # noqa: F401

# Protocol for type safety (optional, for strict typing)
from typing import Protocol

class ICatalogService(Protocol):
    async def find_product_by_id(self, product_id: str) -> Product: ...
    async def find_products_by_ids(self, ids: list[str]) -> list[Product]: ...
    async def search_products(self, query: str, filters: dict) -> list[Product]: ...
```

### Avoiding Module Coupling

```python
# BAD: Direct model query across modules
from src.models.product import Product
result = await db.execute(select(Product))  # Don't query other module's models directly!

# GOOD: Use exported services
from src.modules.catalog import CatalogService
products = await catalog_service.find_by_ids(ids)

# BAD: Importing internal module classes
from src.modules.catalog.repository import ProductRepository

# GOOD: Import from module __init__
from src.modules.catalog import CatalogService
```

### Scaling Strategy (When Needed)

```
Phase 1: Single Instance
└── Modular Monolith on ECS Fargate (uvicorn)

Phase 2: Horizontal Scaling
└── Multiple uvicorn instances behind ALB
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
1. Set up FastAPI project with module structure
2. Define module boundaries and interfaces
3. Implement core modules (auth, users, catalog)
4. Add business modules (procurement, orders)
5. Implement cross-cutting concerns (caching, events via Celery)
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

```python
# RULE 1: Modules own their database tables exclusively
# Only catalog module can write to products table
# Other modules read via CatalogService

# RULE 2: Cross-module communication via __init__.py exports only
# src/modules/catalog/__init__.py
from .service import CatalogService  # Public API
# _repository is NOT exported

# RULE 3: Events for async, loose coupling via Celery tasks
# procurement module dispatches tasks, notifications module processes
# send_rfq_awarded_notification.delay(rfq_id)

# RULE 4: No circular dependencies
# Allowed: orders → catalog, procurement → catalog
# Not allowed: catalog → orders → catalog
```

### Coupling Prevention Checklist

- [ ] Each module has a clearly defined `__init__.py` exporting only public API
- [ ] No direct model imports across modules
- [ ] No shared mutable state between modules
- [ ] Cross-module calls go through service interfaces
- [ ] Database migrations scoped to single module
- [ ] import-linter rules enforce import boundaries

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
- [FastAPI Project Structure](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [Microservices Prerequisites](https://martinfowler.com/bliki/MicroservicePrerequisites.html)
- [Monolith First](https://martinfowler.com/bliki/MonolithFirst.html)
