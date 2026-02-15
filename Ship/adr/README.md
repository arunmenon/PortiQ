# Architecture Decision Records (ADRs)

## Maritime Ship Chandlery Platform

This directory contains Architecture Decision Records for the B2B maritime ship chandlery platform targeting the $95B global market.

---

## ADR Index

### Functional ADRs (29)

| ID | Title | Status | Priority |
|----|-------|--------|----------|
| [ADR-FN-001](functional/ADR-FN-001-impa-issa-primary-identifier.md) | IMPA/ISSA Code as Primary Identifier | Accepted | P0 |
| [ADR-FN-002](functional/ADR-FN-002-product-master-data-model.md) | Product Master Data Model | Accepted | P0 |
| [ADR-FN-003](functional/ADR-FN-003-catalog-data-ingestion.md) | Catalog Data Ingestion Strategy | Accepted | P0 |
| [ADR-FN-004](functional/ADR-FN-004-product-hierarchy-categories.md) | Product Hierarchy & Categories | Accepted | P1 |
| [ADR-FN-005](functional/ADR-FN-005-catalog-extensibility-jsonb.md) | Catalog Extensibility (JSONB) | Accepted | P1 |
| [ADR-FN-006](functional/ADR-FN-006-document-ai-pipeline.md) | Document AI Pipeline Architecture | Accepted | P0 |
| [ADR-FN-007](functional/ADR-FN-007-document-parsing-service.md) | Document Parsing Service | Accepted | P0 |
| [ADR-FN-008](functional/ADR-FN-008-llm-provider-normalization.md) | LLM Provider for Normalization | Accepted | P1 |
| [ADR-FN-009](functional/ADR-FN-009-confidence-gated-human-loop.md) | Confidence-Gated Human-in-Loop | Accepted | P0 |
| [ADR-FN-010](functional/ADR-FN-010-large-table-processing.md) | Large Table Processing | Accepted | P1 |
| [ADR-FN-011](functional/ADR-FN-011-rfq-workflow-state-machine.md) | RFQ Workflow State Machine | Accepted | P0 |
| [ADR-FN-012](functional/ADR-FN-012-auction-types.md) | Auction Types | Accepted | P1 |
| [ADR-FN-013](functional/ADR-FN-013-quote-comparison-tco-engine.md) | Quote Comparison & TCO Engine | Accepted | P1 |
| [ADR-FN-014](functional/ADR-FN-014-supplier-onboarding-kyc.md) | Supplier Onboarding & KYC | Accepted | P1 |
| [ADR-FN-015](functional/ADR-FN-015-marketplace-framework.md) | Marketplace Framework | Accepted | P1 |
| [ADR-FN-016](functional/ADR-FN-016-embedded-finance-architecture.md) | Embedded Finance Architecture | Accepted | P2 |
| [ADR-FN-017](functional/ADR-FN-017-invoice-financing-workflow.md) | Invoice Financing Workflow | Accepted | P2 |
| [ADR-FN-018](functional/ADR-FN-018-treds-platform-integration.md) | TReDS Platform Integration | Accepted | P2 |
| [ADR-FN-019](functional/ADR-FN-019-ais-data-integration.md) | AIS Data Integration | Accepted | P2 |
| [ADR-FN-020](functional/ADR-FN-020-india-port-integration.md) | India Port Integration (PCS1x) | Accepted | P2 |
| [ADR-FN-021](functional/ADR-FN-021-predictive-supply-ml-model.md) | Predictive Supply ML Model | Accepted | P3 |
| [ADR-FN-022](functional/ADR-FN-022-order-lifecycle-fulfillment.md) | Order Lifecycle & Fulfillment | Accepted | P1 |
| [ADR-FN-023](functional/ADR-FN-023-multi-tenant-user-model.md) | Multi-Tenant User Model | Accepted | P0 |
| [ADR-FN-024](functional/ADR-FN-024-fleet-management-erp-integration.md) | Fleet Management ERP Integration | Accepted | P2 |
| [ADR-FN-025](functional/ADR-FN-025-delivery-proof-of-delivery.md) | Delivery Tracking & Proof-of-Delivery | Accepted | P0 |
| [ADR-FN-026](functional/ADR-FN-026-dispute-resolution-workflow.md) | Dispute Resolution Workflow | Accepted | P0 |
| [ADR-FN-027](functional/ADR-FN-027-settlement-invoice-generation.md) | Settlement Preparation & Invoice Generation | Accepted | P1 |
| [ADR-FN-028](functional/ADR-FN-028-data-export-service.md) | Data Export Service (CSV/Excel/PDF) | Accepted | P1 |
| [ADR-FN-029](functional/ADR-FN-029-basic-inventory-stock-levels.md) | Basic Inventory & Stock Levels | Accepted | P2 |

