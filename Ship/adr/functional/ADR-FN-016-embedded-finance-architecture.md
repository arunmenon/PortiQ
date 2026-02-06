# ADR-FN-016: Embedded Finance Architecture

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

The platform aims to offer embedded finance services enabling suppliers to receive early payment on invoices, addressing the 90-120 day payment cycles common in maritime procurement.

### Business Context
Ship chandlers face severe working capital constraints due to extended payment terms. Typical payment cycles of 90-120 days strain supplier finances, limiting their ability to fulfill orders and grow. India's fintech infrastructure (TReDS, NBFCs) provides regulated mechanisms for invoice financing that can be embedded into the platform. This creates a differentiated offering: suppliers can receive 70% of invoice value at 30 days instead of waiting 90-120 days.

### Technical Context
- TReDS (Trade Receivables Discounting System) is RBI-regulated
- Multiple NBFCs offer API-based invoice financing
- Need to integrate with multiple lenders for competitive rates
- Credit assessment requires platform transaction data
- Compliance with RBI guidelines mandatory

### Assumptions
- Suppliers will opt in to financing services
- Buyers will acknowledge invoices on platform (required for TReDS)
- Platform transaction history can support credit assessment
- Middleware providers simplify multi-lender integration

---

## Decision Drivers

- Supplier value proposition and retention
- Platform revenue diversification (commission on financed amounts)
- Regulatory compliance (RBI guidelines)
- Integration complexity with multiple lenders
- User experience for financing workflow
- Risk management for platform

---

## Considered Options

### Option 1: Direct TReDS Integration
**Description:** Integrate directly with TReDS platforms (M1xchange, RXIL) for invoice discounting.

**Pros:**
- Regulated "without recourse" financing
- Competitive rates through auction
- Established infrastructure
- Trusted by banks and NBFCs

**Cons:**
- Complex integration per platform
- Requires MSME registration
- Limited to certain buyer types
- Slower implementation

### Option 2: Embedded Finance Middleware
**Description:** Use middleware providers (CredAble, FinBox, Decentro) for single integration to multiple lenders.

**Pros:**
- Single API to multiple lenders
- Handles compliance complexity
- White-label experience
- Faster implementation
- Built-in credit assessment

**Cons:**
- Middleware fees
- Dependency on third party
- Less control over lender selection

### Option 3: Proprietary Financing (Platform as Lender)
**Description:** Platform directly provides financing from its balance sheet.

**Pros:**
- Complete control
- Full margin capture
- No third-party dependencies

**Cons:**
- Massive capital requirements
- Regulatory licensing needed (NBFC)
- Credit risk on balance sheet
- Not feasible at current stage

---

## Decision

**Chosen Option:** Embedded Finance Middleware with TReDS Fallback

We will implement embedded finance using a middleware provider (CredAble or FinBox) as the primary integration, with direct TReDS platform integration as a secondary channel for eligible transactions.

### Rationale
Middleware providers offer the fastest path to multi-lender financing with a single integration, handling compliance complexity and credit assessment. TReDS integration provides the regulated, "without recourse" option preferred for larger transactions. This dual approach maximizes supplier access to financing while managing implementation complexity.

---

## Consequences

### Positive
- Fast time-to-market for financing features
- Access to multiple lenders through single integration
- Regulated option available via TReDS
- Platform earns commission on financed amount
- Significant supplier value proposition

### Negative
- Middleware fees reduce margin
- **Mitigation:** Negotiate volume-based pricing, pass through transparently
- Third-party dependency
- **Mitigation:** Abstract integration, maintain TReDS as backup

### Risks
- Middleware provider issues: TReDS fallback, multi-provider strategy
- Regulatory changes: Stay compliant, legal monitoring
- Credit defaults: Without-recourse TReDS, middleware handles risk

---

