# ADR-FN-027: Settlement Preparation & Invoice Generation

**Status:** Accepted
**Date:** 2026-02-12
**Technical Area:** Backend

---

## Context

Once goods are delivered and accepted (or disputes resolved), the platform must generate invoices and prepare settlement data. This bridges the gap between operational delivery and financial processing, providing clean reconciliation views and invoice documents.

### Business Context
Maritime procurement settlement has specific requirements:
- Invoices must reconcile what was ordered vs what was delivered vs what was accepted
- Disputes (quantity shortages, quality rejections) create credit notes or adjustments
- Settlement periods vary: per delivery, per port call, weekly, or monthly aggregation
- Shipping companies need clean invoice summaries for their finance teams
- Suppliers need timely invoice generation to maintain cash flow
- Export-ready invoices (PDF, Excel) are required for accounting systems
- Future integration with embedded finance (ADR-FN-016/FN-017) and TReDS (ADR-FN-018)

### Technical Context
- Invoices auto-generated from accepted deliveries (ADR-FN-025)
- Dispute resolutions (ADR-FN-026) create credit adjustments on invoices
- Order data (ADR-FN-022) provides the pricing baseline
- Celery tasks for async invoice generation (ADR-NF-008)
- Event-driven notifications on invoice status changes (ADR-NF-009)

### Assumptions
- Invoices are generated automatically when a delivery is accepted
- One invoice per delivery (but can be consolidated per settlement period)
- Credit notes from dispute resolution reduce the invoice amount
- Actual payment processing is out of scope — invoices prepare data for offline or future finance integration
- Tax calculations are simplified (single tax rate per organization) for MVP

---

## Decision Drivers

- Automatic invoice generation from delivery acceptance
- Clean reconciliation: ordered → delivered → accepted → invoiced
- Dispute-aware adjustments (credit notes)
- Settlement period aggregation (per port call, weekly, monthly)
- Future-ready for FN-016/FN-017 embedded finance integration
- Export-friendly data structure

---

## Considered Options

### Option 1: Manual Invoice Creation by Supplier
**Description:** Suppliers create invoices manually and upload them. Platform stores and tracks status.

**Pros:**
- Suppliers control their own invoice content
- Simple platform implementation
- Familiar to suppliers

**Cons:**
- Data entry duplication — supplier re-enters what platform already knows
- Prone to errors and discrepancies
- No automatic reconciliation
- Slower settlement cycle

### Option 2: Auto-Generated Invoices from Delivery Acceptance (Chosen)
**Description:** Platform auto-generates invoices from accepted delivery data. Invoice reflects agreed prices, delivered quantities, and dispute adjustments.

**Pros:**
- Zero data entry — invoices auto-populated from delivery data
- Automatic reconciliation between order, delivery, and invoice
- Dispute adjustments applied automatically
- Clean data flow for settlement
- Ready for future finance integration

**Cons:**
- Suppliers may want to customize invoice details
- Platform becomes the invoice system of record
- Tax handling must be built

### Option 3: Third-Party Invoicing Integration
**Description:** Integrate with an external invoicing service (Zoho Invoice, QuickBooks) for generation and tracking.

**Pros:**
- Purpose-built invoicing features
- Tax calculation libraries
- PDF generation included

**Cons:**
- Data synchronization complexity
- Vendor lock-in and ongoing costs
- Loses direct link to order/delivery data
- Extra latency in settlement flow

---

## Decision

**Chosen Option:** Auto-Generated Invoices from Delivery Acceptance

Invoices are automatically generated when a delivery is accepted. The invoice reflects the agreed unit prices from the order, the accepted quantities from the delivery, and any credit adjustments from resolved disputes. Settlement periods allow aggregation for reporting and payment processing.

### Rationale
Since the platform already has the order prices, delivered quantities, and dispute outcomes, auto-generating invoices eliminates data entry, ensures accuracy, and enables instant reconciliation. This creates the cleanest data flow from order through settlement and positions the platform for future embedded finance integration.

---

## Consequences

