# ADR-UI-017: Post-Award Operational UI

**Status:** Accepted
**Date:** 2026-02-12
**Technical Area:** Frontend

---

## Context

The codebase currently stops at RFQ Award — there are no UI pages for orders, deliveries, proof-of-delivery, settlements, invoices, disputes, or inventory. The post-award operational flow is the core MVP value chain and needs dedicated pages for both buyer and supplier personas.

### Business Context
The post-award flow is where real value is delivered:
- **Buyers** need to track orders, verify deliveries, review invoices, and manage disputes
- **Suppliers** need to manage confirmed orders, submit deliveries with POD evidence, track invoices, and maintain inventory
- Delivery staff need mobile-friendly interfaces at port for GPS/photo/signature capture
- Finance teams need reconciliation views and export capabilities
- The supplier portal currently shows "Coming Soon" for orders — this must be replaced with real functionality

### Technical Context
- Follows existing Next.js 14+ App Router pattern (ADR-UI-001)
- Uses shadcn/ui components (ADR-UI-002)
- React Query for server state (ADR-UI-003)
- Buyer pages live at `apps/web/app/(dashboard)/` following ADR-UI-013
- Supplier pages live at `apps/web/app/(supplier)/supplier/` following ADR-UI-014
- Backend APIs defined in ADR-FN-022 through ADR-FN-029

### Assumptions
- All pages follow the existing layout and navigation patterns
- Mobile-responsive design using Tailwind breakpoints (delivery pages are mobile-first)
- PortiQ AI conversation panel available on all pages (ADR-UI-013)
- Real-time updates via React Query refetch (no WebSocket for MVP)
- Pages share common table/list, detail, and form patterns from existing UI

---

## Decision Drivers

- Complete the post-award flow for both buyer and supplier
- Follow existing App Router and component patterns
- Mobile-first for delivery-related pages
- Reuse existing shadcn/ui components
- Clear information hierarchy for operational data
- Export integration for finance pages

---

## Considered Options

### Option 1: Extend Existing Pages with Tabs/Sections
**Description:** Add order/delivery/invoice sections as tabs within existing RFQ detail or dashboard pages.

**Pros:**
- Fewer new pages to create
- Context stays on one page
- Less navigation

**Cons:**
- Overloads existing pages with too many concerns
- RFQ detail page becomes unwieldy
- Different user flows (buyer viewing invoices vs supplier submitting POD) forced into same page structure
- Breaks progressive disclosure principle

### Option 2: Dedicated Pages Per Entity (Chosen)
**Description:** Separate pages for orders, deliveries, invoices, disputes, and inventory — each following the existing list/detail pattern.

**Pros:**
- Clear separation of concerns
- Each page optimized for its specific workflow
- Follows existing navigation pattern (sidebar → list → detail)
- Mobile-optimized pages for delivery submission
- Easy to add, test, and iterate independently

**Cons:**
- More pages to build (~15 total)
- More navigation links in sidebar
- Some context switching between related pages

### Option 3: Single-Page Application with Dynamic Panels
**Description:** A unified operations dashboard with dynamic panels that load order, delivery, and invoice data based on context.

**Pros:**
- Rich, desktop-like experience
- Minimal page navigation
- Side-by-side comparisons easy

**Cons:**
- Complex state management
- Poor mobile experience
- Hard to deep-link to specific views
- Breaks existing App Router patterns

---

## Decision

**Chosen Option:** Dedicated Pages Per Entity

We implement dedicated pages for each post-award entity (orders, deliveries, invoices, disputes, inventory) following the established list → detail page pattern. Buyer and supplier get separate page sets optimized for their workflows.

### Rationale
The existing codebase uses dedicated pages per entity (RFQs, suppliers, products) with consistent list/detail patterns. Continuing this approach for post-award entities provides consistency, testability, and clear separation. Delivery pages are designed mobile-first since they're used at port by delivery staff.

---

## Consequences

### Positive
- Consistent with existing UI architecture
- Each page is independently developable and testable
- Mobile-first delivery pages optimized for port use
- Clear navigation and deep-linking
- Progressive disclosure — users see only what they need

### Negative
- ~15 new pages to build and maintain
- **Mitigation:** Shared components (StatusBadge, DataTable, DetailPanel) reduce duplication
- More sidebar navigation items
- **Mitigation:** Grouped under "Operations" and "Finance" sections