## Implementation Notes

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Platform Finance Layer                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌───────────────────────────────────────────┐  │
│  │   Invoice    │    │         Finance Middleware                 │  │
│  │   Service    │───▶│                                           │  │
│  └──────────────┘    │  ┌─────────────────────────────────────┐  │  │
│                      │  │    CredAble / FinBox / Decentro     │  │  │
│  ┌──────────────┐    │  │                                     │  │  │
│  │   Credit     │───▶│  │  - Credit Assessment                │  │  │
│  │  Assessment  │    │  │  - Multi-Lender Matching            │  │  │
│  └──────────────┘    │  │  - Offer Management                 │  │  │
│                      │  │  - Disbursement                     │  │  │
│  ┌──────────────┐    │  │  - Compliance                       │  │  │
│  │   TReDS      │    │  │                                     │  │  │
│  │  Connector   │────│  └─────────────────────────────────────┘  │  │
│  └──────────────┘    │                    │                      │  │
│                      │                    ▼                      │  │
│                      │  ┌─────────────────────────────────────┐  │  │
│                      │  │           Lender Network            │  │  │
│                      │  │                                     │  │  │
│                      │  │  Banks │ NBFCs │ TReDS Platforms    │  │  │
│                      │  │                                     │  │  │
│                      │  └─────────────────────────────────────┘  │  │
│                      └───────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Invoice Financing Flow

```typescript
// finance/flows/invoice-financing.flow.ts
export const InvoiceFinancingFlow = {
  steps: [
    'INVOICE_CREATED',
    'BUYER_ACKNOWLEDGED',
    'FINANCING_REQUESTED',
    'CREDIT_ASSESSMENT',
    'OFFERS_RECEIVED',
    'OFFER_SELECTED',
    'DISBURSEMENT_INITIATED',
    'FUNDS_DISBURSED',
    'REPAYMENT_DUE',
    'REPAYMENT_COMPLETED'
  ]
};

interface FinancingRequest {
  invoiceId: string;
  supplierId: string;
  buyerId: string;
  invoiceAmount: number;
  invoiceDate: Date;
  dueDate: Date;
  requestedAmount: number;  // Amount to finance (may be partial)
  preferredTenure: number;  // Days
}

interface FinancingOffer {
  lenderId: string;
  lenderName: string;
  offerId: string;
  principal: number;
  discountRate: number;  // Annual rate
  processingFee: number;
  netDisbursement: number;
  tenure: number;
  repaymentDate: Date;
  validUntil: Date;
  termsUrl: string;
}
```

### Finance Service

```typescript
// finance/services/invoice-finance.service.ts
@Injectable()
export class InvoiceFinanceService {
  constructor(
    private readonly middlewareClient: FinanceMiddlewareClient,
    private readonly tredsConnector: TredsConnector,
    private readonly creditService: CreditAssessmentService,
    private readonly invoiceRepository: InvoiceRepository
  ) {}

  async requestFinancing(request: FinancingRequest): Promise<FinancingSession> {
    const invoice = await this.invoiceRepository.findById(request.invoiceId);

    // Validate invoice is eligible
    this.validateEligibility(invoice);

    // Get platform credit assessment data
    const creditData = await this.creditService.getSupplierCreditData(
      request.supplierId
    );

    // Create financing session
    const session = await this.middlewareClient.createSession({
      invoice: {
        number: invoice.number,
        amount: invoice.amount,
        date: invoice.date,
        dueDate: invoice.dueDate,
        buyerGstin: invoice.buyer.gstNumber,
        sellerGstin: invoice.supplier.gstNumber
      },
      creditData,
      requestedAmount: request.requestedAmount,
      preferredTenure: request.preferredTenure
    });

    // Store session reference
    await this.financeSessionRepository.create({
      invoiceId: request.invoiceId,
      sessionId: session.id,
      status: 'PENDING_OFFERS',
      createdAt: new Date()
    });

    return session;
  }

  async getOffers(sessionId: string): Promise<FinancingOffer[]> {
    const offers = await this.middlewareClient.getOffers(sessionId);

    // Add TReDS offers if eligible
    const session = await this.financeSessionRepository.findBySessionId(sessionId);
    const invoice = await this.invoiceRepository.findById(session.invoiceId);

    if (this.isEligibleForTreds(invoice)) {
      const tredsOffers = await this.tredsConnector.getOffers(invoice);
      offers.push(...tredsOffers);
    }

    // Sort by effective rate
    offers.sort((a, b) =>
      this.calculateEffectiveRate(a) - this.calculateEffectiveRate(b)
    );

    return offers;
  }

  async acceptOffer(sessionId: string, offerId: string): Promise<Disbursement> {
    const offer = await this.middlewareClient.getOffer(sessionId, offerId);

    // Accept offer with lender
    const acceptance = await this.middlewareClient.acceptOffer(sessionId, offerId);

    // Update session status
    await this.financeSessionRepository.update(sessionId, {
      status: 'OFFER_ACCEPTED',
      acceptedOfferId: offerId,
      acceptedAt: new Date()
    });

    // Initiate disbursement tracking
    return this.trackDisbursement(acceptance);
  }

  private validateEligibility(invoice: Invoice): void {
    const validations = [
      {
        check: invoice.status === 'ACKNOWLEDGED',
        error: 'Invoice must be acknowledged by buyer'
      },
      {
        check: invoice.dueDate > new Date(),
        error: 'Invoice must not be past due'
      },
      {
        check: !invoice.financingSessionId,
        error: 'Invoice already has active financing'
      },
      {
        check: invoice.amount >= 10000,
        error: 'Minimum invoice amount is ₹10,000'
      }
    ];

    for (const { check, error } of validations) {
      if (!check) throw new BadRequestException(error);
    }
  }

  private isEligibleForTreds(invoice: Invoice): boolean {
    // TReDS eligibility: MSME supplier, large buyer
    return (
      invoice.supplier.msmeRegistration &&
      invoice.buyer.annualTurnover > 25000000000  // > ₹250 Cr
    );
  }
}
```

