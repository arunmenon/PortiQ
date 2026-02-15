# ADR-FN-025: Delivery Tracking & Proof-of-Delivery

**Status:** Accepted
**Date:** 2026-02-12
**Technical Area:** Backend

---

## Context

After an order is confirmed (ADR-FN-022), goods must be physically delivered to the vessel at port. The platform needs to track deliveries, capture proof-of-delivery (POD) evidence, and verify that what was ordered matches what was received.

### Business Context
Maritime delivery presents unique challenges:
- Deliveries happen at port berths, anchorages, or agent warehouses — often with unreliable connectivity
- Proof-of-delivery is legally required for settlement and dispute resolution
- Delivery staff need a mobile-friendly interface to capture GPS, photos, and signatures on-site
- SLA tracking (on-time vs delayed) is critical for supplier performance scoring
- Quantity discrepancies are common and must be flagged immediately
- Photo evidence of delivered goods protects both buyer and supplier

### Technical Context
- Extends ADR-FN-022 (Order Lifecycle) — deliveries are linked to fulfillments/vendor orders
- S3 storage for photos and signature images (ADR-NF-013)
- Event-driven notifications on delivery status changes (ADR-NF-009)
- GPS coordinates captured via browser Geolocation API or mobile native
- Signature capture via HTML5 Canvas or React Native gesture handler

### Assumptions
- Delivery staff have smartphones with camera and GPS capability
- Intermittent connectivity at port — offline capture with sync is a future enhancement
- One delivery maps to one fulfillment from ADR-FN-022
- Photos are stored as S3 objects with presigned URLs for upload/download
- Digital signatures are captured as PNG images and stored in S3

---

## Decision Drivers

- Must capture legally defensible proof-of-delivery (GPS, timestamp, signature, photos)
- Mobile-first UX for delivery staff at port
- Quantity verification against order line items
- SLA tracking for supplier scoring
- Immediate dispute flagging for discrepancies
- S3-backed media storage for scalability

---

## Considered Options

### Option 1: Inline POD on FN-022 Fulfillment Model
**Description:** Add GPS, photo, and signature fields directly to the existing `fulfillments` table from ADR-FN-022.

**Pros:**
- No new tables — simpler schema
- Single query for fulfillment + POD data
- Fewer joins

**Cons:**
- Bloats the fulfillment model with media concerns
- No support for multiple photos per delivery
- SLA configuration has no home
- Tight coupling between logistics and evidence capture

### Option 2: Separate Delivery Model with POD Evidence (Chosen)
**Description:** Dedicated `deliveries` table linked to fulfillments, with separate `delivery_items` for quantity verification and `delivery_photos` for media evidence.

**Pros:**
- Clean separation of logistics (fulfillment) and evidence (delivery/POD)
- Supports multiple photos per delivery
- Dedicated SLA configuration per buyer/supplier pair
- Delivery items enable line-item level quantity verification
- Extensible for future offline sync and mobile enhancements

**Cons:**
- Additional tables and joins
- More complex queries for full delivery picture
- Need to keep delivery status in sync with fulfillment status

### Option 3: Third-Party POD Service Integration
**Description:** Integrate with an external proof-of-delivery service (e.g., Detrack, Onfleet) and store references.

**Pros:**
- Purpose-built for delivery tracking
- Mobile SDKs already available
- Route optimization included

**Cons:**
- Vendor lock-in and ongoing costs
- Data lives outside the platform
- Limited customization for maritime-specific needs
- Connectivity issues at ports may break real-time sync

---

## Decision

**Chosen Option:** Separate Delivery Model with POD Evidence

We implement a dedicated delivery tracking system with `deliveries`, `delivery_items`, `delivery_photos`, and `delivery_sla_configs` tables. Deliveries are linked to fulfillments from ADR-FN-022. POD evidence (GPS, signature, photos) is captured at delivery time and stored in S3.

### Rationale
Maritime POD requires rich evidence capture (photos, GPS, signatures) that would bloat the fulfillment model. A separate delivery entity provides clean separation of concerns, supports multiple photos, enables dedicated SLA tracking, and keeps the fulfillment model focused on logistics. Third-party services add unnecessary cost and connectivity risk for port environments.