### Non-Functional ADRs (20)

| ID | Title | Status | Priority |
|----|-------|--------|----------|
| [ADR-NF-001](non-functional/ADR-NF-001-postgresql-unified-data-store.md) | PostgreSQL as Unified Data Store | Accepted | P0 |
| [ADR-NF-002](non-functional/ADR-NF-002-vector-search-pgvector.md) | Vector Search with pgvector | Accepted | P0 |
| [ADR-NF-003](non-functional/ADR-NF-003-search-engine-meilisearch.md) | Search Engine - Meilisearch | Accepted | P0 |
| [ADR-NF-004](non-functional/ADR-NF-004-time-series-timescaledb.md) | Time Series with TimescaleDB | Accepted | P3 |
| [ADR-NF-005](non-functional/ADR-NF-005-caching-strategy-redis.md) | Caching Strategy (Redis) | Accepted | P1 |
| [ADR-NF-006](non-functional/ADR-NF-006-modular-monolith.md) | Modular Monolith vs Microservices | Accepted | P0 |
| [ADR-NF-007](non-functional/ADR-NF-007-api-design-principles.md) | API Design Principles | Accepted | P0 |
| [ADR-NF-008](non-functional/ADR-NF-008-async-processing-bullmq.md) | Async Processing (Celery) | Accepted | P0 |
| [ADR-NF-009](non-functional/ADR-NF-009-event-driven-communication.md) | Event-Driven Communication | Accepted | P1 |
| [ADR-NF-010](non-functional/ADR-NF-010-saga-pattern-transactions.md) | Saga Pattern for Transactions | Accepted | P2 |
| [ADR-NF-011](non-functional/ADR-NF-011-cloud-provider-aws.md) | Cloud Provider - AWS Mumbai | Accepted | P0 |
| [ADR-NF-012](non-functional/ADR-NF-012-container-orchestration.md) | Container Orchestration | Accepted | P0 |
| [ADR-NF-013](non-functional/ADR-NF-013-object-storage-s3.md) | Object Storage (S3) | Accepted | P0 |
| [ADR-NF-014](non-functional/ADR-NF-014-cdn-strategy.md) | CDN Strategy | Accepted | P2 |
| [ADR-NF-015](non-functional/ADR-NF-015-authentication-strategy.md) | Authentication Strategy | Accepted | P0 |
| [ADR-NF-016](non-functional/ADR-NF-016-api-security-rate-limiting.md) | API Security & Rate Limiting | Accepted | P1 |
| [ADR-NF-017](non-functional/ADR-NF-017-data-encryption.md) | Data Encryption | Accepted | P1 |
| [ADR-NF-018](non-functional/ADR-NF-018-multi-tenant-data-isolation.md) | Multi-Tenant Data Isolation | Accepted | P1 |
| [ADR-NF-019](non-functional/ADR-NF-019-observability-stack.md) | Observability Stack | Accepted | P1 |
| [ADR-NF-020](non-functional/ADR-NF-020-cicd-pipeline-design.md) | CI/CD Pipeline Design | Accepted | P1 |

### UI ADRs (17)

