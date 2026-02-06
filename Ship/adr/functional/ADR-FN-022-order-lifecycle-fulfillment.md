# ADR-FN-022: Order Lifecycle & Fulfillment

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

The platform requires a comprehensive order lifecycle management system from quote acceptance through delivery and completion, handling the complexities of maritime fulfillment.

### Business Context
Maritime order fulfillment presents unique challenges:
- Delivery to moving vessels at port
- Time-sensitive coordination with ship schedules
- Multiple delivery locations (alongside, warehouse, agent)
- Partial fulfillment common for large orders
- Quality verification on delivery
- Documentation requirements (delivery notes, certificates)

### Technical Context
- Integration with RFQ workflow (ADR-FN-011)
- Marketplace framework for multi-vendor orders (ADR-FN-015)
- Real-time tracking via AIS (ADR-FN-019)
- Event-driven notifications (ADR-NF-009)
- Saga pattern for complex fulfillment flows (ADR-NF-010)

### Assumptions
- Orders may span multiple suppliers
- Partial delivery is acceptable and common
- Delivery confirmation from vessel required
- Quality disputes need resolution process

---

## Decision Drivers

- Clear visibility into order status
- Support for partial fulfillment
- Multi-vendor order coordination
- Integration with vessel schedules
- Dispute resolution capability
- Audit trail for compliance

---

## Considered Options

### Option 1: Simple Linear Workflow
**Description:** Fixed sequential states from order to delivery.

**Pros:**
- Simple implementation
- Easy to understand
- Clear progression

**Cons:**
- No partial fulfillment support
- Rigid state transitions
- Doesn't handle exceptions well

### Option 2: Hierarchical Order/Fulfillment Model
**Description:** Separate order and fulfillment lifecycles with line-item level tracking.

**Pros:**
- Supports partial fulfillment
- Line-item granularity
- Multi-vendor capable
- Flexible state management

**Cons:**
- More complex data model
- Multiple status levels to track
- UI complexity

### Option 3: Event-Sourced Order System
**Description:** Full event sourcing for order lifecycle.

**Pros:**
- Complete audit history
- Replay capability
- Flexible querying

**Cons:**
- High implementation complexity
- Infrastructure overhead
- Overkill for current needs

---

## Decision

**Chosen Option:** Hierarchical Order/Fulfillment Model

We will implement a hierarchical model with Order → Vendor Orders → Fulfillment → Line Items, enabling partial fulfillment, multi-vendor coordination, and line-item level tracking.

### Rationale
Maritime fulfillment complexity requires line-item level tracking for partial deliveries and multi-vendor coordination. The hierarchical model provides necessary granularity while maintaining clear aggregate order status through rollup logic.

---

## Consequences

### Positive
- Supports partial fulfillment naturally
- Multi-vendor orders handled correctly
- Line-item level tracking
- Clear status at each level
- Flexible for maritime scenarios

### Negative
- More complex data model
- **Mitigation:** Clear aggregation rules, status rollup logic
- Multiple status levels to display
- **Mitigation:** Thoughtful UI design, progressive disclosure

### Risks
- Status inconsistency across levels: Automatic rollup, validation rules
- Complex partial delivery tracking: Clear fulfillment records, audit trail
- Dispute resolution complexity: Defined workflow, escalation paths

---

## Implementation Notes

### Order Model Hierarchy