---

## Consequences

### Positive
- Clean separation between logistics (fulfillment) and evidence (POD)
- Multiple photos per delivery with S3 storage
- Line-item level quantity verification with discrepancy detection
- SLA configuration per buyer-supplier pair
- GPS + timestamp + signature provides legally defensible POD
- Extensible for offline sync in future mobile phases

### Negative
- Additional database tables and join complexity
- **Mitigation:** Denormalized delivery summary view for common queries
- Must keep delivery and fulfillment statuses synchronized
- **Mitigation:** Event-driven status sync via domain events

### Risks
- Photo upload failures at ports with poor connectivity: Retry queue with exponential backoff, store locally and sync later
- GPS accuracy in port environments: Accept coordinates with accuracy metadata, fallback to manual port/berth entry
- Signature capture quality on small screens: Minimum canvas size enforcement, pinch-to-zoom support

---

## Implementation Notes

### Database Schema

```sql
-- Delivery records linked to fulfillments
CREATE TABLE deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    delivery_number VARCHAR(50) UNIQUE NOT NULL,
    fulfillment_id UUID NOT NULL REFERENCES fulfillments(id),
    vendor_order_id UUID NOT NULL REFERENCES vendor_orders(id),
    order_id UUID NOT NULL REFERENCES orders(id),
    organization_id UUID NOT NULL REFERENCES organizations(id),

    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    -- PENDING, DISPATCHED, IN_TRANSIT, ARRIVED, DELIVERED, ACCEPTED, DISPUTED, CANCELLED

    -- Dispatch info
    dispatched_at TIMESTAMPTZ,
    dispatched_by UUID REFERENCES users(id),
    estimated_arrival TIMESTAMPTZ,

    -- Delivery info
    delivered_at TIMESTAMPTZ,
    delivered_by UUID REFERENCES users(id),
    delivery_type VARCHAR(20), -- ALONGSIDE, WAREHOUSE, AGENT, ANCHORAGE

    -- GPS coordinates at delivery
    delivery_latitude DECIMAL(10, 8),
    delivery_longitude DECIMAL(11, 8),
    gps_accuracy_meters DECIMAL(8, 2),

    -- Receiver info
    receiver_name VARCHAR(200) NOT NULL DEFAULT '',
    receiver_designation VARCHAR(100),
    receiver_contact VARCHAR(50),

    -- Signature (S3 key)
    signature_s3_key VARCHAR(500),
    signature_captured_at TIMESTAMPTZ,

    -- SLA
    sla_target_time TIMESTAMPTZ,
    sla_met BOOLEAN,
    delay_reason TEXT,

    -- Acceptance
    accepted_at TIMESTAMPTZ,
    accepted_by UUID REFERENCES users(id),
    acceptance_notes TEXT,

    -- Dispute
    disputed_at TIMESTAMPTZ,
    dispute_reason TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Line-item level delivery verification
CREATE TABLE delivery_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    delivery_id UUID NOT NULL REFERENCES deliveries(id),
    fulfillment_item_id UUID NOT NULL REFERENCES fulfillment_items(id),
    order_line_item_id UUID NOT NULL REFERENCES order_line_items(id),

    -- Quantities
    quantity_expected INTEGER NOT NULL,
    quantity_delivered INTEGER,
    quantity_accepted INTEGER,
    quantity_rejected INTEGER DEFAULT 0,

    -- Verification
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    -- PENDING, DELIVERED, ACCEPTED, PARTIALLY_ACCEPTED, REJECTED, DISPUTED
    rejection_reason TEXT,
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Photo evidence for deliveries
CREATE TABLE delivery_photos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    delivery_id UUID NOT NULL REFERENCES deliveries(id),
    delivery_item_id UUID REFERENCES delivery_items(id), -- optional: photo of specific item

    s3_key VARCHAR(500) NOT NULL,
    s3_bucket VARCHAR(100) NOT NULL,
    file_name VARCHAR(255),
    content_type VARCHAR(50) DEFAULT 'image/jpeg',
    file_size_bytes INTEGER,

    photo_type VARCHAR(30) NOT NULL DEFAULT 'DELIVERY',
    -- DELIVERY, DAMAGE, PACKAGING, QUANTITY, DISPUTE
    caption TEXT,

    -- Photo metadata
    taken_at TIMESTAMPTZ DEFAULT NOW(),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),

    uploaded_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- SLA configuration per buyer-supplier pair
CREATE TABLE delivery_sla_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    buyer_org_id UUID NOT NULL REFERENCES organizations(id),
    supplier_org_id UUID NOT NULL REFERENCES organizations(id),
    port_code VARCHAR(10), -- optional: port-specific SLA

    -- SLA windows
    delivery_window_hours INTEGER NOT NULL DEFAULT 24,
    max_delay_hours INTEGER NOT NULL DEFAULT 4,

    -- Penalties
    late_delivery_penalty_percent DECIMAL(5, 2) DEFAULT 0,
    no_show_penalty_percent DECIMAL(5, 2) DEFAULT 0,

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(buyer_org_id, supplier_org_id, port_code)
);

-- Indexes
CREATE INDEX idx_deliveries_fulfillment ON deliveries(fulfillment_id);
CREATE INDEX idx_deliveries_order ON deliveries(order_id);
CREATE INDEX idx_deliveries_org ON deliveries(organization_id);
CREATE INDEX idx_deliveries_status ON deliveries(status);
CREATE INDEX idx_delivery_items_delivery ON delivery_items(delivery_id);
CREATE INDEX idx_delivery_photos_delivery ON delivery_photos(delivery_id);
```