### Credit Assessment Service

```typescript
// finance/services/credit-assessment.service.ts
@Injectable()
export class CreditAssessmentService {
  async getSupplierCreditData(supplierId: string): Promise<CreditData> {
    const supplier = await this.supplierRepository.findById(supplierId);

    // Get platform transaction history
    const orderHistory = await this.orderRepository.getSupplierHistory(
      supplierId,
      { months: 24 }
    );

    // Get GST return data (via Account Aggregator if available)
    const gstData = await this.gstService.getReturns(supplier.gstNumber);

    // Calculate credit metrics
    const metrics = this.calculateCreditMetrics(orderHistory, gstData);

    return {
      supplierId,
      supplierName: supplier.businessName,
      gstin: supplier.gstNumber,

      // Platform data
      platformTenureMonths: this.calculateTenure(supplier.createdAt),
      totalOrders: orderHistory.totalOrders,
      totalGmv: orderHistory.totalGmv,
      avgOrderValue: orderHistory.avgOrderValue,
      orderFrequency: orderHistory.ordersPerMonth,
      fulfillmentRate: orderHistory.fulfillmentRate,
      onTimeDeliveryRate: orderHistory.onTimeDeliveryRate,

      // External data
      gstComplianceScore: gstData.complianceScore,
      gstTurnover12m: gstData.turnover12Months,

      // Calculated score
      creditScore: metrics.score,
      creditLimit: metrics.recommendedLimit,

      generatedAt: new Date()
    };
  }

  private calculateCreditMetrics(
    orders: OrderHistory,
    gst: GstData
  ): CreditMetrics {
    let score = 0;

    // Platform performance (40%)
    score += Math.min(orders.fulfillmentRate * 40, 40);

    // Order volume (20%)
    const volumeScore = Math.min(orders.totalGmv / 10000000, 1) * 20;
    score += volumeScore;

    // Tenure (15%)
    const tenureScore = Math.min(orders.tenureMonths / 24, 1) * 15;
    score += tenureScore;

    // GST compliance (15%)
    score += gst.complianceScore * 0.15;

    // Consistency (10%)
    const consistencyScore = this.calculateConsistency(orders) * 10;
    score += consistencyScore;

    // Calculate recommended limit
    const avgMonthlyGmv = orders.totalGmv / Math.max(orders.tenureMonths, 1);
    const recommendedLimit = avgMonthlyGmv * 2 * (score / 100);

    return {
      score: Math.round(score),
      recommendedLimit: Math.round(recommendedLimit)
    };
  }
}
```

### Middleware Client Interface

