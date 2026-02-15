# ADR-FN-029: Basic Inventory & Stock Levels

**Status:** Accepted
**Date:** 2026-02-12
**Technical Area:** Backend

---

## Context

Suppliers need to track stock levels for the products they offer on the platform. Basic inventory visibility enables smarter RFQ routing (directing requests to suppliers who have stock) and helps suppliers manage their chandlery operations.

### Business Context
Ship chandlers typically operate from port warehouses with varying stock:
- Suppliers need to indicate which items they have in stock and approximate quantities
- Buyers benefit from knowing which suppliers can fulfill immediately vs requiring lead time
- Stock levels change with deliveries (auto-deduction) and restocking
- Low-stock alerts help suppliers avoid accepting orders they cannot fulfill
- Inventory data feeds into supplier matching intelligence (ADR-FN-014) for smarter routing
- Full WMS (warehouse management system) is out of scope — this is a simple stock level tracker

### Technical Context
- Products are defined in the product catalog (ADR-FN-002)
- Suppliers are onboarded via ADR-FN-014
- Stock deduction triggered by delivery acceptance events (ADR-FN-025)
- Movement audit log tracks all stock changes for reconciliation
- Low-stock alerts processed via Celery (ADR-NF-008)

### Assumptions
- Stock levels are per supplier per product (not per warehouse — single location per supplier for MVP)
- Quantities are in the product's standard unit of measure
- Stock updates can be manual (supplier input) or automatic (delivery deduction)
- Negative stock is allowed (indicates backorder/oversold situation)
- Stock data is advisory — not a hard constraint on order acceptance

---

## Decision Drivers

- Simple stock level tracking per supplier per product
- Movement audit log for traceability
- Auto-deduction on delivery acceptance
- Low-stock alerting
- Feeds into supplier matching for RFQ routing
- Minimal complexity — not a full WMS

---

## Considered Options

### Option 1: Stock Field on SupplierProduct
**Description:** Add a `quantity_available` column directly to the existing supplier-product relationship table.

**Pros:**
- Simplest implementation — one column
- No new tables
- Easy to query with existing product APIs

**Cons:**
- No movement history — cannot audit stock changes
- No bulk update support
- Cannot track why stock changed (delivery, manual adjustment, restocking)
- Hard to add alerts without movement tracking

### Option 2: Dedicated StockLevel Entity with Movement Audit Log (Chosen)
**Description:** Separate `stock_levels` table for current quantities and `stock_movements` table for change history.

**Pros:**
- Current stock + full movement history
- Audit trail for every stock change
- Supports both manual and automatic updates
- Movement data enables trend analysis and low-stock prediction
- Bulk update via CSV/API
- Clean separation from product catalog

**Cons:**
- Two new tables
- Must keep stock_levels in sync with movements
- More complex queries for "products with stock"

### Option 3: Event-Sourced Inventory
**Description:** Store only stock movements (events) and compute current levels from the event stream.

**Pros:**
- Perfect audit trail
- Replay capability
- No sync issues (single source of truth)

**Cons:**
- Expensive to compute current stock (aggregate all events)
- Complex implementation
- Overkill for basic inventory needs
- Query performance issues at scale

---

## Decision

**Chosen Option:** Dedicated StockLevel Entity with Movement Audit Log

We implement a `stock_levels` table that holds current stock per supplier per product, alongside a `stock_movements` table that records every change (manual update, delivery deduction, restocking). The stock level is the source of truth for current quantity; movements provide the audit trail.

### Rationale
A simple field on SupplierProduct lacks the audit trail and movement tracking needed for reconciliation and alerting. Event-sourced inventory is overkill for what is essentially a simple stock counter with history. The dedicated entity approach provides current-state queries (fast) with full history (traceable) — the right balance for MVP inventory.

---

## Consequences

### Positive
- Clear current stock levels per supplier per product
- Full movement audit trail
- Supports manual and automatic stock updates
- Low-stock alerts based on configurable thresholds
- Movement data enables future trend analysis
- Feeds into supplier matching for smarter RFQ routing

### Negative
- Additional tables in the schema
- **Mitigation:** Simple two-table design with clear ownership
- Must ensure stock_levels stays in sync with movements
- **Mitigation:** All stock changes go through the service layer which updates both atomically

### Risks
- Stock data becomes stale if suppliers don't update: Low-stock reminder notifications, last-updated visibility in UI
- Auto-deduction conflicts with manual updates: Movement log shows all changes; service layer uses database transactions for atomicity
- Negative stock due to overselling: Allow negative stock as advisory; flag for supplier attention

---

## Implementation Notes

### Database Schema

