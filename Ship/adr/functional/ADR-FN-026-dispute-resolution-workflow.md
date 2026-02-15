# ADR-FN-026: Dispute Resolution Workflow

**Status:** Accepted
**Date:** 2026-02-12
**Technical Area:** Backend

---

## Context

When deliveries have quantity discrepancies, quality issues, or other problems, a structured dispute resolution process is needed. The platform must track disputes from creation through investigation to resolution, with clear accountability and financial outcomes.

### Business Context
Maritime procurement disputes are common and costly:
- Quantity shortages at delivery (goods counted differ from shipping manifest)
- Quality issues discovered after delivery (wrong grade, damaged goods, expired items)
- Price disputes between agreed quote and invoiced amount
- Delivery timing disputes (late delivery impacting vessel schedule)
- Without structured resolution, disputes become adversarial and erode trust
- Financial outcomes (credit notes, refunds, penalties) must be tracked for settlement

### Technical Context
- Disputes arise from delivery acceptance (ADR-FN-025) or invoice review
- Linked to orders (ADR-FN-022) for financial context
- Dispute resolution affects invoice generation (ADR-FN-027)
- Comment trail with attachments for evidence
- State machine for predictable workflow progression

### Assumptions
- Disputes are raised by the buyer (vessel/procurement team)
- Suppliers respond within a defined SLA (48-72 hours)
- PortiQ operations team can be assigned as reviewer for escalations
- Financial outcomes are tracked but actual money movement is handled by settlement (ADR-FN-027)
- One dispute per delivery item, but multiple disputes per delivery are allowed

---

## Decision Drivers

- Clear state machine for dispute progression
- Comment trail with evidence attachments
- Financial outcome tracking (credit, refund, replacement)
- SLA enforcement for response times
- Escalation path for unresolved disputes
- Audit trail for compliance

---

## Considered Options

### Option 1: Inline Dispute Fields on Delivery/Invoice
**Description:** Add `is_disputed`, `dispute_reason`, `dispute_resolved` fields directly to delivery and invoice records.

**Pros:**
- Simple — no new tables
- Easy to query disputed deliveries
- Minimal implementation effort

**Cons:**
- No comment trail or back-and-forth communication
- No state machine — just boolean flags
- Cannot track multiple issues per delivery
- No financial outcome tracking
- No escalation support

### Option 2: Dedicated Dispute Entity with State Machine (Chosen)
**Description:** Separate `disputes` table with state machine (OPEN → UNDER_REVIEW → RESOLVED/ESCALATED), comment trail, and financial outcome tracking.

**Pros:**
- Full state machine with audit trail
- Comment thread for buyer-supplier communication
- Multiple disputes per delivery supported
- Financial outcome tracking (credit amount, resolution type)
- Escalation to platform operations team
- SLA tracking on dispute response

**Cons:**
- Additional tables and complexity
- Need to sync dispute status back to delivery/order
- More endpoints to build and maintain

### Option 3: External Ticketing System Integration
**Description:** Use a third-party ticketing system (Zendesk, Freshdesk) for dispute management.

**Pros:**
- Purpose-built for ticket workflows
- Email integration out of the box
- Reporting and analytics included

**Cons:**
- Context switching between platform and ticketing tool
- Disputes lose connection to order/delivery data
- Ongoing subscription costs
- Cannot embed financial outcomes in ticket

---

## Decision

**Chosen Option:** Dedicated Dispute Entity with State Machine

We implement a dedicated dispute resolution system with `disputes`, `dispute_comments`, and `dispute_transitions` tables. Disputes follow a state machine: OPEN → UNDER_REVIEW → RESOLVED or ESCALATED. Each dispute tracks the financial outcome (credit note, refund, replacement) and links back to the delivery and order for full context.

### Rationale
Maritime disputes require full traceability from the delivery discrepancy through investigation to financial resolution. Inline fields are too simplistic for a workflow that involves back-and-forth communication, evidence, and financial outcomes. External ticketing loses the critical link to order and delivery data. A dedicated entity with state machine provides the structure, audit trail, and financial integration needed.