```
┌────────────────────────────────────────────────────────────────────┐
│                             ORDER                                   │
│                                                                     │
│  order_number: ORD-2024-001234                                     │
│  buyer_org_id: uuid                                                │
│  status: PARTIALLY_FULFILLED                                        │
│  total_amount: $15,000                                             │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    VENDOR ORDER (Supplier A)                  │  │
│  │                                                               │  │
│  │  vendor_order_number: VO-001-A                               │  │
│  │  supplier_id: uuid                                           │  │
│  │  status: FULFILLED                                           │  │
│  │  amount: $8,000                                              │  │
│  │                                                               │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │  FULFILLMENT #1                                         │ │  │
│  │  │  status: DELIVERED                                      │ │  │
│  │  │  delivery_date: 2024-01-15                              │ │  │
│  │  │                                                         │ │  │
│  │  │  Line Items:                                            │ │  │
│  │  │  - IMPA 123456: 100 units (DELIVERED)                   │ │  │
│  │  │  - IMPA 234567: 50 units (DELIVERED)                    │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    VENDOR ORDER (Supplier B)                  │  │
│  │                                                               │  │
│  │  vendor_order_number: VO-001-B                               │  │
│  │  supplier_id: uuid                                           │  │
│  │  status: IN_TRANSIT                                          │  │
│  │  amount: $7,000                                              │  │
│  │                                                               │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │  FULFILLMENT #1 (Partial)                               │ │  │
│  │  │  status: DELIVERED                                      │ │  │
│  │  │                                                         │ │  │
│  │  │  Line Items:                                            │ │  │
│  │  │  - IMPA 345678: 30 of 50 units (DELIVERED)              │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  │                                                               │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │  FULFILLMENT #2 (Remaining)                             │ │  │
│  │  │  status: IN_TRANSIT                                     │ │  │
│  │  │                                                         │ │  │
│  │  │  Line Items:                                            │ │  │
│  │  │  - IMPA 345678: 20 units (IN_TRANSIT)                   │ │  │
│  │  │  - IMPA 456789: 75 units (IN_TRANSIT)                   │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Status Definitions

```typescript
// order/enums/order-status.enum.ts
export enum OrderStatus {
  PENDING_PAYMENT = 'PENDING_PAYMENT',
  CONFIRMED = 'CONFIRMED',
  PROCESSING = 'PROCESSING',
  PARTIALLY_FULFILLED = 'PARTIALLY_FULFILLED',
  FULFILLED = 'FULFILLED',
  COMPLETED = 'COMPLETED',  // Delivered and accepted
  CANCELLED = 'CANCELLED',
  DISPUTED = 'DISPUTED'
}

export enum VendorOrderStatus {
  PENDING_CONFIRMATION = 'PENDING_CONFIRMATION',
  CONFIRMED = 'CONFIRMED',
  PREPARING = 'PREPARING',
  READY_FOR_PICKUP = 'READY_FOR_PICKUP',
  IN_TRANSIT = 'IN_TRANSIT',
  DELIVERED = 'DELIVERED',
  FULFILLED = 'FULFILLED',  // Fully delivered and accepted
  CANCELLED = 'CANCELLED',
  DISPUTED = 'DISPUTED'
}

export enum FulfillmentStatus {
  PENDING = 'PENDING',
  PICKING = 'PICKING',
  PACKED = 'PACKED',
  SHIPPED = 'SHIPPED',
  IN_TRANSIT = 'IN_TRANSIT',
  OUT_FOR_DELIVERY = 'OUT_FOR_DELIVERY',
  DELIVERED = 'DELIVERED',
  ACCEPTED = 'ACCEPTED',
  REJECTED = 'REJECTED',
  PARTIALLY_ACCEPTED = 'PARTIALLY_ACCEPTED'
}

export enum LineItemStatus {
  PENDING = 'PENDING',
  ALLOCATED = 'ALLOCATED',
  PICKED = 'PICKED',
  PACKED = 'PACKED',
  SHIPPED = 'SHIPPED',
  DELIVERED = 'DELIVERED',
  ACCEPTED = 'ACCEPTED',
  REJECTED = 'REJECTED',
  BACKORDERED = 'BACKORDERED',
  CANCELLED = 'CANCELLED'
}
```

### Database Schema

```sql
-- Orders (aggregate)
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number VARCHAR(50) UNIQUE NOT NULL,
    rfq_id UUID REFERENCES rfqs(id),
    buyer_org_id UUID REFERENCES organizations(id),

    status VARCHAR(30) NOT NULL DEFAULT 'PENDING_PAYMENT',
    total_amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',

    -- Delivery details
    delivery_port VARCHAR(10),
    vessel_imo VARCHAR(10),
    vessel_name VARCHAR(100),
    requested_delivery_date DATE,

    -- Payment
    payment_status VARCHAR(20),
    payment_method VARCHAR(30),
    payment_reference VARCHAR(100),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vendor Orders (per supplier)