```sql
-- Current stock levels per supplier per product
CREATE TABLE stock_levels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id), -- supplier org
    product_id UUID NOT NULL REFERENCES products(id),

    -- Current quantity
    quantity_available INTEGER NOT NULL DEFAULT 0,
    unit_of_measure VARCHAR(20) NOT NULL DEFAULT 'EACH',

    -- Thresholds
    reorder_point INTEGER, -- alert when stock falls below
    reorder_quantity INTEGER, -- suggested restock amount
    max_stock_level INTEGER,

    -- Status
    is_in_stock BOOLEAN GENERATED ALWAYS AS (quantity_available > 0) STORED,
    is_low_stock BOOLEAN GENERATED ALWAYS AS (
        reorder_point IS NOT NULL AND quantity_available <= reorder_point
    ) STORED,

    -- Metadata
    last_movement_at TIMESTAMPTZ,
    last_counted_at TIMESTAMPTZ, -- physical count date
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(organization_id, product_id)
);

-- Stock movement audit log
CREATE TABLE stock_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_level_id UUID NOT NULL REFERENCES stock_levels(id),
    organization_id UUID NOT NULL REFERENCES organizations(id),

    -- Movement details
    movement_type VARCHAR(30) NOT NULL,
    -- MANUAL_ADJUSTMENT, DELIVERY_DEDUCTION, RESTOCK, INITIAL_STOCK, CORRECTION, RETURN
    quantity_change INTEGER NOT NULL, -- positive = add, negative = deduct
    quantity_before INTEGER NOT NULL,
    quantity_after INTEGER NOT NULL,

    -- Reference (what caused this movement)
    reference_type VARCHAR(30), -- DELIVERY, ORDER, MANUAL, IMPORT
    reference_id UUID, -- delivery_id, order_id, etc.

    -- Who and why
    performed_by UUID REFERENCES users(id),
    reason TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_stock_levels_org ON stock_levels(organization_id);
CREATE INDEX idx_stock_levels_product ON stock_levels(product_id);
CREATE INDEX idx_stock_levels_low ON stock_levels(is_low_stock) WHERE is_low_stock = TRUE;
CREATE INDEX idx_stock_movements_stock ON stock_movements(stock_level_id);
CREATE INDEX idx_stock_movements_org ON stock_movements(organization_id);
CREATE INDEX idx_stock_movements_type ON stock_movements(movement_type);
CREATE INDEX idx_stock_movements_ref ON stock_movements(reference_type, reference_id);
```

### API Endpoints

```
# Inventory & Stock (5 endpoints)
GET    /api/v1/inventory                            # List stock levels (filterable by product, low-stock)
GET    /api/v1/inventory/{product_id}               # Get stock detail with movement history
PUT    /api/v1/inventory/{product_id}               # Update stock (manual adjustment)
POST   /api/v1/inventory/bulk-update                # Bulk update via CSV or JSON array
GET    /api/v1/inventory/low-stock                  # Low-stock alerts (items below reorder point)
```

### Auto-Deduction Flow

```
Delivery Accepted (event from FN-025)
        │
        ▼
┌─────────────────────────┐
│ For each accepted item: │
│ - Find stock_level      │
│ - Deduct quantity       │
│ - Record movement       │
│ - Check low-stock       │
└─────────┬───────────────┘
          │
    ┌─────▼──────────┐
    │ Below reorder  │──── Yes ───▶ Emit "inventory.low_stock" event
    │ point?         │
    └─────┬──────────┘
          │ No
          ▼
       (done)
```

### Domain Events

```python
# Events emitted by the inventory module
"inventory.updated"       # {stock_level_id, product_id, quantity_change, new_quantity}
"inventory.low_stock"     # {stock_level_id, product_id, current_qty, reorder_point}
"inventory.out_of_stock"  # {stock_level_id, product_id}
"inventory.restocked"     # {stock_level_id, product_id, quantity_added}
```

### Dependencies
- ADR-FN-002: Product Master Data Model (products referenced by stock levels)
- ADR-FN-014: Supplier Onboarding & KYC (suppliers own stock levels)
- ADR-FN-025: Delivery & Proof-of-Delivery (delivery acceptance triggers stock deduction)
- ADR-NF-008: Async Processing (low-stock alert notifications)
- ADR-NF-009: Event-Driven Communication (inventory events)

### Migration Strategy
1. Create `stock_levels` and `stock_movements` tables
2. Implement manual stock update API with movement logging
3. Implement bulk update endpoint (CSV + JSON)
4. Add event listener for delivery acceptance → auto-deduction
5. Implement low-stock alert logic with configurable thresholds
6. Wire inventory data into supplier matching intelligence (FN-014)

---

## References
- [ADR-FN-002: Product Master Data Model](ADR-FN-002-product-master-data-model.md)
- [ADR-FN-014: Supplier Onboarding & KYC](ADR-FN-014-supplier-onboarding-kyc.md)
- [ADR-FN-025: Delivery & Proof-of-Delivery](ADR-FN-025-delivery-proof-of-delivery.md)
- [Inventory Management Basics](https://www.investopedia.com/terms/i/inventory-management.asp)