---

## Consequences

### Positive
- Structured workflow with clear states and transitions
- Full comment trail with timestamps and attachments
- Financial outcome tracking integrated with settlement
- Escalation path for complex disputes
- SLA enforcement drives timely resolution
- Audit trail for compliance and reporting

### Negative
- Additional complexity in the data model
- **Mitigation:** Clear foreign key relationships and denormalized summary fields
- Dispute status must sync to delivery and order status
- **Mitigation:** Domain events trigger status updates on related entities

### Risks
- Disputes may become stale without follow-up: Automated reminders via Celery scheduled tasks
- Supplier may not respond within SLA: Auto-escalation after SLA breach
- Complex multi-party disputes: Escalation to PortiQ operations with full context

---

## Implementation Notes

### Database Schema

```sql
-- Disputes linked to deliveries, orders, and line items
CREATE TABLE disputes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dispute_number VARCHAR(50) UNIQUE NOT NULL,
    organization_id UUID NOT NULL REFERENCES organizations(id),

    -- Links
    delivery_id UUID REFERENCES deliveries(id),
    delivery_item_id UUID REFERENCES delivery_items(id),
    order_id UUID NOT NULL REFERENCES orders(id),
    vendor_order_id UUID REFERENCES vendor_orders(id),

    -- Parties
    raised_by_org_id UUID NOT NULL REFERENCES organizations(id),
    raised_by_user_id UUID NOT NULL REFERENCES users(id),
    supplier_org_id UUID NOT NULL REFERENCES organizations(id),
    assigned_reviewer_id UUID REFERENCES users(id),

    -- Dispute details
    dispute_type VARCHAR(30) NOT NULL,
    -- QUANTITY_SHORTAGE, QUALITY_ISSUE, WRONG_PRODUCT, DAMAGED_GOODS, PRICE_DISPUTE, LATE_DELIVERY, OTHER
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN',
    -- OPEN, UNDER_REVIEW, AWAITING_SUPPLIER, AWAITING_BUYER, RESOLVED, ESCALATED, CLOSED
    priority VARCHAR(10) NOT NULL DEFAULT 'MEDIUM',
    -- LOW, MEDIUM, HIGH, CRITICAL

    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,

    -- Financial
    disputed_amount DECIMAL(15, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    resolution_type VARCHAR(30),
    -- CREDIT_NOTE, REFUND, REPLACEMENT, PRICE_ADJUSTMENT, NO_ACTION, SPLIT
    resolution_amount DECIMAL(15, 2),
    resolution_notes TEXT,

    -- SLA
    response_due_at TIMESTAMPTZ,
    resolution_due_at TIMESTAMPTZ,
    sla_breached BOOLEAN DEFAULT FALSE,

    -- Timestamps
    resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES users(id),
    escalated_at TIMESTAMPTZ,
    escalated_by UUID REFERENCES users(id),
    closed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Comment trail for dispute communication
CREATE TABLE dispute_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dispute_id UUID NOT NULL REFERENCES disputes(id),
    author_id UUID NOT NULL REFERENCES users(id),
    author_org_id UUID NOT NULL REFERENCES organizations(id),

    content TEXT NOT NULL,
    is_internal BOOLEAN DEFAULT FALSE, -- internal notes not visible to other party

    -- Attachment (optional)
    attachment_s3_key VARCHAR(500),
    attachment_filename VARCHAR(255),
    attachment_content_type VARCHAR(50),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- State transition audit log
CREATE TABLE dispute_transitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dispute_id UUID NOT NULL REFERENCES disputes(id),
    from_status VARCHAR(30) NOT NULL,
    to_status VARCHAR(30) NOT NULL,
    transitioned_by UUID NOT NULL REFERENCES users(id),
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_disputes_org ON disputes(organization_id);
CREATE INDEX idx_disputes_order ON disputes(order_id);
CREATE INDEX idx_disputes_delivery ON disputes(delivery_id);
CREATE INDEX idx_disputes_status ON disputes(status);
CREATE INDEX idx_disputes_supplier ON disputes(supplier_org_id);
CREATE INDEX idx_dispute_comments_dispute ON dispute_comments(dispute_id);
CREATE INDEX idx_dispute_transitions_dispute ON dispute_transitions(dispute_id);
```