CREATE TABLE vendor_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_order_number VARCHAR(50) UNIQUE NOT NULL,
    order_id UUID REFERENCES orders(id),
    supplier_id UUID REFERENCES suppliers(id),

    status VARCHAR(30) NOT NULL DEFAULT 'PENDING_CONFIRMATION',
    amount DECIMAL(15, 2) NOT NULL,
    commission_rate DECIMAL(5, 2),
    commission_amount DECIMAL(15, 2),

    confirmed_at TIMESTAMPTZ,
    estimated_ready_date DATE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Fulfillments (shipments)
CREATE TABLE fulfillments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fulfillment_number VARCHAR(50) UNIQUE NOT NULL,
    vendor_order_id UUID REFERENCES vendor_orders(id),

    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',

    -- Shipping details
    carrier VARCHAR(100),
    tracking_number VARCHAR(100),
    shipped_at TIMESTAMPTZ,
    estimated_delivery TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,

    -- Delivery location
    delivery_type VARCHAR(20),  -- ALONGSIDE, WAREHOUSE, AGENT
    delivery_address TEXT,
    delivery_contact VARCHAR(100),
    delivery_phone VARCHAR(20),

    -- Acceptance
    accepted_at TIMESTAMPTZ,
    accepted_by VARCHAR(100),
    acceptance_notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Fulfillment Line Items
CREATE TABLE fulfillment_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fulfillment_id UUID REFERENCES fulfillments(id),
    order_line_item_id UUID REFERENCES order_line_items(id),

    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    quantity_shipped INTEGER NOT NULL,
    quantity_delivered INTEGER,
    quantity_accepted INTEGER,
    quantity_rejected INTEGER,

    rejection_reason TEXT,
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Order Line Items (detailed products)
CREATE TABLE order_line_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_order_id UUID REFERENCES vendor_orders(id),
    product_id UUID REFERENCES products(id),

    impa_code CHAR(6) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    quantity_ordered INTEGER NOT NULL,
    quantity_fulfilled INTEGER DEFAULT 0,
    quantity_accepted INTEGER DEFAULT 0,
    unit_price DECIMAL(12, 2) NOT NULL,
    line_total DECIMAL(15, 2) NOT NULL,

    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Status rollup function
CREATE OR REPLACE FUNCTION update_order_status()
RETURNS TRIGGER AS $$
BEGIN
    -- Update vendor order status based on fulfillments
    UPDATE vendor_orders vo
    SET status = (
        CASE
            WHEN NOT EXISTS (
                SELECT 1 FROM fulfillments f WHERE f.vendor_order_id = vo.id
            ) THEN vo.status
            WHEN EXISTS (
                SELECT 1 FROM fulfillments f
                WHERE f.vendor_order_id = vo.id AND f.status = 'DISPUTED'
            ) THEN 'DISPUTED'
            WHEN NOT EXISTS (
                SELECT 1 FROM fulfillments f
                WHERE f.vendor_order_id = vo.id AND f.status != 'ACCEPTED'
            ) THEN 'FULFILLED'
            WHEN EXISTS (
                SELECT 1 FROM fulfillments f
                WHERE f.vendor_order_id = vo.id AND f.status = 'DELIVERED'
            ) THEN 'DELIVERED'
            WHEN EXISTS (
                SELECT 1 FROM fulfillments f
                WHERE f.vendor_order_id = vo.id AND f.status = 'IN_TRANSIT'
            ) THEN 'IN_TRANSIT'
            ELSE vo.status
        END
    )
    WHERE vo.id = NEW.vendor_order_id;

    -- Update parent order status
    UPDATE orders o
    SET status = (
        SELECT
            CASE
                WHEN bool_and(vo.status = 'FULFILLED') THEN 'FULFILLED'
                WHEN bool_or(vo.status = 'DISPUTED') THEN 'DISPUTED'
                WHEN bool_or(vo.status IN ('DELIVERED', 'FULFILLED')) AND
                     bool_or(vo.status NOT IN ('DELIVERED', 'FULFILLED', 'CANCELLED'))
                THEN 'PARTIALLY_FULFILLED'
                WHEN bool_or(vo.status = 'IN_TRANSIT') THEN 'PROCESSING'
                ELSE o.status
            END
        FROM vendor_orders vo
        WHERE vo.order_id = o.id
    )
    WHERE o.id = (SELECT order_id FROM vendor_orders WHERE id = NEW.vendor_order_id);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER fulfillment_status_trigger