| ID | Title | Status | Priority |
|----|-------|--------|----------|
| [ADR-UI-001](ui/ADR-UI-001-nextjs-app-router.md) | Next.js 14+ App Router | Accepted | P0 |
| [ADR-UI-002](ui/ADR-UI-002-component-library-shadcn.md) | Component Library (shadcn/ui) | Accepted | P0 |
| [ADR-UI-003](ui/ADR-UI-003-state-management-strategy.md) | State Management Strategy | Accepted | P1 |
| [ADR-UI-004](ui/ADR-UI-004-buyer-portal-architecture.md) | Buyer Portal Architecture | ⚠️ Superseded | P0 |
| [ADR-UI-005](ui/ADR-UI-005-supplier-dashboard-architecture.md) | Supplier Dashboard Architecture | ⚠️ Superseded | P1 |
| [ADR-UI-006](ui/ADR-UI-006-react-native-expo.md) | React Native with Expo | Accepted | P0 |
| [ADR-UI-007](ui/ADR-UI-007-offline-first-mobile.md) | Offline-First Mobile | Accepted | P0 |
| [ADR-UI-008](ui/ADR-UI-008-mobile-catalog-caching.md) | Mobile Catalog Caching | Accepted | P1 |
| [ADR-UI-009](ui/ADR-UI-009-design-system-theming.md) | Design System & Theming | Accepted | P1 |
| [ADR-UI-010](ui/ADR-UI-010-accessibility-standards.md) | Accessibility Standards | Accepted | P2 |
| [ADR-UI-011](ui/ADR-UI-011-search-ux-pattern.md) | Search UX Pattern | ⚠️ Superseded | P0 |
| [ADR-UI-012](ui/ADR-UI-012-real-time-notifications.md) | Real-Time Notifications | ⚠️ Superseded | P1 |
| [ADR-UI-013](ui/ADR-UI-013-portiq-buyer-experience.md) | **PortiQ Buyer Experience** | Accepted | P0 |
| [ADR-UI-014](ui/ADR-UI-014-portiq-supplier-experience.md) | **PortiQ Supplier Experience** | Accepted | P0 |
| [ADR-UI-015](ui/ADR-UI-015-command-bar-voice-input.md) | **Command Bar & Voice Input** | Accepted | P0 |
| [ADR-UI-016](ui/ADR-UI-016-proactive-intelligence.md) | **Proactive Intelligence & Notifications** | Accepted | P1 |
| [ADR-UI-017](ui/ADR-UI-017-post-award-operational-ui.md) | **Post-Award Operational UI** | Accepted | P0 |

#### PortiQ UX Notes
The PortiQ AI-native UX specification (UI-013 through UI-016) introduces a **conversation-first paradigm** that supersedes traditional dashboard-based approaches:
- **UI-013** supersedes UI-004 (Buyer Portal) with AI-driven buyer experience
- **UI-014** supersedes UI-005 (Supplier Dashboard) with AI-assisted quoting
- **UI-015** supersedes UI-011 (Search UX) with natural language Command Bar
- **UI-016** supersedes UI-012 (Notifications) with proactive intelligence

Superseded ADRs are preserved for historical reference.

---

## Implementation Phases

### 0.x Infrastructure (Done: 0.1, 0.2, 0.4 | Deferred: 0.3)
| Phase | Name | ADRs | Status |
|-------|------|------|--------|
| 0.1 | Database Core | NF-001, NF-002 | Done |
| 0.2 | Backend Architecture | NF-006, NF-007 | Done |
| 0.3 | Cloud & Auth | NF-011, NF-015 | Deferred |
| 0.4 | Hybrid Search & Async | NF-003, NF-008 | Done |

### 1.x Data Ingestion (Done: 1.1)
| Phase | Name | ADRs | Status |
|-------|------|------|--------|
| 1.1 | Maritime Data Feeds | FN-019, FN-020 | Done |
| 1.2 | Fleet System Integration | FN-024, FN-003 | Planned |

### 2.x Prediction Engine (Done: 2.1, 2.2)
| Phase | Name | ADRs | Status |
|-------|------|------|--------|
| 2.1 | Product Data Model | FN-001, FN-002, FN-004 | Done |
| 2.2 | Catalog Extensibility | FN-005 | Done |
| 2.3 | Consumption Prediction | FN-021 | Planned |

### 3.x Orchestration (Done: 3.1, 3.2, 3.3, 3.4 | Planned: 3.5)
| Phase | Name | ADRs | Status |
|-------|------|------|--------|
| 3.1 | Multi-tenancy | FN-023, NF-018 | Done |
| 3.2 | Vendor Onboarding | FN-014, FN-015 | Done |
| 3.3 | RFQ & Bidding | FN-011, FN-012 | Done |
| 3.4 | TCO & Quote Comparison | FN-013 | Done |
| 3.5 | Basic Inventory | FN-029 | Planned |

### 4.x Execution (Done: 4.1, 4.2, 4.3 | Planned: 4.4, 4.5, 4.6)
| Phase | Name | ADRs | Status |
|-------|------|------|--------|
| 4.1 | Order Lifecycle | FN-022, NF-005 | Done |
| 4.2 | Document Pipeline | FN-006, FN-007 | Done |
| 4.3 | AI Quality Control | FN-008, FN-009, FN-010 | Done |
| 4.4 | Order Implementation | FN-022 | Planned |
| 4.5 | Delivery & POD | FN-025 | Planned |
| 4.6 | Dispute Resolution | FN-026 | Planned |