### Positive
- Zero manual data entry for invoices
- Automatic reconciliation across order → delivery → invoice
- Dispute adjustments seamlessly integrated
- Settlement periods enable flexible aggregation
- Clean data foundation for future FN-016/FN-017 integration
- Consistent invoice format across all transactions

### Negative
- Suppliers lose direct control over invoice content
- **Mitigation:** Allow supplier notes/reference fields; provide preview before finalization
- Tax handling adds complexity
- **Mitigation:** Simple single-rate tax for MVP, extensible tax engine for later

### Risks
- Incorrect auto-generated amounts due to data issues: Reconciliation validation before invoice finalization
- Disputed deliveries creating partial invoices: Hold invoice generation until disputes are resolved or create provisional invoices with adjustments
- Tax calculation errors: Validate against known tax rules, allow manual override

---

## Implementation Notes

### Database Schema

```sql
-- Invoices generated from accepted deliveries
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    organization_id UUID NOT NULL REFERENCES organizations(id),

    -- Links
    order_id UUID NOT NULL REFERENCES orders(id),
    vendor_order_id UUID NOT NULL REFERENCES vendor_orders(id),
    delivery_id UUID REFERENCES deliveries(id),
    settlement_period_id UUID REFERENCES settlement_periods(id),

    -- Parties
    buyer_org_id UUID NOT NULL REFERENCES organizations(id),
    supplier_org_id UUID NOT NULL REFERENCES organizations(id),

    -- Status
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT',
    -- DRAFT, READY, SENT, ACKNOWLEDGED, DISPUTED, PAID, CANCELLED, CREDIT_NOTE

    -- Amounts
    subtotal DECIMAL(15, 2) NOT NULL,
    tax_rate DECIMAL(5, 2) DEFAULT 0,
    tax_amount DECIMAL(15, 2) DEFAULT 0,
    discount_amount DECIMAL(15, 2) DEFAULT 0,
    credit_adjustment DECIMAL(15, 2) DEFAULT 0, -- from dispute resolutions
    total_amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',

    -- References
    buyer_po_number VARCHAR(100),
    supplier_invoice_ref VARCHAR(100),

    -- Dates
    invoice_date DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date DATE,
    sent_at TIMESTAMPTZ,
    acknowledged_at TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    paid_reference VARCHAR(200),

    -- Notes
    notes TEXT,
    internal_notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Invoice line items from accepted delivery items
CREATE TABLE invoice_line_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    order_line_item_id UUID NOT NULL REFERENCES order_line_items(id),
    delivery_item_id UUID REFERENCES delivery_items(id),
    dispute_id UUID REFERENCES disputes(id), -- if credit adjustment

    -- Product info (denormalized for invoice record)
    impa_code CHAR(6),
    product_name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Quantities
    quantity_ordered INTEGER NOT NULL,
    quantity_delivered INTEGER NOT NULL,
    quantity_accepted INTEGER NOT NULL,
    quantity_rejected INTEGER DEFAULT 0,

    -- Pricing
    unit_price DECIMAL(12, 2) NOT NULL,
    line_subtotal DECIMAL(15, 2) NOT NULL,
    credit_amount DECIMAL(15, 2) DEFAULT 0, -- from dispute resolution
    line_total DECIMAL(15, 2) NOT NULL,

    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Settlement periods for aggregation
CREATE TABLE settlement_periods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),

    period_type VARCHAR(20) NOT NULL, -- PORT_CALL, WEEKLY, MONTHLY
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    period_label VARCHAR(100), -- e.g., "Mumbai Port Call - Jan 2026" or "Week 3 - Jan 2026"

    -- Aggregates
    total_invoices INTEGER DEFAULT 0,
    total_amount DECIMAL(15, 2) DEFAULT 0,
    total_credits DECIMAL(15, 2) DEFAULT 0,
    net_amount DECIMAL(15, 2) DEFAULT 0,

    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    -- OPEN, CLOSED, RECONCILED
    closed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_invoices_org ON invoices(organization_id);
CREATE INDEX idx_invoices_order ON invoices(order_id);
CREATE INDEX idx_invoices_buyer ON invoices(buyer_org_id);
CREATE INDEX idx_invoices_supplier ON invoices(supplier_org_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_settlement ON invoices(settlement_period_id);
CREATE INDEX idx_invoice_items_invoice ON invoice_line_items(invoice_id);
CREATE INDEX idx_settlement_periods_org ON settlement_periods(organization_id);
```