### State Machine

```
                    ┌─────────────────────────────┐
                    │           OPEN               │
                    │  (Buyer raises dispute)       │
                    └──────────┬──────────────────┘
                               │ assign_reviewer
                    ┌──────────▼──────────────────┐
                    │       UNDER_REVIEW           │
                    │  (Reviewer investigates)      │
                    └──┬───────────┬──────────┬───┘
                       │           │          │
          request_info │           │ resolve  │ escalate
                       │           │          │
            ┌──────────▼──┐  ┌─────▼────┐  ┌──▼─────────┐
            │ AWAITING_    │  │ RESOLVED │  │ ESCALATED  │
            │ SUPPLIER/    │  │          │  │ (Ops team) │
            │ BUYER        │  └─────┬────┘  └──────┬─────┘
            └──────┬───────┘        │              │
                   │ respond        │              │ resolve
                   │                │              │
            ┌──────▼───────┐        │         ┌────▼─────┐
            │ UNDER_REVIEW ├────────┤         │ RESOLVED │
            │ (back)       │        │         └────┬─────┘
            └──────────────┘        │              │
                                    └──────┬───────┘
                                    ┌──────▼───────┐
                                    │   CLOSED     │
                                    │ (archived)   │
                                    └──────────────┘
```

### API Endpoints

```
# Dispute Resolution (7 endpoints)
POST   /api/v1/disputes                         # Raise a dispute
GET    /api/v1/disputes                         # List disputes (filterable by status, type, org)
GET    /api/v1/disputes/{id}                    # Get dispute detail with comments
POST   /api/v1/disputes/{id}/comments           # Add comment (with optional attachment)
PUT    /api/v1/disputes/{id}/assign             # Assign reviewer
POST   /api/v1/disputes/{id}/resolve            # Resolve with financial outcome
POST   /api/v1/disputes/{id}/escalate           # Escalate to platform operations
```

### Domain Events

```python
# Events emitted by the dispute module
"dispute.created"      # {dispute_id, order_id, delivery_id, type, raised_by}
"dispute.assigned"     # {dispute_id, reviewer_id}
"dispute.commented"    # {dispute_id, author_id, is_internal}
"dispute.resolved"     # {dispute_id, resolution_type, resolution_amount}
"dispute.escalated"    # {dispute_id, escalated_by, reason}
"dispute.sla_breached" # {dispute_id, sla_type (response|resolution)}
```

### Dependencies
- ADR-FN-022: Order Lifecycle & Fulfillment (disputes reference orders)
- ADR-FN-025: Delivery & Proof-of-Delivery (disputes raised from delivery discrepancies)
- ADR-NF-009: Event-Driven Communication (dispute events)
- ADR-NF-013: Object Storage (comment attachments in S3)
- ADR-NF-008: Async Processing (SLA reminders via Celery)

### Migration Strategy
1. Create `disputes`, `dispute_comments`, `dispute_transitions` tables
2. Implement dispute creation from delivery acceptance flow
3. Build comment system with attachment support
4. Add state machine validation on transitions
5. Implement SLA tracking with Celery-based reminders
6. Wire dispute resolution to delivery/order status updates
7. Connect resolved disputes to invoice adjustments (ADR-FN-027)

---

## References
- [ADR-FN-022: Order Lifecycle & Fulfillment](ADR-FN-022-order-lifecycle-fulfillment.md)
- [ADR-FN-025: Delivery & Proof-of-Delivery](ADR-FN-025-delivery-proof-of-delivery.md)
- [Dispute Resolution Best Practices](https://www.bimco.org/contracts-and-clauses)