AFTER UPDATE OF status ON fulfillments
FOR EACH ROW
EXECUTE FUNCTION update_order_status();
```

### Order Service

```typescript
// order/services/order.service.ts
@Injectable()
export class OrderService {
  constructor(
    private readonly orderRepository: OrderRepository,
    private readonly vendorOrderRepository: VendorOrderRepository,
    private readonly fulfillmentRepository: FulfillmentRepository,
    private readonly eventEmitter: EventEmitter2
  ) {}

  async createFromQuote(
    rfqId: string,
    quoteSelections: QuoteSelection[]
  ): Promise<Order> {
    return await this.orderRepository.transaction(async (tx) => {
      // Create parent order
      const orderNumber = await this.generateOrderNumber();
      const order = await tx.order.create({
        data: {
          orderNumber,
          rfqId,
          buyerOrgId: quoteSelections[0].buyerOrgId,
          status: OrderStatus.PENDING_PAYMENT,
          totalAmount: quoteSelections.reduce((sum, qs) => sum + qs.amount, 0)
        }
      });

      // Create vendor orders for each selected quote
      for (const selection of quoteSelections) {
        const vendorOrderNumber = `${orderNumber}-${selection.supplierId.slice(-4)}`;

        const vendorOrder = await tx.vendorOrder.create({
          data: {
            vendorOrderNumber,
            orderId: order.id,
            supplierId: selection.supplierId,
            status: VendorOrderStatus.PENDING_CONFIRMATION,
            amount: selection.amount,
            commissionRate: selection.commissionRate,
            commissionAmount: selection.amount * selection.commissionRate / 100
          }
        });

        // Create line items
        for (const item of selection.lineItems) {
          await tx.orderLineItem.create({
            data: {
              vendorOrderId: vendorOrder.id,
              productId: item.productId,
              impaCode: item.impaCode,
              productName: item.productName,
              quantityOrdered: item.quantity,
              unitPrice: item.unitPrice,
              lineTotal: item.quantity * item.unitPrice,
              status: LineItemStatus.PENDING
            }
          });
        }
      }

      return order;
    });
  }

  async createFulfillment(
    vendorOrderId: string,
    fulfillmentData: CreateFulfillmentDto
  ): Promise<Fulfillment> {
    const vendorOrder = await this.vendorOrderRepository.findById(vendorOrderId);

    // Validate quantities
    for (const item of fulfillmentData.items) {
      const lineItem = await this.orderLineItemRepository.findById(item.lineItemId);
      const remainingQuantity = lineItem.quantityOrdered - lineItem.quantityFulfilled;

      if (item.quantity > remainingQuantity) {
        throw new BadRequestException(
          `Cannot ship ${item.quantity} units of ${lineItem.productName}. ` +
          `Only ${remainingQuantity} remaining.`
        );
      }
    }

    // Create fulfillment
    const fulfillment = await this.fulfillmentRepository.transaction(async (tx) => {
      const fulfillmentNumber = await this.generateFulfillmentNumber();

      const fulfillment = await tx.fulfillment.create({
        data: {
          fulfillmentNumber,
          vendorOrderId,
          status: FulfillmentStatus.PENDING,
          deliveryType: fulfillmentData.deliveryType,
          deliveryAddress: fulfillmentData.deliveryAddress,
          carrier: fulfillmentData.carrier
        }
      });

      for (const item of fulfillmentData.items) {
        await tx.fulfillmentItem.create({
          data: {
            fulfillmentId: fulfillment.id,
            orderLineItemId: item.lineItemId,
            quantityShipped: item.quantity,
            status: LineItemStatus.ALLOCATED
          }
        });

        // Update line item fulfilled quantity
        await tx.orderLineItem.update({
          where: { id: item.lineItemId },
          data: {
            quantityFulfilled: {
              increment: item.quantity
            }
          }
        });
      }

      return fulfillment;
    });

    this.eventEmitter.emit('fulfillment.created', { fulfillment, vendorOrder });

    return fulfillment;
  }

