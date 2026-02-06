# ADR-FN-015: Marketplace Framework

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

The platform requires a marketplace framework to orchestrate multi-vendor commerce, including unified checkout, payment splitting, commission handling, and vendor management.

### Business Context
The maritime chandlery marketplace connects buyers (shipping companies) with multiple suppliers (chandlers). Key requirements include:
- Buyers may order from multiple suppliers in a single transaction
- Platform collects commission on transactions
- Payments must be split and routed to correct suppliers
- Order fulfillment is supplier-specific
- Returns and disputes need clear ownership

### Technical Context
- NestJS modular monolith architecture (ADR-NF-006)
- PostgreSQL for data persistence (ADR-NF-001)
- Need payment gateway integration for split payments
- Event-driven order processing (ADR-NF-009)
- Multi-tenant model for buyer/supplier organizations (ADR-FN-023)

### Assumptions
- Stripe Connect or similar will handle payment splitting
- Platform operates as marketplace, not merchant of record
- Commission rates may vary by supplier tier
- International payments needed (USD, EUR, INR)

---

## Decision Drivers

- Support for multi-vendor orders
- Automated payment splitting
- Commission management flexibility
- Extensible for future commerce features
- Developer productivity and time-to-market
- Open-source foundation to reduce vendor lock-in

---

## Considered Options

### Option 1: Custom Build
**Description:** Build marketplace functionality from scratch using NestJS modules.

**Pros:**
- Complete control over architecture
- No external dependencies
- Optimized for specific needs

**Cons:**
- Significant development effort
- Reinventing solved problems
- Longer time to market
- Maintenance burden

### Option 2: Medusa.js with Mercur Extension
**Description:** Use Medusa.js open-source commerce platform with Mercur marketplace extension.

**Pros:**
- Purpose-built for headless commerce
- Mercur adds multi-vendor capabilities
- Built-in workflow engine for sagas
- Active community and development
- Stripe Connect integration
- TypeScript/Node.js aligned with stack

**Cons:**
- Learning curve for Medusa patterns
- May have features we don't need
- Extension dependency

### Option 3: Shopify/BigCommerce Marketplace Apps
**Description:** Use established e-commerce platform with marketplace add-ons.

**Pros:**
- Mature platforms
- Rich ecosystem
- Hosted infrastructure

**Cons:**
- High transaction fees
- Less customizable
- Not optimized for B2B
- Vendor lock-in
- Limited API flexibility

### Option 4: Spree Commerce
**Description:** Use Spree open-source platform with marketplace extensions.

**Pros:**
- Mature open-source platform
- Ruby on Rails (proven stack)
- Multi-vendor support

**Cons:**
- Ruby/Rails not aligned with our stack
- Team would need to learn new framework
- Integration complexity with NestJS services

---

## Decision

**Chosen Option:** Medusa.js with Mercur Extension

We will use Medusa.js as the commerce foundation with the Mercur marketplace extension for multi-vendor capabilities, integrated with our NestJS backend services.

### Rationale
Medusa.js provides a modern, TypeScript-based commerce platform that aligns with our tech stack. The Mercur extension adds essential marketplace features (vendor dashboards, split payments, commission handling) without requiring custom development. The built-in workflow engine supports the saga pattern needed for complex multi-step transactions. This combination accelerates time-to-market while maintaining flexibility.

---

## Consequences

### Positive
- Accelerated development with proven commerce patterns
- Built-in multi-vendor and payment splitting
- Aligned with TypeScript/Node.js stack
- Extensible plugin architecture
- Active open-source community

### Negative
- Dependency on Medusa release cycle
- **Mitigation:** Pin versions, maintain fork if critical
- Learning curve for team
- **Mitigation:** Documentation, team training sessions
- Some features may be unnecessary
- **Mitigation:** Selective module inclusion

### Risks
- Medusa project abandonment: Large community, corporate backing; maintain fork capability
- Mercur extension incompatibility: Vendor communication, contribution to upstream
- Performance at scale: Load testing, optimization, caching layer

---

## Implementation Notes

### Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────┐     ┌─────────────────────────────┐   │
│  │   NestJS Services   │     │      Medusa.js Core         │   │
│  │                     │     │                             │   │
│  │  - RFQ Management   │────▶│  - Cart / Checkout         │   │
│  │  - Document AI      │     │  - Order Management        │   │
│  │  - TCO Engine       │     │  - Payment Processing      │   │
│  │  - Supplier KYC     │     │  - Inventory (optional)    │   │
│  │                     │     │                             │   │
│  └─────────────────────┘     └──────────────┬──────────────┘   │
│                                             │                   │
│                              ┌──────────────▼──────────────┐   │
│                              │    Mercur Extension         │   │
│                              │                             │   │
│                              │  - Vendor Management        │   │
│                              │  - Split Payments           │   │
│                              │  - Commission Handling      │   │
│                              │  - Vendor Dashboards        │   │
│                              │                             │   │
│                              └─────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Medusa Configuration

```typescript
// medusa-config.ts
const config = {
  projectConfig: {
    database_url: process.env.DATABASE_URL,
    database_type: 'postgres',
    store_cors: process.env.STORE_CORS,
    admin_cors: process.env.ADMIN_CORS,
    redis_url: process.env.REDIS_URL
  },
  plugins: [
    {
      resolve: '@mercurjs/medusa-plugin-mercur',
      options: {
        enableVendorDashboard: true,
        commissionDefault: 5, // 5% default commission
        paymentSplitEnabled: true,
        stripeConnectEnabled: true
      }
    },
    {
      resolve: 'medusa-payment-stripe',
      options: {
        api_key: process.env.STRIPE_SECRET_KEY,
        webhook_secret: process.env.STRIPE_WEBHOOK_SECRET
      }
    }
  ],
  featureFlags: {
    workflows: true,  // Enable workflow engine
    tax_inclusive_pricing: true
  }
};

export default config;
```

### Vendor (Supplier) Model Extension

```typescript
// src/models/vendor.ts
import { Entity, Column, OneToMany } from 'typeorm';
import { Vendor as MercurVendor } from '@mercurjs/medusa-plugin-mercur';

@Entity()
export class Vendor extends MercurVendor {
  @Column({ nullable: true })
  supplier_tier: string;  // Link to our supplier tier

  @Column({ type: 'jsonb', nullable: true })
  kyc_status: {
    verified: boolean;
    tier: string;
    verifiedAt: Date;
  };

  @Column({ type: 'decimal', precision: 5, scale: 2 })
  commission_rate: number;  // Override default commission

  @Column({ type: 'text', array: true, default: '{}' })
  service_ports: string[];  // Ports this vendor serves

  @Column({ type: 'text', array: true, default: '{}' })
  product_categories: string[];  // IMPA categories
}
```

### Order Workflow Integration

```typescript
// src/workflows/create-marketplace-order.ts
import { createWorkflow, WorkflowResponse } from '@medusajs/workflows-sdk';
import { createOrderStep, capturePaymentStep } from '@medusajs/medusa/core-flows';

export const createMarketplaceOrderWorkflow = createWorkflow(
  'create-marketplace-order',
  (input: CreateMarketplaceOrderInput) => {
    // Step 1: Validate RFQ award
    const rfqValidation = validateRfqAwardStep(input.rfqId, input.quoteId);

    // Step 2: Create orders per vendor
    const vendorOrders = createVendorOrdersStep({
      cartId: input.cartId,
      rfqId: input.rfqId
    });

    // Step 3: Calculate commissions
    const commissions = calculateCommissionsStep(vendorOrders);

    // Step 4: Process split payment
    const payment = processSplitPaymentStep({
      orders: vendorOrders,
      commissions,
      paymentMethod: input.paymentMethod
    });

    // Step 5: Notify vendors
    const notifications = notifyVendorsStep(vendorOrders);

    // Step 6: Update RFQ status
    const rfqUpdate = updateRfqStatusStep(input.rfqId, 'COMPLETED');

    return new WorkflowResponse({
      orders: vendorOrders,
      payment,
      rfqId: input.rfqId
    });
  }
);
```

### Commission Service