### API Endpoints

```
# Delivery Management (9 endpoints)
POST   /api/v1/deliveries                          # Create delivery from fulfillment
POST   /api/v1/deliveries/{id}/dispatch             # Mark as dispatched
POST   /api/v1/deliveries/{id}/record               # Record delivery (GPS, signature, quantities)
POST   /api/v1/deliveries/{id}/photos               # Upload photo(s) — returns S3 presigned URL
POST   /api/v1/deliveries/{id}/accept               # Buyer accepts delivery
POST   /api/v1/deliveries/{id}/dispute               # Flag delivery as disputed
GET    /api/v1/deliveries                           # List deliveries (filterable)
GET    /api/v1/deliveries/{id}                      # Get delivery detail with items and photos
GET    /api/v1/delivery-sla/{buyer_org}/{supplier_org}  # Get SLA config
```

### Domain Events

```python
# Events emitted by the delivery module
"delivery.created"       # {delivery_id, fulfillment_id, order_id}
"delivery.dispatched"    # {delivery_id, dispatched_by, estimated_arrival}
"delivery.recorded"      # {delivery_id, gps, receiver, items_delivered}
"delivery.accepted"      # {delivery_id, accepted_by, all_items_ok}
"delivery.disputed"      # {delivery_id, reason, disputed_items}
"delivery.photo.uploaded" # {delivery_id, photo_id, photo_type}
```

### Dependencies
- ADR-FN-022: Order Lifecycle & Fulfillment (deliveries link to fulfillments)
- ADR-NF-013: Object Storage (S3 for photos and signatures)
- ADR-NF-009: Event-Driven Communication (delivery status events)
- ADR-NF-007: API Design Principles (endpoint conventions)

### Migration Strategy
1. Create `deliveries`, `delivery_items`, `delivery_photos`, `delivery_sla_configs` tables
2. Add indexes for common query patterns
3. Implement delivery service with create, dispatch, record, accept flows
4. Integrate S3 presigned URL generation for photo uploads
5. Add event emission on status transitions
6. Wire delivery acceptance to fulfillment status update in FN-022

---

## References
- [ADR-FN-022: Order Lifecycle & Fulfillment](ADR-FN-022-order-lifecycle-fulfillment.md)
- [HTML5 Geolocation API](https://developer.mozilla.org/en-US/docs/Web/API/Geolocation_API)
- [AWS S3 Presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html)
- [Digital Signature Capture](https://github.com/nicbell/react-native-signature-canvas)