```typescript
// finance/clients/finance-middleware.client.ts
interface FinanceMiddlewareClient {
  createSession(request: CreateSessionRequest): Promise<FinancingSession>;
  getOffers(sessionId: string): Promise<FinancingOffer[]>;
  getOffer(sessionId: string, offerId: string): Promise<FinancingOffer>;
  acceptOffer(sessionId: string, offerId: string): Promise<OfferAcceptance>;
  getDisbursementStatus(disbursementId: string): Promise<DisbursementStatus>;
  getRepaymentSchedule(financingId: string): Promise<RepaymentSchedule>;
}

// CredAble implementation
@Injectable()
export class CredAbleClient implements FinanceMiddlewareClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;

  async createSession(request: CreateSessionRequest): Promise<FinancingSession> {
    const response = await this.httpService.post(
      `${this.baseUrl}/v1/financing/sessions`,
      {
        invoice_details: {
          invoice_number: request.invoice.number,
          invoice_amount: request.invoice.amount,
          invoice_date: request.invoice.date,
          due_date: request.invoice.dueDate,
          buyer_gstin: request.invoice.buyerGstin,
          seller_gstin: request.invoice.sellerGstin
        },
        credit_data: request.creditData,
        requested_amount: request.requestedAmount
      },
      {
        headers: { 'X-API-Key': this.apiKey }
      }
    ).toPromise();

    return this.mapToSession(response.data);
  }

  // ... other method implementations
}
```

### Dependencies
- ADR-FN-017: Invoice Financing Workflow
- ADR-FN-018: TReDS Platform Integration
- ADR-FN-022: Order Lifecycle & Fulfillment
- ADR-NF-017: Data Encryption

### Migration Strategy
1. Select and contract with middleware provider
2. Implement credit assessment service
3. Build financing request flow
4. Create offer comparison UI
5. Implement disbursement tracking
6. Add TReDS integration for eligible transactions
7. Build finance dashboard for suppliers

---

## Operational Considerations

### Regulated Parties, Responsibilities, and KYC/AML Handoffs

#### Regulatory Framework

| Entity | Regulatory Status | Primary Regulator | Licenses/Registrations |
|--------|------------------|-------------------|------------------------|
| **Platform (ShipChandler)** | Non-regulated marketplace | None directly | GST, MCA registration |
| **Finance Middleware (CredAble/FinBox)** | Technology provider | RBI (indirect) | API aggregator |
| **TReDS Platforms (M1xchange, RXIL)** | RBI-licensed TReDS | RBI | TReDS License |
| **NBFCs (financing partners)** | RBI-regulated NBFC | RBI | NBFC License (CoR) |
| **Banks (via TReDS)** | Scheduled banks | RBI | Banking License |
| **Suppliers (borrowers)** | Unregulated | N/A | MSME Udyam (optional) |
| **Buyers (obligors)** | Unregulated | N/A | Corporate registration |

#### Responsibility Matrix (RACI)

| Activity | Platform | Middleware | Lender | TReDS | Supplier | Buyer |
|----------|----------|------------|--------|-------|----------|-------|
| Supplier onboarding KYC | Collect | Verify | Approve | N/A | Provide | N/A |
| Credit assessment | Provide data | Process | Decide | N/A | N/A | N/A |
| AML screening | R | A | C | C | I | I |
| Invoice verification | A | R | C | C | I | I |
| Disbursement | I | C | A/R | A/R | I | N/A |
| Repayment collection | A | R | C | C | N/A | R |
| Dispute resolution | A | R | C | C | I | I |

*R=Responsible, A=Accountable, C=Consulted, I=Informed*

#### KYC/AML Handoff Process