```typescript
// src/services/commission.service.ts
import { TransactionBaseService } from '@medusajs/medusa';

interface CommissionCalculation {
  orderId: string;
  vendorId: string;
  orderAmount: number;
  commissionRate: number;
  commissionAmount: number;
  netVendorAmount: number;
}

class CommissionService extends TransactionBaseService {
  async calculateCommission(
    orderId: string,
    vendorId: string,
    orderAmount: number
  ): Promise<CommissionCalculation> {
    const vendor = await this.vendorRepository.findById(vendorId);

    // Get commission rate (vendor-specific or default)
    const commissionRate = vendor.commission_rate ??
      this.getDefaultCommissionRate(vendor.supplier_tier);

    const commissionAmount = orderAmount * (commissionRate / 100);
    const netVendorAmount = orderAmount - commissionAmount;

    return {
      orderId,
      vendorId,
      orderAmount,
      commissionRate,
      commissionAmount,
      netVendorAmount
    };
  }

  private getDefaultCommissionRate(tier: string): number {
    const rates = {
      'BASIC': 5,
      'VERIFIED': 4,
      'PREFERRED': 3,
      'PREMIUM': 2
    };
    return rates[tier] ?? 5;
  }

  async recordCommission(calculation: CommissionCalculation): Promise<void> {
    await this.commissionRepository.create({
      ...calculation,
      status: 'PENDING',
      createdAt: new Date()
    });
  }
}
```

### Stripe Connect Integration

```typescript
// src/services/split-payment.service.ts
import Stripe from 'stripe';

interface SplitPaymentInput {
  totalAmount: number;
  currency: string;
  vendorPayments: {
    vendorId: string;
    stripeAccountId: string;
    amount: number;
  }[];
  platformFee: number;
}

class SplitPaymentService {
  private stripe: Stripe;

  constructor() {
    this.stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
  }

  async createSplitPayment(input: SplitPaymentInput): Promise<Stripe.PaymentIntent> {
    // Create payment intent with transfer group
    const transferGroup = `order_${Date.now()}`;

    const paymentIntent = await this.stripe.paymentIntents.create({
      amount: input.totalAmount,
      currency: input.currency,
      transfer_group: transferGroup,
      application_fee_amount: input.platformFee,
      metadata: {
        vendor_count: input.vendorPayments.length.toString()
      }
    });

    // Create transfers to each vendor
    for (const vendorPayment of input.vendorPayments) {
      await this.stripe.transfers.create({
        amount: vendorPayment.amount,
        currency: input.currency,
        destination: vendorPayment.stripeAccountId,
        transfer_group: transferGroup,
        metadata: {
          vendor_id: vendorPayment.vendorId
        }
      });
    }

    return paymentIntent;
  }
}
```

### NestJS Integration Module

```typescript
// src/modules/medusa-integration.module.ts
import { Module } from '@nestjs/common';

@Module({
  providers: [
    {
      provide: 'MEDUSA_CLIENT',
      useFactory: () => {
        const Medusa = require('@medusajs/medusa-js').default;
        return new Medusa({
          baseUrl: process.env.MEDUSA_BACKEND_URL,
          maxRetries: 3
        });
      }
    },
    MedusaSyncService,
    CommissionService,
    SplitPaymentService
  ],
  exports: ['MEDUSA_CLIENT', MedusaSyncService]
})
export class MedusaIntegrationModule {}
```

### Dependencies
- ADR-FN-011: RFQ Workflow State Machine
- ADR-FN-014: Supplier Onboarding & KYC
- ADR-FN-022: Order Lifecycle & Fulfillment
- ADR-NF-006: Modular Monolith vs Microservices
- ADR-NF-010: Saga Pattern for Transactions

### Migration Strategy
1. Set up Medusa.js with Mercur extension
2. Configure Stripe Connect for payments
3. Build integration layer with NestJS
4. Migrate vendor data from supplier model
5. Implement commission calculation
6. Create unified checkout flow
7. Build vendor dashboard views

---

## Operational Considerations

### Marketplace Model: Managed Marketplace

The platform operates as a **Managed Marketplace** with the following characteristics:

| Aspect | Model Choice | Rationale |
|--------|--------------|-----------|
| Curation | Verified suppliers only | Quality assurance for maritime industry |
| Pricing | Supplier-set with platform guidelines | Market-driven with floor protection |
| Fulfillment | Supplier-managed | Leverages existing logistics |
| Payments | Platform-processed | Trust, commission collection, financing |
| Disputes | Platform-arbitrated | Neutral third-party resolution |
| Support | Hybrid (self-service + platform) | Scalability with quality baseline |