  async recordDelivery(
    fulfillmentId: string,
    deliveryData: DeliveryRecordDto
  ): Promise<Fulfillment> {
    const fulfillment = await this.fulfillmentRepository.findById(fulfillmentId);

    await this.fulfillmentRepository.update(fulfillmentId, {
      status: FulfillmentStatus.DELIVERED,
      deliveredAt: new Date(),
      acceptedBy: deliveryData.receivedBy
    });

    // Update item quantities
    for (const item of deliveryData.items) {
      await this.fulfillmentItemRepository.update(item.fulfillmentItemId, {
        quantityDelivered: item.quantityReceived,
        quantityAccepted: item.quantityAccepted,
        quantityRejected: item.quantityRejected,
        rejectionReason: item.rejectionReason,
        status: item.quantityRejected > 0
          ? LineItemStatus.REJECTED
          : LineItemStatus.ACCEPTED
      });
    }

    // Update fulfillment status based on acceptance
    const hasRejections = deliveryData.items.some(i => i.quantityRejected > 0);
    const allRejected = deliveryData.items.every(
      i => i.quantityAccepted === 0 && i.quantityRejected > 0
    );

    await this.fulfillmentRepository.update(fulfillmentId, {
      status: allRejected
        ? FulfillmentStatus.REJECTED
        : hasRejections
          ? FulfillmentStatus.PARTIALLY_ACCEPTED
          : FulfillmentStatus.ACCEPTED,
      acceptedAt: new Date(),
      acceptanceNotes: deliveryData.notes
    });

    this.eventEmitter.emit('fulfillment.delivered', {
      fulfillmentId,
      hasRejections
    });

    return this.fulfillmentRepository.findById(fulfillmentId);
  }

  async getOrderDetails(orderId: string): Promise<OrderDetailsDto> {
    const order = await this.orderRepository.findById(orderId);
    const vendorOrders = await this.vendorOrderRepository.findByOrderId(orderId);

    const vendorOrderDetails = await Promise.all(
      vendorOrders.map(async (vo) => {
        const fulfillments = await this.fulfillmentRepository.findByVendorOrderId(vo.id);
        const lineItems = await this.orderLineItemRepository.findByVendorOrderId(vo.id);

        return {
          ...vo,
          fulfillments: await Promise.all(
            fulfillments.map(async (f) => ({
              ...f,
              items: await this.fulfillmentItemRepository.findByFulfillmentId(f.id)
            }))
          ),
          lineItems
        };
      })
    );

    return {
      order,
      vendorOrders: vendorOrderDetails,
      fulfillmentSummary: this.calculateFulfillmentSummary(vendorOrderDetails)
    };
  }
}
```

### Dependencies
- ADR-FN-011: RFQ Workflow State Machine
- ADR-FN-015: Marketplace Framework
- ADR-NF-009: Event-Driven Communication
- ADR-NF-010: Saga Pattern for Transactions

### Migration Strategy
1. Create order schema and tables
2. Implement order creation from quotes
3. Build fulfillment workflow
4. Add delivery confirmation system
5. Implement status rollup triggers
6. Create order tracking UI
7. Add dispute resolution workflow

---

## Operational Considerations

### Partial Fulfillment, Backorders, and Cancellations

#### Partial Fulfillment Handling

| Scenario | System Behavior | Status Transition | Financial Impact |
|----------|-----------------|-------------------|------------------|
| Partial shipment (supplier ships less than ordered) | Create fulfillment with partial quantities; remaining stays as `PENDING` | Vendor Order: `IN_TRANSIT`, Line Item: `PARTIALLY_SHIPPED` | Invoice only for shipped quantity |
| Split shipment (multiple deliveries planned) | Multiple fulfillment records per vendor order | Aggregate status based on all fulfillments | Separate invoices per fulfillment or consolidated |
| Quantity shortage at delivery | Record `quantity_delivered` < `quantity_shipped` | Fulfillment: `PARTIALLY_ACCEPTED` | Credit note for shortage |
| Quality rejection | Record `quantity_rejected` with reason | Line Item: `REJECTED`, triggers dispute | Credit note or replacement fulfillment |

```typescript
// Partial fulfillment state machine
interface PartialFulfillmentRules {
  // Minimum fulfillment percentage before auto-cancellation of remainder
  minFulfillmentPercent: 80;
  // Days to wait for remaining items before creating backorder
  backorderGracePeriodDays: 14;
  // Auto-close partially fulfilled orders after this period
  autoCloseAfterDays: 30;
}