```typescript
// KYC handoff workflow
interface KYCHandoff {
  stage: 'platform_collection' | 'middleware_verification' | 'lender_approval';
  dataRequired: KYCDataPoint[];
  responsible: string;
  sla: number;  // hours
  fallbackAction: string;
}

const KYC_HANDOFF_FLOW: KYCHandoff[] = [
  {
    stage: 'platform_collection',
    dataRequired: [
      { field: 'pan', type: 'document', required: true },
      { field: 'gstin', type: 'identifier', required: true },
      { field: 'udyam', type: 'identifier', required: false },
      { field: 'bank_account', type: 'bank_verification', required: true },
      { field: 'directors_pan', type: 'document', required: true },
      { field: 'address_proof', type: 'document', required: true }
    ],
    responsible: 'Platform',
    sla: 24,
    fallbackAction: 'Notify supplier of missing documents'
  },
  {
    stage: 'middleware_verification',
    dataRequired: [
      { field: 'pan_verification', type: 'api_check', required: true },
      { field: 'gstin_verification', type: 'api_check', required: true },
      { field: 'bank_verification', type: 'penny_drop', required: true },
      { field: 'aml_screening', type: 'watchlist_check', required: true },
      { field: 'cibil_check', type: 'bureau_pull', required: true }
    ],
    responsible: 'Middleware',
    sla: 4,
    fallbackAction: 'Manual verification queue'
  },
  {
    stage: 'lender_approval',
    dataRequired: [
      { field: 'credit_decision', type: 'internal', required: true },
      { field: 'limit_sanction', type: 'internal', required: true },
      { field: 'agreement_execution', type: 'digital_signature', required: true }
    ],
    responsible: 'Lender',
    sla: 48,
    fallbackAction: 'Escalate to relationship manager'
  }
];

// AML screening integration
interface AMLScreeningResult {
  supplierId: string;
  screeningDate: Date;
  watchlistMatches: WatchlistMatch[];
  pepStatus: 'clear' | 'flagged' | 'review_required';
  sanctionsStatus: 'clear' | 'flagged' | 'review_required';
  adverseMediaHits: number;
  riskScore: number;  // 0-100
  recommendation: 'approve' | 'enhanced_due_diligence' | 'reject';
}

@Injectable()
export class AMLComplianceService {
  async screenSupplier(supplierId: string): Promise<AMLScreeningResult> {
    const supplier = await this.supplierRepository.findById(supplierId);

    // Screen through middleware
    const result = await this.middlewareClient.amlScreen({
      entityName: supplier.businessName,
      pan: supplier.pan,
      directors: supplier.directors.map(d => ({ name: d.name, pan: d.pan })),
      country: 'IN'
    });

    // Store for audit
    await this.amlAuditRepository.insert({
      supplierId,
      screeningDate: new Date(),
      result,
      nextScreeningDue: addMonths(new Date(), 12)  // Annual rescreening
    });

    return result;
  }
}
```

### Risk Limits, Reconciliation, and Failure Handling

#### Risk Limits Framework

| Risk Type | Limit Level | Limit Value | Monitoring | Breach Action |
|-----------|-------------|-------------|------------|---------------|
| **Single supplier exposure** | Per supplier | Max 10% of total financing | Real-time | Block new financing |
| **Single buyer concentration** | Per buyer | Max 15% of total financing | Daily | Alert + review |
| **Industry concentration** | Per sector | Max 30% | Weekly | Portfolio review |
| **Daily disbursement** | Platform | ₹5 Cr (MVP), ₹50 Cr (scale) | Real-time | Queue pending |
| **Monthly disbursement** | Platform | ₹50 Cr (MVP), ₹500 Cr (scale) | Daily | Suspend new requests |
| **Invoice age** | Per invoice | Max 60 days old | At request | Reject |
| **Financing ratio** | Per invoice | Max 85% of invoice value | At request | Cap amount |

```typescript
// Risk limit enforcement
interface RiskLimits {
  supplierExposure: {
    maxPercentOfPortfolio: 10;
    absoluteMaxINR: 10000000;  // ₹1 Cr
  };
  buyerConcentration: {
    maxPercentOfPortfolio: 15;
  };
  dailyDisbursement: {
    maxINR: 50000000;  // ₹5 Cr
    warningThresholdPercent: 80;
  };
  invoiceAge: {
    maxDaysOld: 60;
  };
  financingRatio: {
    maxPercent: 85;
  };
}

@Injectable()
export class RiskLimitService {
  async checkLimits(request: FinancingRequest): Promise<RiskCheckResult> {
    const checks: RiskCheck[] = [];

    // Supplier exposure check
    const supplierExposure = await this.getSupplierExposure(request.supplierId);
    const portfolioTotal = await this.getTotalPortfolio();
    const newExposure = supplierExposure + request.amount;

    if (newExposure / portfolioTotal > 0.10) {
      checks.push({
        type: 'supplier_exposure',
        status: 'breach',
        message: `Supplier exposure would exceed 10% (current: ${(supplierExposure / portfolioTotal * 100).toFixed(1)}%)`
      });
    }

    // Daily disbursement check
    const todayDisbursements = await this.getTodayDisbursements();
    if (todayDisbursements + request.amount > RISK_LIMITS.dailyDisbursement.maxINR) {
      checks.push({
        type: 'daily_limit',
        status: 'breach',
        message: `Daily disbursement limit would be exceeded`
      });
    }

    // Invoice age check
    const invoiceAge = differenceInDays(new Date(), request.invoiceDate);
    if (invoiceAge > RISK_LIMITS.invoiceAge.maxDaysOld) {
      checks.push({
        type: 'invoice_age',
        status: 'breach',
        message: `Invoice is ${invoiceAge} days old (max: 60)`
      });
    }

    return {
      approved: checks.every(c => c.status !== 'breach'),
      checks,
      warnings: checks.filter(c => c.status === 'warning')
    };
  }
}
```