#### Platform vs. Merchant of Record

| Scenario | Platform Role | Tax Responsibility | Invoice Issuer |
|----------|--------------|-------------------|----------------|
| Standard Order | Facilitator | Supplier | Supplier |
| Financed Order | Facilitator | Supplier | Supplier (platform guarantee) |
| Cross-Border (future) | Merchant of Record | Platform | Platform |

### Medusa.js Customization Strategy

#### Core Customizations

| Medusa Component | Customization | Implementation |
|------------------|---------------|----------------|
| Product Model | Extended with IMPA codes, vessel compatibility | Custom entity extending `Product` |
| Cart | Multi-vendor support, RFQ linkage | Mercur extension + custom fields |
| Checkout | Split payment, delivery port selection | Custom workflow steps |
| Order | Vessel assignment, delivery scheduling | Extended order entity |
| Customer | Organization model integration | Custom customer-organization link |
| Inventory | Port-based availability | Location-aware inventory service |

```typescript
// Custom product extension for maritime
import { Product as MedusaProduct } from '@medusajs/medusa';
import { Entity, Column } from 'typeorm';

@Entity()
export class Product extends MedusaProduct {
  @Column({ nullable: true })
  impa_code: string;

  @Column({ nullable: true })
  issa_code: string;

  @Column({ type: 'jsonb', default: '[]' })
  vessel_compatibility: {
    vessel_types: string[];
    flag_restrictions: string[];
    certification_required: string[];
  };

  @Column({ type: 'text', array: true, default: '{}' })
  hazmat_classifications: string[];

  @Column({ nullable: true })
  shelf_life_days: number;

  @Column({ type: 'jsonb', default: '{}' })
  regulatory_compliance: {
    solas_compliant: boolean;
    med_certified: boolean;
    imo_approved: boolean;
  };
}
```

#### Extension Points Architecture

| Extension Point | Purpose | Implementation Method |
|-----------------|---------|----------------------|
| Product Sync | Sync with catalog service | Medusa subscriber + event handler |
| Pricing | TCO integration | Custom pricing strategy |
| Tax | GST/VAT calculation | Tax provider plugin |
| Shipping | Port-based rates | Custom fulfillment provider |
| Notifications | Multi-channel alerts | Notification subscriber |
| Analytics | Business intelligence | Event-driven data export |

### Medusa Upgrade Strategy

#### Version Pinning Policy

| Component | Pinning Strategy | Upgrade Frequency |
|-----------|------------------|-------------------|
| Medusa Core | Minor version pin (e.g., 1.20.x) | Quarterly evaluation |
| Mercur Extension | Exact version pin | After Medusa upgrade |
| Plugins | Minor version pin | Monthly security patches |
| Custom Extensions | Internal versioning | Continuous deployment |

#### Upgrade Process

```typescript
// Upgrade compatibility check
interface MedusaUpgradeAssessment {
  currentVersion: string;
  targetVersion: string;
  breakingChanges: BreakingChange[];
  customizationImpact: CustomizationImpact[];
  migrationRequired: boolean;
  estimatedEffort: 'low' | 'medium' | 'high';
  testingRequirements: string[];
}

interface BreakingChange {
  component: string;
  changeType: 'api' | 'database' | 'config' | 'behavior';
  description: string;
  migrationPath: string;
}

// Upgrade workflow
const UPGRADE_STEPS = [
  { step: 1, action: 'Review changelog and breaking changes' },
  { step: 2, action: 'Assess impact on customizations' },
  { step: 3, action: 'Update dependencies in staging' },
  { step: 4, action: 'Run migration scripts' },
  { step: 5, action: 'Execute full test suite' },
  { step: 6, action: 'Performance benchmark comparison' },
  { step: 7, action: 'Security scan' },
  { step: 8, action: 'Staged rollout (canary -> full)' },
  { step: 9, action: 'Monitor for 7 days' },
  { step: 10, action: 'Document changes and update runbooks' }
];
```