// Backorder handling
async function handleBackorder(lineItem: OrderLineItem): Promise<BackorderResult> {
  const remainingQty = lineItem.quantityOrdered - lineItem.quantityFulfilled;

  if (remainingQty > 0 && lineItem.backorderEligible) {
    return {
      action: 'CREATE_BACKORDER',
      backorder: {
        originalOrderId: lineItem.vendorOrder.orderId,
        productId: lineItem.productId,
        quantity: remainingQty,
        priority: 'HIGH',
        notifyWhenAvailable: true
      }
    };
  }
  return { action: 'CANCEL_REMAINDER', refundAmount: remainingQty * lineItem.unitPrice };
}
```

#### Cancellation Matrix

| Cancellation Initiator | Order Status | Allowed Actions | Penalty/Fees |
|------------------------|--------------|-----------------|--------------|
| Buyer | `PENDING_PAYMENT` | Full cancel | None |
| Buyer | `CONFIRMED` (within 24h) | Full cancel | None |
| Buyer | `CONFIRMED` (after 24h) | Cancel with fee | 5% restocking fee |
| Buyer | `PROCESSING`/`IN_TRANSIT` | Request cancel | Supplier approval required, shipping costs |
| Supplier | `CONFIRMED` | Full cancel | Platform penalty (rating impact) |
| Supplier | `PREPARING` | Partial cancel (out of stock) | Credit + notification |
| System | Any | Force cancel (fraud, dispute) | Full refund + investigation |

### Event Contracts and Reconciliation for Financial Accuracy

#### Domain Events

```typescript
// Order lifecycle events with financial implications
interface OrderEvents {
  // Creation
  'order.created': {
    orderId: string;
    totalAmount: number;
    currency: string;
    paymentMethod: string;
    vendorOrders: { supplierId: string; amount: number; commissionRate: number }[];
  };

  // Payment
  'order.payment.received': {
    orderId: string;
    paymentId: string;
    amount: number;
    paymentReference: string;
    receivedAt: Date;
  };

  // Fulfillment
  'fulfillment.shipped': {
    fulfillmentId: string;
    vendorOrderId: string;
    lineItems: { productId: string; quantity: number; unitPrice: number }[];
    carrier: string;
    trackingNumber: string;
    estimatedDelivery: Date;
  };

  'fulfillment.delivered': {
    fulfillmentId: string;
    deliveredAt: Date;
    receivedBy: string;
    acceptedItems: { lineItemId: string; quantityAccepted: number }[];
    rejectedItems: { lineItemId: string; quantityRejected: number; reason: string }[];
  };

  // Financial
  'invoice.generated': {
    invoiceId: string;
    vendorOrderId: string;
    amount: number;
    dueDate: Date;
  };