#### Daily Reconciliation Process

```typescript
// Daily reconciliation job
@Injectable()
export class FinanceReconciliationService {
  @Cron('0 2 * * *')  // 2 AM daily
  async runDailyReconciliation(): Promise<ReconciliationReport> {
    const yesterday = subDays(startOfDay(new Date()), 1);

    const report: ReconciliationReport = {
      date: yesterday,
      disbursements: await this.reconcileDisbursements(yesterday),
      repayments: await this.reconcileRepayments(yesterday),
      commissions: await this.reconcileCommissions(yesterday),
      discrepancies: [],
      status: 'pending'
    };

    // Check for discrepancies
    report.discrepancies = await this.identifyDiscrepancies(report);

    if (report.discrepancies.length > 0) {
      report.status = 'review_required';
      await this.alertService.sendWarning('reconciliation_discrepancy', {
        date: yesterday,
        count: report.discrepancies.length,
        totalAmount: report.discrepancies.reduce((sum, d) => sum + d.amount, 0)
      });
    } else {
      report.status = 'matched';
    }

    await this.reconciliationRepository.save(report);
    return report;
  }

  private async reconcileDisbursements(date: Date): Promise<DisbursementReconciliation> {
    // Platform records
    const platformDisbursements = await this.disbursementRepository.findByDate(date);

    // Middleware records (via API)
    const middlewareDisbursements = await this.middlewareClient.getDisbursements(date);

    // Match records
    const matched: MatchedRecord[] = [];
    const platformOnly: DisbursementRecord[] = [];
    const middlewareOnly: any[] = [];

    for (const platform of platformDisbursements) {
      const middleware = middlewareDisbursements.find(
        m => m.reference === platform.middlewareReference
      );

      if (middleware) {
        if (platform.amount === middleware.amount && platform.status === middleware.status) {
          matched.push({ platform, middleware, status: 'matched' });
        } else {
          matched.push({ platform, middleware, status: 'mismatch' });
        }
      } else {
        platformOnly.push(platform);
      }
    }

    return { matched, platformOnly, middlewareOnly, date };
  }
}
```

#### Failure Handling Matrix

| Failure Type | Detection | Immediate Action | Recovery | Escalation |
|--------------|-----------|------------------|----------|------------|
| **Middleware API down** | Health check (1 min) | Queue requests | Auto-retry (exp backoff) | Alert after 15 min |
| **Disbursement failed** | Webhook/polling | Notify supplier | Retry with support | Manual intervention |
| **Repayment missed** | T+1 check | Alert lender + buyer | Grace period (3 days) | Collection process |
| **KYC verification failed** | API response | Notify supplier | Manual document review | Reject if unresolved |
| **Credit decision timeout** | SLA breach (48h) | Alert ops | Escalate to lender | Manual override |
| **Bank transfer failed** | UTR verification | Retry alternate bank | Manual payout | Finance team |

```typescript
// Failure handling service
@Injectable()
export class FinanceFailureHandler {
  @OnEvent('disbursement.failed')
  async handleDisbursementFailure(event: DisbursementFailedEvent): Promise<void> {
    const { disbursementId, reason, errorCode } = event;

    // Log failure
    await this.failureLogRepository.insert({
      entityType: 'disbursement',
      entityId: disbursementId,
      reason,
      errorCode,
      timestamp: new Date()
    });

    // Determine recovery action
    const action = this.determineRecoveryAction(errorCode);

    switch (action) {
      case 'retry':
        await this.queueRetry(disbursementId, { delay: 300000 });  // 5 min
        break;
      case 'alternate_bank':
        await this.attemptAlternateBank(disbursementId);
        break;
      case 'manual':
        await this.createManualInterventionTicket(disbursementId, reason);
        break;
    }

    // Notify supplier
    await this.notificationService.notify(event.supplierId, {
      type: 'DISBURSEMENT_DELAYED',
      reason: this.getUserFriendlyMessage(errorCode),
      expectedResolution: this.getExpectedResolutionTime(action)
    });
  }

  @OnEvent('repayment.overdue')
  async handleOverdueRepayment(event: RepaymentOverdueEvent): Promise<void> {
    const { financingId, daysOverdue, amount } = event;

    if (daysOverdue === 1) {
      // First reminder
      await this.notificationService.notifyBuyer(event.buyerId, {
        type: 'PAYMENT_REMINDER',
        invoiceId: event.invoiceId,
        amount
      });
    } else if (daysOverdue === 3) {
      // Escalate to lender
      await this.middlewareClient.reportOverdue(financingId, daysOverdue);
      await this.alertService.sendWarning('repayment_overdue', event);
    } else if (daysOverdue >= 7) {
      // Initiate collection
      await this.initiateCollectionProcess(financingId);
    }
  }
}
```