### API Endpoints

```
# Invoice & Settlement (8 endpoints)
POST   /api/v1/invoices/generate/{delivery_id}       # Auto-generate invoice from accepted delivery
GET    /api/v1/invoices                               # List invoices (filterable by status, org, period)
GET    /api/v1/invoices/{id}                          # Get invoice detail with line items
PUT    /api/v1/invoices/{id}/ready                    # Mark invoice as ready for payment
PUT    /api/v1/invoices/{id}/acknowledge              # Buyer acknowledges invoice
PUT    /api/v1/invoices/{id}/mark-paid                # Record payment against invoice
GET    /api/v1/invoices/{id}/reconciliation           # Reconciliation view: ordered vs delivered vs invoiced
GET    /api/v1/settlements                            # Settlement summary by period
```

### Invoice Generation Flow

```
Delivery Accepted
      │
      ▼
┌─────────────────────────┐
│ Check for open disputes │
│ on this delivery        │
└─────────┬───────────────┘
          │
    ┌─────▼──────┐     ┌──────────────────┐
    │ No disputes│     │ Has disputes     │
    └─────┬──────┘     └───────┬──────────┘
          │                    │
          │              ┌─────▼──────────┐
          │              │ Wait for       │
          │              │ resolution     │
          │              └─────┬──────────┘
          │                    │
          └────────┬───────────┘
                   │
          ┌────────▼──────────┐
          │ Generate Invoice  │
          │ - Accepted qtys   │
          │ - Agreed prices   │
          │ - Credit adjust.  │
          └────────┬──────────┘
                   │
          ┌────────▼──────────┐
          │ Invoice DRAFT     │
          │ → READY → SENT   │
          │ → ACKNOWLEDGED    │
          │ → PAID            │
          └───────────────────┘
```

### Domain Events

```python
# Events emitted by the invoice/settlement module
"invoice.generated"     # {invoice_id, order_id, delivery_id, total_amount}
"invoice.ready"         # {invoice_id, supplier_org_id}
"invoice.acknowledged"  # {invoice_id, buyer_org_id}
"invoice.paid"          # {invoice_id, payment_reference, paid_at}
"settlement.closed"     # {settlement_period_id, net_amount}
```

### Dependencies
- ADR-FN-022: Order Lifecycle & Fulfillment (order pricing data)
- ADR-FN-025: Delivery & Proof-of-Delivery (delivery acceptance triggers invoice)
- ADR-FN-026: Dispute Resolution (credit adjustments from resolved disputes)
- ADR-NF-008: Async Processing (async invoice generation via Celery)
- ADR-NF-009: Event-Driven Communication (invoice status events)

### Migration Strategy
1. Create `invoices`, `invoice_line_items`, `settlement_periods` tables
2. Implement auto-generation on delivery acceptance event
3. Build reconciliation view (ordered vs delivered vs invoiced)
4. Add invoice status workflow (DRAFT → READY → SENT → PAID)
5. Integrate dispute credit adjustments into invoice generation
6. Build settlement period aggregation logic
7. Prepare data structure for future FN-016/FN-017 integration

---

## References
- [ADR-FN-022: Order Lifecycle & Fulfillment](ADR-FN-022-order-lifecycle-fulfillment.md)
- [ADR-FN-025: Delivery & Proof-of-Delivery](ADR-FN-025-delivery-proof-of-delivery.md)
- [ADR-FN-026: Dispute Resolution Workflow](ADR-FN-026-dispute-resolution-workflow.md)
- [Invoice Standards - PEPPOL BIS](https://peppol.eu/what-is-peppol/peppol-profiles-specifications/)