  'settlement.initiated': {
    settlementId: string;
    supplierId: string;
    grossAmount: number;
    commissionAmount: number;
    netAmount: number;
    invoiceIds: string[];
  };
}
```

#### Daily Reconciliation Process

```sql
-- Daily financial reconciliation query
WITH order_totals AS (
  SELECT
    DATE(created_at) as order_date,
    SUM(total_amount) as total_orders,
    COUNT(*) as order_count
  FROM orders
  WHERE status NOT IN ('CANCELLED')
  GROUP BY DATE(created_at)
),
payment_totals AS (
  SELECT
    DATE(received_at) as payment_date,
    SUM(amount) as total_payments,
    COUNT(*) as payment_count
  FROM payments
  WHERE status = 'COMPLETED'
  GROUP BY DATE(received_at)
),
fulfillment_totals AS (
  SELECT
    DATE(delivered_at) as delivery_date,
    SUM(fi.quantity_accepted * oli.unit_price) as delivered_value
  FROM fulfillment_items fi
  JOIN order_line_items oli ON fi.order_line_item_id = oli.id
  JOIN fulfillments f ON fi.fulfillment_id = f.id
  WHERE f.status = 'ACCEPTED'
  GROUP BY DATE(delivered_at)
),
settlement_totals AS (
  SELECT
    DATE(settled_at) as settlement_date,
    SUM(gross_amount) as gross_settled,
    SUM(commission_amount) as commission_collected,
    SUM(net_amount) as net_to_suppliers
  FROM settlements
  WHERE status = 'COMPLETED'
  GROUP BY DATE(settled_at)
)
SELECT
  COALESCE(o.order_date, p.payment_date, f.delivery_date, s.settlement_date) as date,
  o.total_orders,
  p.total_payments,
  f.delivered_value,
  s.gross_settled,
  s.commission_collected,
  -- Reconciliation checks
  (p.total_payments - o.total_orders) as payment_variance,
  (f.delivered_value - s.gross_settled) as settlement_variance
FROM order_totals o
FULL OUTER JOIN payment_totals p ON o.order_date = p.payment_date
FULL OUTER JOIN fulfillment_totals f ON o.order_date = f.delivery_date
FULL OUTER JOIN settlement_totals s ON o.order_date = s.settlement_date
ORDER BY date DESC;
```

#### Financial State Synchronization

| Event | Financial System Update | Accounting Entry |
|-------|------------------------|------------------|
| Order confirmed | Create receivable from buyer | DR: Accounts Receivable, CR: Deferred Revenue |
| Payment received | Clear receivable, escrow funds | DR: Cash/Bank, CR: Accounts Receivable |
| Goods delivered | Recognize revenue, create payable | DR: Deferred Revenue, CR: Revenue + Commission + Payable |
| Settlement paid | Clear supplier payable | DR: Accounts Payable, CR: Cash/Bank |
| Refund issued | Reverse entries | DR: Revenue/Deferred Revenue, CR: Cash/Bank |

### Open Questions

- **Q:** How are disputes or returns integrated into the lifecycle?
  - **A:** Disputes and returns follow a dedicated workflow:

  **Dispute Types and Handling:**
  | Dispute Type | Trigger | Resolution Path | SLA |
  |--------------|---------|-----------------|-----|
  | Quantity shortage | `quantity_delivered` < `quantity_shipped` | Auto-create credit note | Immediate |
  | Quality rejection | Delivery acceptance with rejections | Review queue + supplier response | 48 hours |
  | Wrong product | Buyer reports mismatch | Investigation + return authorization | 72 hours |
  | Damaged goods | Delivery inspection | Photo evidence + carrier claim | 5 business days |
  | Price dispute | Invoice discrepancy | Order audit + adjustment | 48 hours |

  **Return Flow:**
  ```
  RETURN_REQUESTED → RETURN_AUTHORIZED → GOODS_IN_TRANSIT →
  GOODS_RECEIVED → INSPECTION → REFUND_PROCESSED / REPLACEMENT_SHIPPED
  ```

  **Financial Integration:**
  - Disputes create `dispute` records linked to fulfillment items
  - Approved disputes generate credit notes automatically
  - Credit notes offset against future invoices or trigger refunds
  - Supplier rating adjusted based on dispute resolution outcome

---

## References
- [Order Management Systems](https://www.shopify.com/enterprise/order-management-system)
- [Fulfillment Patterns](https://docs.medusajs.com/modules/orders/fulfillment)
- [Maritime Delivery Standards](https://www.bimco.org/)