### Fee Structure

#### Commission Rates by Tier

| Supplier Tier | Commission Rate | Volume Discount | Payment Terms |
|---------------|-----------------|-----------------|---------------|
| BASIC | 5.0% | None | Net 15 |
| VERIFIED | 4.0% | >$100K/mo: 3.5% | Net 30 |
| PREFERRED | 3.0% | >$250K/mo: 2.5% | Net 45 |
| PREMIUM | 2.0% | Negotiated | Net 60 |

#### Additional Fees

| Fee Type | Amount | When Applied |
|----------|--------|--------------|
| Payment Processing | 2.5% + $0.30 | All transactions |
| Currency Conversion | 1.5% | Cross-currency |
| Financing Fee | 1.5-3% of invoice | Invoice financing used |
| Expedited Settlement | 0.5% | Settlement < 48 hours |
| Dispute Resolution | $50 | Loser pays (if applicable) |
| API Access (Premium) | $500/month | High-volume integrations |

```typescript
// Fee calculation
interface FeeCalculation {
  orderId: string;
  grossAmount: number;
  fees: {
    commission: { rate: number; amount: number };
    paymentProcessing: { rate: number; fixed: number; amount: number };
    currencyConversion?: { rate: number; amount: number };
    expeditedSettlement?: { rate: number; amount: number };
  };
  totalFees: number;
  netToSupplier: number;
  platformRevenue: number;
}

function calculateFees(order: Order, supplier: Supplier): FeeCalculation {
  const commissionRate = getCommissionRate(supplier.tier, supplier.monthlyVolume);
  const commission = order.totalAmount * (commissionRate / 100);

  const paymentFee = (order.totalAmount * 0.025) + 0.30;

  let currencyFee = 0;
  if (order.currency !== supplier.settlementCurrency) {
    currencyFee = order.totalAmount * 0.015;
  }

  const totalFees = commission + paymentFee + currencyFee;

  return {
    orderId: order.id,
    grossAmount: order.totalAmount,
    fees: {
      commission: { rate: commissionRate, amount: commission },
      paymentProcessing: { rate: 2.5, fixed: 0.30, amount: paymentFee },
      ...(currencyFee > 0 && { currencyConversion: { rate: 1.5, amount: currencyFee } })
    },
    totalFees,
    netToSupplier: order.totalAmount - totalFees,
    platformRevenue: commission
  };
}
```

### Dispute Resolution Flow

#### Dispute Categories and SLAs

| Category | Description | Resolution SLA | Escalation Path |
|----------|-------------|----------------|-----------------|
| Quality | Product doesn't match description | 7 days | Support -> Ops -> Legal |
| Delivery | Late, damaged, or missing items | 5 days | Support -> Ops -> Legal |
| Pricing | Overcharge or price discrepancy | 3 days | Support -> Finance |
| Documentation | Missing or incorrect documents | 3 days | Support -> Ops |
| Fraud | Suspected fraudulent activity | 24 hours | Security -> Legal |

#### Resolution Workflow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Dispute Filed   │────▶│ Auto-Categorize │────▶│ Assign Handler  │
│ by Buyer        │     │ & Prioritize    │     │ (SLA Clock)     │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
┌─────────────────┐     ┌─────────────────┐              │
│ Supplier        │◀────│ Request         │◀─────────────┘
│ Response        │     │ Evidence        │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Evidence        │────▶│ Platform        │────▶│ Resolution      │
│ Review          │     │ Decision        │     │ Execution       │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
         ┌───────────────────┬───────────────────────────┘
         ▼                   ▼                           ▼