### Risks
- Information fragmentation across pages: Cross-links between related entities (order → delivery → invoice)
- Mobile UX for camera/GPS/signature: Use native browser APIs, progressive enhancement
- Page load performance with many new routes: Lazy loading via Next.js dynamic imports, React Query prefetching

---

## Implementation Notes

### Page Map

#### Buyer Pages (`apps/web/app/(dashboard)/`)

| Route | Page | Purpose | Data Source |
|-------|------|---------|-------------|
| `/orders` | Order List | All orders with status filters | FN-022 |
| `/orders/[id]` | Order Detail | Order with vendor orders, fulfillments, line items | FN-022 |
| `/deliveries` | Delivery List | All deliveries with status/date filters | FN-025 |
| `/deliveries/[id]` | Delivery Detail | Delivery with POD evidence, items, photos | FN-025 |
| `/deliveries/[id]/accept` | Delivery Acceptance | Accept/dispute with quantity verification | FN-025, FN-026 |
| `/invoices` | Invoice List | All invoices with status/period filters | FN-027 |
| `/invoices/[id]` | Invoice Detail | Invoice with line items, reconciliation view | FN-027 |
| `/disputes` | Dispute List | All disputes with status filters | FN-026 |
| `/disputes/[id]` | Dispute Detail | Dispute with comment trail | FN-026 |
| `/settlements` | Settlement Dashboard | Settlement periods with totals and export | FN-027, FN-028 |

#### Supplier Pages (`apps/web/app/(supplier)/supplier/`)

| Route | Page | Purpose | Data Source |
|-------|------|---------|-------------|
| `/orders` | Order List | Confirmed orders (replace "Coming Soon") | FN-022 |
| `/orders/[id]` | Order Detail | Order items, prepare fulfillment | FN-022 |
| `/deliveries` | Delivery List | Deliveries to manage | FN-025 |
| `/deliveries/[id]/submit` | Delivery Submission | Mobile-first: GPS, photos, signature, quantities | FN-025 |
| `/inventory` | Inventory Dashboard | Stock levels with low-stock alerts | FN-029 |
| `/invoices` | Invoice List | Generated invoices and payment status | FN-027 |

### Key UI Components

#### Delivery Submission (Mobile-First)

```
┌─────────────────────────────┐
│ 📦 Submit Delivery          │
│ Order: ORD-2026-001234      │
│ Vessel: MV Pacific Star     │
├─────────────────────────────┤
│                             │
│ 📍 Location                 │
│ [Capture GPS] ✓ Captured    │
│ Lat: 18.9388 Lng: 72.8354   │
│                             │
│ 📸 Photos (tap to add)      │
│ [📷] [📷] [📷] [+]          │
│                             │
│ ✏️ Items Delivered           │
│ ┌───────────────────────┐   │
│ │ IMPA 123456          │   │
│ │ Marine Paint White    │   │
│ │ Ordered: 100 units   │   │
│ │ Delivered: [___100__] │   │
│ └───────────────────────┘   │
│ ┌───────────────────────┐   │
│ │ IMPA 234567          │   │
│ │ Safety Rope 12mm     │   │
│ │ Ordered: 50 units    │   │
│ │ Delivered: [____48__] │   │
│ └───────────────────────┘   │
│                             │
│ ✍️ Receiver Signature        │
│ ┌───────────────────────┐   │
│ │                       │   │
│ │   [Signature Canvas]  │   │
│ │                       │   │
│ └───────────────────────┘   │
│ Name: [________________]    │
│ Designation: [_________]    │
│                             │
│ [Submit Delivery]           │
└─────────────────────────────┘
```

#### Reconciliation View (Invoice Detail)

```
┌──────────────────────────────────────────────────────────────┐
│ Invoice INV-2026-000123          Status: READY               │
│ Supplier: ABC Marine Supplies    Due: 15 Feb 2026           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ IMPA    │ Product          │ Ordered │ Delivered │ Accepted │ Unit   │ Total    │
│─────────┼──────────────────┼─────────┼───────────┼──────────┼────────┼──────────│
│ 123456  │ Marine Paint     │ 100     │ 100       │ 100      │ $12.50 │ $1,250   │
│ 234567  │ Safety Rope 12mm │ 50      │ 48        │ 48       │ $8.00  │ $384     │
│ 345678  │ First Aid Kit    │ 25      │ 25        │ 20       │ $45.00 │ $900     │
│         │                  │         │           │ ⚠ 5 rej  │        │ -$225 cr │
│─────────┴──────────────────┴─────────┴───────────┴──────────┴────────┼──────────│
│                                                    Subtotal          │ $2,309   │
│                                                    Tax (18% GST)     │ $415.62  │
│                                                    Credit Adj.       │ -$225.00 │
│                                                    ─────────────────────────────│
│                                                    TOTAL             │ $2,499.62│
│                                                                      │          │
│ [📥 Export PDF]  [📥 Export Excel]  [✅ Acknowledge]                 │          │
└──────────────────────────────────────────────────────────────────────┘
```