### Open Questions

- **Q:** Which finance partners or APIs are assumed, and what is the contingency plan?
  - **A:** Primary and contingency partner strategy:

  **Primary Partners (Launch):**
  | Partner Type | Primary | Integration Status | Go-Live Target |
  |--------------|---------|-------------------|----------------|
  | **Finance Middleware** | CredAble | API available | Month 3 |
  | **TReDS Platform** | M1xchange | Partner agreement | Month 4 |
  | **NBFC (via middleware)** | Multiple (Lendingkart, FlexiLoans) | Via CredAble | Month 3 |
  | **Bank Account Verification** | Cashfree | API integrated | Month 2 |
  | **GST Verification** | ClearTax API | API available | Month 2 |

  **Secondary Partners (Contingency):**
  | Partner Type | Secondary | Switch Criteria | Switch Effort |
  |--------------|-----------|-----------------|---------------|
  | **Finance Middleware** | FinBox | CredAble SLA breach > 3x/month | 3 weeks |
  | **TReDS Platform** | RXIL | M1xchange unavailable > 24h | 2 weeks |
  | **Bank Verification** | Signzy | Cashfree downtime > 4h | 1 week |
  | **GST Verification** | Masters India | ClearTax issues | 3 days |

  **Contingency Implementation:**
  ```typescript
  // Multi-provider finance client
  interface FinanceProviderConfig {
    primary: {
      provider: 'credable' | 'finbox';
      baseUrl: string;
      apiKey: string;
      healthCheckUrl: string;
    };
    secondary: {
      provider: 'credable' | 'finbox';
      baseUrl: string;
      apiKey: string;
      healthCheckUrl: string;
    };
    failover: {
      healthCheckIntervalMs: 60000;
      failureThreshold: 3;
      recoveryThreshold: 2;
      circuitBreakerTimeoutMs: 300000;
    };
  }

  @Injectable()
  export class ResilientFinanceClient {
    private activeProvider: 'primary' | 'secondary' = 'primary';
    private failureCount = 0;

    async createFinancingSession(request: SessionRequest): Promise<Session> {
      const provider = this.getActiveProvider();

      try {
        const result = await provider.createSession(request);
        this.recordSuccess();
        return result;
      } catch (error) {
        this.recordFailure(error);

        if (this.shouldFailover()) {
          this.switchProvider();
          return this.createFinancingSession(request);  // Retry with secondary
        }

        throw error;
      }
    }

    private shouldFailover(): boolean {
      return this.failureCount >= this.config.failover.failureThreshold &&
             this.activeProvider === 'primary';
    }

    private switchProvider(): void {
      this.activeProvider = this.activeProvider === 'primary' ? 'secondary' : 'primary';
      this.failureCount = 0;

      this.alertService.sendWarning('finance_provider_failover', {
        from: this.activeProvider === 'primary' ? 'secondary' : 'primary',
        to: this.activeProvider,
        reason: 'failure_threshold_exceeded'
      });
    }
  }
  ```

  **Partner SLA Requirements:**
  | Partner | Availability | Response Time | Support Hours |
  |---------|--------------|---------------|---------------|
  | CredAble | 99.5% | < 500ms P95 | 24/7 |
  | M1xchange | 99.0% | < 2s | Business hours |
  | Cashfree | 99.9% | < 200ms | 24/7 |

  **Escalation Contacts:**
  - CredAble: Technical - api-support@credable.in, Business - partnerships@credable.in
  - M1xchange: Integration - tech@m1xchange.com, Operations - ops@m1xchange.com

---

## References
- [CredAble Embedded Finance](https://www.credable.in/)
- [FinBox Embedded Lending](https://finbox.in/)
- [RBI TReDS Guidelines](https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=10718)
- [Account Aggregator Framework](https://sahamati.org.in/)