┌─────────────────┐  ┌─────────────────┐      ┌─────────────────┐
│ Full Refund     │  │ Partial Refund  │      │ Dispute         │
│ to Buyer        │  │ / Credit        │      │ Rejected        │
└─────────────────┘  └─────────────────┘      └─────────────────┘
```

#### Resolution Options

| Resolution | When Applied | Financial Impact |
|------------|--------------|------------------|
| Full Refund | Product unusable, fraud confirmed | Supplier charged + fee |
| Partial Refund | Minor quality/quantity issues | Negotiated split |
| Replacement | Product defective, supplier willing | Supplier bears shipping |
| Credit | Future purchase credit | Applied to next order |
| No Action | Dispute unfounded | Buyer charged dispute fee |
| Mediation | Complex cases, high value | External mediator if needed |

### Supplier Quality Governance

#### Performance Metrics and Thresholds

| Metric | Calculation | Warning | Critical | Delisting |
|--------|-------------|---------|----------|-----------|
| Order Accuracy | Correct items / Total items | <95% | <90% | <85% |
| On-Time Delivery | On-time / Total deliveries | <90% | <85% | <80% |
| Response Time | Avg quote response time | >24h | >48h | >72h |
| Dispute Rate | Disputes / Orders | >3% | >5% | >8% |
| Quality Score | Buyer ratings (1-5) | <4.0 | <3.5 | <3.0 |
| Return Rate | Returns / Orders | >5% | >8% | >12% |

#### Supplier Scorecard

```typescript
interface SupplierScorecard {
  supplierId: string;
  period: { from: Date; to: Date };
  metrics: {
    orderAccuracy: { value: number; trend: 'up' | 'down' | 'stable'; threshold: 'ok' | 'warning' | 'critical' };
    onTimeDelivery: { value: number; trend: 'up' | 'down' | 'stable'; threshold: 'ok' | 'warning' | 'critical' };
    responseTime: { value: number; trend: 'up' | 'down' | 'stable'; threshold: 'ok' | 'warning' | 'critical' };
    disputeRate: { value: number; trend: 'up' | 'down' | 'stable'; threshold: 'ok' | 'warning' | 'critical' };
    qualityScore: { value: number; trend: 'up' | 'down' | 'stable'; threshold: 'ok' | 'warning' | 'critical' };
    returnRate: { value: number; trend: 'up' | 'down' | 'stable'; threshold: 'ok' | 'warning' | 'critical' };
  };
  overallHealth: 'excellent' | 'good' | 'needs_improvement' | 'at_risk' | 'critical';
  recommendations: string[];
  requiredActions: RequiredAction[];
}

interface RequiredAction {
  action: string;
  deadline: Date;
  consequence: string;
  acknowledged: boolean;
}
```

#### Delisting Criteria and Process

| Trigger | Grace Period | Remediation Option | Appeal |
|---------|--------------|-------------------|--------|
| 3+ critical metrics | 30 days | Performance improvement plan | Yes |
| Confirmed fraud | Immediate | None | Legal only |
| KYC non-compliance | 7 days | Document submission | Yes |
| Repeated SLA breaches | 14 days | Capacity review | Yes |
| Customer safety issue | Immediate | Third-party audit | Yes |

### Open Questions - Resolved

- **Q:** What compliance obligations (tax, invoicing, cross-border) are in scope?
  - **A:** For the initial launch, the platform addresses the following compliance obligations:

    **Tax Compliance:**
    - GST collection and reporting for Indian transactions (platform facilitates, suppliers remit)
    - GST invoice generation with mandatory fields (GSTIN, HSN codes, place of supply)
    - TDS deduction on supplier payments where applicable (platform deducts and deposits)
    - Monthly GST reconciliation reports for suppliers

    **Invoicing Compliance:**
    - E-invoicing integration with GST portal for B2B transactions >50L turnover
    - Invoice numbering per GST requirements (unique, sequential)
    - Credit note and debit note handling for returns/adjustments
    - Invoice archival for 7 years per tax requirements

    **Cross-Border (Phase 2):**
    - Initially out of scope - all transactions are India-domestic
    - Phase 2 will address: import/export documentation, customs integration, multi-currency settlement, withholding tax treaties
    - Platform may become Merchant of Record for specific cross-border corridors

    **Data Compliance:**
    - Data localization: Primary data stored in India (AWS Mumbai)
    - GDPR considerations for EU suppliers (consent, data portability)
    - RBI guidelines for payment data storage

---

## References
- [Medusa.js Documentation](https://docs.medusajs.com/)
- [Mercur Marketplace Extension](https://github.com/aspect-build/mercur)
- [Stripe Connect Documentation](https://stripe.com/docs/connect)
- [Multi-Vendor Marketplace Patterns](https://www.sharetribe.com/academy/what-is-a-marketplace/)