### Navigation Structure

#### Buyer Sidebar Additions
```
Operations
├── Orders          (new)
├── Deliveries      (new)
└── Disputes        (new)

Finance
├── Invoices        (new)
├── Settlements     (new)
└── Export          (links to export within invoice/settlement)
```

#### Supplier Sidebar Updates
```
Orders              (replace "Coming Soon" → real page)
Deliveries          (new)
Inventory           (new)
Invoices            (new)
```

### Shared Components

| Component | Used By | Purpose |
|-----------|---------|---------|
| `StatusBadge` | All list pages | Colored badge for entity status |
| `QuantityComparison` | Delivery, Invoice | Show ordered vs delivered vs accepted |
| `TimelineTracker` | Order, Delivery detail | Visual status progression |
| `PhotoGallery` | Delivery detail | Display delivery photos with lightbox |
| `SignatureCanvas` | Delivery submission | HTML5 canvas for signature capture |
| `GPSCapture` | Delivery submission | Geolocation capture with accuracy display |
| `ReconciliationTable` | Invoice detail | Three-column comparison table |
| `ExportButton` | Invoice, Settlement | Trigger export with format selector |
| `DisputeThread` | Dispute detail | Comment trail with attachments |

### Implementation Waves

| Wave | Pages | Depends On |
|------|-------|-----------|
| Wave 1 | Buyer Order List/Detail, Supplier Order List/Detail | Phase 4.4 (FN-022 API) |
| Wave 2 | Supplier Delivery Submission, Buyer Delivery List/Detail/Accept | Phase 4.5 (FN-025 API) |
| Wave 3 | Buyer Invoice List/Detail, Supplier Invoice List, Settlement Dashboard | Phase 5.3 (FN-027 API) |
| Wave 4 | Supplier Inventory, Buyer/Supplier Dispute pages, Export integration | Phase 3.5 + 4.6 + 5.4 |

### Dependencies
- ADR-UI-001: Next.js 14+ App Router (routing pattern)
- ADR-UI-002: Component Library shadcn/ui (component foundation)
- ADR-UI-003: State Management (React Query for server state)
- ADR-UI-013: PortiQ Buyer Experience (buyer page layout)
- ADR-UI-014: PortiQ Supplier Experience (supplier page layout)
- ADR-FN-022: Order Lifecycle & Fulfillment (order API)
- ADR-FN-025: Delivery & Proof-of-Delivery (delivery API)
- ADR-FN-026: Dispute Resolution Workflow (dispute API)
- ADR-FN-027: Settlement & Invoice Generation (invoice API)
- ADR-FN-028: Data Export Service (export API)
- ADR-FN-029: Basic Inventory & Stock Levels (inventory API)

### Migration Strategy
1. Wave 1: Build buyer + supplier order pages (requires FN-022 API)
2. Wave 2: Build delivery submission and review pages (requires FN-025 API)
3. Wave 3: Build invoice and settlement pages (requires FN-027 API)
4. Wave 4: Build inventory and dispute pages (requires FN-026, FN-029 APIs)
5. Each wave adds sidebar navigation items incrementally
6. Shared components built in Wave 1, reused across all waves

---

## References
- [ADR-UI-013: PortiQ Buyer Experience](ADR-UI-013-portiq-buyer-experience.md)
- [ADR-UI-014: PortiQ Supplier Experience](ADR-UI-014-portiq-supplier-experience.md)
- [Next.js App Router](https://nextjs.org/docs/app)
- [shadcn/ui Components](https://ui.shadcn.com/)
- [HTML5 Canvas Signature](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API)
- [Geolocation API](https://developer.mozilla.org/en-US/docs/Web/API/Geolocation_API)