### 5.x Settlement (Planned)
| Phase | Name | ADRs | Status |
|-------|------|------|--------|
| 5.1 | Embedded Finance | FN-016, FN-017 | Planned |
| 5.2 | TReDS Integration | FN-018 | Planned |
| 5.3 | Settlement & Invoicing | FN-027 | Planned |
| 5.4 | Data Export | FN-028 | Planned |

### 6.x User Experience (Done: 6.1, 6.2, 6.5, 6.6 | Superseded: 6.3 | Planned: 6.7)
| Phase | Name | ADRs | Status |
|-------|------|------|--------|
| 6.1 | Web Foundation | UI-001, UI-002 | Done |
| 6.2 | Fleet Manager Portal | UI-004, UI-011 | Done |
| 6.3 | Supplier Dashboard | UI-005, UI-012 | Superseded by 6.6 |
| 6.4 | Mobile Foundation | UI-006, UI-007 | Planned |
| 6.5 | State & Theming | UI-003, UI-009 | Done |
| 6.6 | PortiQ AI Experience | UI-013, UI-014, UI-015, UI-016 | Done |
| 6.7 | Post-Award UI | UI-017 | Planned |

### 7.x Hardening (Planned)
| Phase | Name | ADRs | Status |
|-------|------|------|--------|
| 7.1 | Deployment Infrastructure | NF-012, NF-013 | Planned |
| 7.2 | API Security | NF-016, NF-017 | Planned |
| 7.3 | DevOps & Observability | NF-019, NF-020 | Planned |

### 8.x Scale (Planned)
| Phase | Name | ADRs | Status |
|-------|------|------|--------|
| 8.1 | Event Architecture | NF-009, NF-010 | Planned |
| 8.2 | Performance & Analytics | NF-004, NF-014 | Planned |
| 8.3 | Mobile Polish & Accessibility | UI-008, UI-010 | Planned |

---

## Key Dependencies

```
NF-006 (Monolith) ──> NF-007 (API) ──> All FN-* ADRs
NF-001 (PostgreSQL) ──> NF-002 (pgvector) ──> FN-006 (Doc AI)
                   ──> NF-003 (Hybrid Search) ──> UI-015 (Command Bar)
                   ──> FN-002 (Product Model) ──> FN-001 (IMPA)
NF-008 (Celery) ──> FN-011 (RFQ), FN-013 (TCO), FN-028 (Export)
NF-011 (AWS) ──> NF-012 (Fargate), NF-013 (S3)
NF-013 (S3) ──> FN-025 (Delivery Photos), FN-028 (Export Files)
UI-001 (Next.js) ──> UI-002 (shadcn) ──> UI-013 (PortiQ Buyer)
                                     ──> UI-014 (PortiQ Supplier)
                                     ──> UI-017 (Post-Award UI)
UI-013 (Buyer) ──> UI-015 (Command Bar) ──> UI-016 (Proactive Intel)
UI-006 (React Native) ──> UI-007 (Offline) ──> UI-008 (Caching)
FN-022 (Order) ──> FN-025 (Delivery) ──> FN-026 (Disputes)
                                     ──> FN-027 (Settlement)
FN-002 (Product) ──> FN-029 (Inventory)
FN-014 (Supplier) ──> FN-029 (Inventory)
```

---

## ADR Status Legend

| Status | Description |
|--------|-------------|
| **Proposed** | Under discussion, not yet decided |
| **Accepted** | Decision made and approved |
| **Deprecated** | No longer relevant or replaced |
| **⚠️ Superseded** | Replaced by a newer ADR (see superseding ADR for current guidance) |

---

## Priority Legend

| Priority | Description |
|----------|-------------|
| **P0** | Critical - Must have for MVP |
| **P1** | High - Required for production readiness |
| **P2** | Medium - Important for scaling |
| **P3** | Low - Future enhancement |

---

## References

- [IMPA Marine Stores Guide](https://www.impa.net)
- [ShipServ IMPA Catalogue](https://impa-catalogue.shipserv.com)
- [Azure Document Intelligence](https://azure.microsoft.com/en-us/products/ai-services/ai-document-intelligence)
- [Medusa.js](https://medusajs.com)
- [FastAPI](https://fastapi.tiangolo.com)
- [Next.js](https://nextjs.org)
- [Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API)
- [Expo Speech](https://docs.expo.dev/versions/latest/sdk/speech/)
