# ADR-FN-017: Invoice Financing Workflow

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

Building on the embedded finance architecture (ADR-FN-016), this ADR defines the detailed workflow for invoice financing from request to repayment.

### Business Context
The invoice financing workflow involves multiple parties and steps:
1. Supplier requests financing on an acknowledged invoice
2. Platform provides credit assessment data to lenders
3. Multiple lenders submit offers
4. Supplier selects preferred offer
5. Lender disburses funds (T+1 typical)
6. On invoice due date, buyer pays platform
7. Platform remits to lender

Each step requires proper state management, notifications, and audit trail.

### Technical Context
- Integration with finance middleware (ADR-FN-016)
- Saga pattern for multi-step workflow (ADR-NF-010)
- Event-driven notifications (ADR-NF-009)
- Secure handling of financial data (ADR-NF-017)
- Reconciliation with payment systems

### Assumptions
- Buyers acknowledge invoices on platform
- T+1 disbursement is acceptable
- Platform holds funds temporarily for routing
- Repayment comes from buyer payment, not supplier

---

## Decision Drivers

- Clear workflow state visibility
- Error handling and recovery
- Audit trail for financial transactions
- Multi-party coordination
- Regulatory compliance
- User experience simplicity

---

## Considered Options

### Option 1: Linear Sequential Workflow
**Description:** Simple step-by-step workflow with manual intervention for exceptions.

**Pros:**
- Easy to understand
- Simple to implement
- Clear state transitions

**Cons:**
- No parallel processing
- Manual exception handling
- Poor user experience for delays

### Option 2: Saga-Based Orchestration
**Description:** Use saga pattern with compensating transactions for each step.

**Pros:**
- Robust error handling
- Automatic rollback capability
- Clear compensation logic
- Supports parallel operations

**Cons:**
- More complex implementation
- Requires careful design of compensations

### Option 3: Event-Driven Choreography
**Description:** Events trigger reactions across services without central orchestration.

**Pros:**
- Loose coupling
- Scalable
- Services independent

**Cons:**
- Hard to track overall flow
- Debugging challenges
- No central visibility

---

## Decision

**Chosen Option:** Saga-Based Orchestration

We will implement the invoice financing workflow using the saga pattern with explicit compensating transactions, providing robust error handling and clear audit trail.

### Rationale
Financial workflows require guaranteed consistency and clear rollback paths. The saga pattern provides explicit handling for partial failures—critical when dealing with external lenders and payment systems. Combined with the workflow engine from Medusa (ADR-FN-015), this provides a robust foundation for financial operations.

---

## Consequences

### Positive
- Robust handling of partial failures
- Clear compensation logic for each step
- Comprehensive audit trail
- Supports complex multi-party coordination
- Recoverable from system failures

### Negative
- Higher implementation complexity
- **Mitigation:** Use workflow engine, clear documentation
- Compensation logic must be carefully designed
- **Mitigation:** Thorough testing, financial team review

### Risks
- Compensation failures: Manual intervention queue, alerts
- Timing issues with external systems: Idempotency, retry logic
- Data inconsistency: Transaction boundaries, reconciliation

---

## Implementation Notes

### Workflow State Machine

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Invoice Financing State Machine                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────┐      ┌───────────────┐      ┌─────────────────┐       │
│  │ INVOICE  │─────▶│   FINANCING   │─────▶│    CREDIT       │       │
│  │ ELIGIBLE │      │   REQUESTED   │      │   ASSESSMENT    │       │
│  └──────────┘      └───────────────┘      └────────┬────────┘       │
│                                                     │                │
│                                                     ▼                │
│  ┌──────────┐      ┌───────────────┐      ┌─────────────────┐       │
│  │ EXPIRED  │◀─────│    OFFERS     │◀─────│    OFFERS       │       │
│  │          │      │   RECEIVED    │      │   PENDING       │       │
│  └──────────┘      └───────┬───────┘      └─────────────────┘       │
│                            │                                         │
│                            ▼                                         │
│  ┌──────────┐      ┌───────────────┐      ┌─────────────────┐       │
│  │ REJECTED │◀─────│    OFFER      │─────▶│  DISBURSEMENT   │       │
│  │          │      │   SELECTED    │      │    PENDING      │       │
│  └──────────┘      └───────────────┘      └────────┬────────┘       │
│                                                     │                │
│                                                     ▼                │
│  ┌──────────┐      ┌───────────────┐      ┌─────────────────┐       │
│  │ DEFAULTED│◀─────│  REPAYMENT    │◀─────│    DISBURSED    │       │
│  │          │      │    DUE        │      │                 │       │
│  └──────────┘      └───────┬───────┘      └─────────────────┘       │
│                            │                                         │
│                            ▼                                         │
│                    ┌───────────────┐                                 │
│                    │   COMPLETED   │                                 │
│                    │               │                                 │
│                    └───────────────┘                                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Saga Definition

```typescript
// finance/sagas/invoice-financing.saga.ts
import { createWorkflow, WorkflowResponse, StepResponse } from '@medusajs/workflows-sdk';

export const invoiceFinancingSaga = createWorkflow(
  'invoice-financing-saga',
  (input: FinancingInput) => {
    // Step 1: Validate and lock invoice
    const invoiceLock = lockInvoiceStep(input.invoiceId);

    // Step 2: Get credit assessment
    const creditData = getCreditAssessmentStep({
      supplierId: input.supplierId,
      invoiceId: input.invoiceId
    });

    // Step 3: Request offers from lenders
    const offers = requestOffersStep({
      invoice: invoiceLock.invoice,
      creditData: creditData,
      requestedAmount: input.requestedAmount
    });

    // Step 4: Wait for supplier selection (async)
    const selectedOffer = awaitOfferSelectionStep({
      sessionId: offers.sessionId,
      timeout: input.offerValidityHours * 3600
    });

    // Step 5: Accept offer with lender
    const acceptance = acceptOfferStep({
      sessionId: offers.sessionId,
      offerId: selectedOffer.offerId
    });

    // Step 6: Await disbursement
    const disbursement = awaitDisbursementStep({
      acceptanceId: acceptance.id,
      expectedDate: acceptance.expectedDisbursementDate
    });

    // Step 7: Update invoice status
    const finalStatus = updateInvoiceStatusStep({
      invoiceId: input.invoiceId,
      financingId: disbursement.financingId,
      status: 'FINANCED'
    });

    return new WorkflowResponse({
      financingId: disbursement.financingId,
      disbursedAmount: disbursement.amount,
      repaymentDate: disbursement.repaymentDate
    });
  }
);

// Compensation handlers
invoiceFinancingSaga.addCompensation('lockInvoiceStep', async (context) => {
  await unlockInvoice(context.invoiceId);
});

invoiceFinancingSaga.addCompensation('acceptOfferStep', async (context) => {
  await cancelOfferAcceptance(context.acceptanceId);
  await notifyLender(context.lenderId, 'ACCEPTANCE_CANCELLED');
});
```

### Step Implementations

```typescript
// finance/steps/financing-steps.ts

// Step 1: Lock invoice for financing
export const lockInvoiceStep = createStep(
  'lock-invoice',
  async (input: { invoiceId: string }, context) => {
    const invoice = await invoiceRepository.findById(input.invoiceId);

    if (invoice.financingLock) {
      throw new Error('Invoice already locked for financing');
    }

    await invoiceRepository.update(input.invoiceId, {
      financingLock: true,
      financingLockAt: new Date(),
      financingLockBy: context.userId
    });

    return new StepResponse({ invoice });
  },
  // Compensation
  async (input, context) => {
    await invoiceRepository.update(input.invoiceId, {
      financingLock: false,
      financingLockAt: null,
      financingLockBy: null
    });
  }
);

// Step 2: Get credit assessment
export const getCreditAssessmentStep = createStep(
  'get-credit-assessment',
  async (input: { supplierId: string; invoiceId: string }) => {
    const creditData = await creditAssessmentService.getSupplierCreditData(
      input.supplierId
    );

    // Record assessment for audit
    await creditAssessmentRepository.create({
      supplierId: input.supplierId,
      invoiceId: input.invoiceId,
      creditScore: creditData.creditScore,
      creditLimit: creditData.creditLimit,
      assessedAt: new Date(),
      dataSnapshot: creditData
    });

    return new StepResponse(creditData);
  }
);

// Step 3: Request offers from lenders
export const requestOffersStep = createStep(
  'request-offers',
  async (input: RequestOffersInput) => {
    const session = await financeMiddleware.createSession({
      invoice: input.invoice,
      creditData: input.creditData,
      requestedAmount: input.requestedAmount
    });

    // Poll for offers (or use webhook)
    const offers = await waitForOffers(session.id, {
      timeout: 3600,  // 1 hour
      minOffers: 1
    });

    // Notify supplier of available offers
    await notificationService.notify(input.invoice.supplierId, {
      type: 'FINANCING_OFFERS_AVAILABLE',
      sessionId: session.id,
      offerCount: offers.length,
      bestRate: Math.min(...offers.map(o => o.discountRate))
    });

    return new StepResponse({
      sessionId: session.id,
      offers
    });
  }
);

// Step 5: Accept selected offer
export const acceptOfferStep = createStep(
  'accept-offer',
  async (input: { sessionId: string; offerId: string }, context) => {
    // Validate offer still valid
    const offer = await financeMiddleware.getOffer(input.sessionId, input.offerId);

    if (new Date() > offer.validUntil) {
      throw new Error('Offer has expired');
    }

    // Accept with lender
    const acceptance = await financeMiddleware.acceptOffer(
      input.sessionId,
      input.offerId
    );

    // Record acceptance
    await financingAcceptanceRepository.create({
      sessionId: input.sessionId,
      offerId: input.offerId,
      lenderId: offer.lenderId,
      principal: offer.principal,
      discountRate: offer.discountRate,
      netDisbursement: offer.netDisbursement,
      acceptedAt: new Date(),
      acceptedBy: context.userId
    });

    return new StepResponse(acceptance);
  },
  // Compensation: Cancel acceptance
  async (input, context) => {
    await financeMiddleware.cancelAcceptance(input.sessionId, input.offerId);
  }
);
```

### Async Offer Selection Handler

```typescript
// finance/handlers/offer-selection.handler.ts
@Injectable()
export class OfferSelectionHandler {
  @OnEvent('financing.offer.selected')
  async handleOfferSelection(event: OfferSelectedEvent): Promise<void> {
    const { sessionId, offerId, userId } = event;

    // Resume saga workflow
    const workflow = await workflowRepository.findBySessionId(sessionId);

    if (!workflow || workflow.status !== 'AWAITING_SELECTION') {
      throw new Error('Invalid workflow state for offer selection');
    }

    // Continue saga execution
    await workflowEngine.resume(workflow.id, {
      selectedOffer: { offerId },
      userId
    });
  }

  @OnEvent('financing.session.expired')
  async handleSessionExpired(event: SessionExpiredEvent): Promise<void> {
    const { sessionId } = event;

    const workflow = await workflowRepository.findBySessionId(sessionId);

    if (workflow && workflow.status === 'AWAITING_SELECTION') {
      // Trigger compensation
      await workflowEngine.compensate(workflow.id, {
        reason: 'SESSION_EXPIRED'
      });

      // Notify supplier
      await notificationService.notify(workflow.supplierId, {
        type: 'FINANCING_SESSION_EXPIRED',
        sessionId
      });
    }
  }
}
```

### Disbursement Tracking

```typescript
// finance/services/disbursement-tracker.service.ts
@Injectable()
export class DisbursementTrackerService {
  @Cron('*/15 * * * *')  // Every 15 minutes
  async trackPendingDisbursements(): Promise<void> {
    const pending = await disbursementRepository.findPending();

    for (const disbursement of pending) {
      try {
        const status = await financeMiddleware.getDisbursementStatus(
          disbursement.middlewareId
        );

        if (status.status === 'COMPLETED') {
          await this.handleDisbursementComplete(disbursement, status);
        } else if (status.status === 'FAILED') {
          await this.handleDisbursementFailed(disbursement, status);
        }
      } catch (error) {
        logger.error(`Disbursement tracking failed: ${disbursement.id}`, error);
      }
    }
  }

  private async handleDisbursementComplete(
    disbursement: Disbursement,
    status: DisbursementStatus
  ): Promise<void> {
    await disbursementRepository.update(disbursement.id, {
      status: 'COMPLETED',
      completedAt: status.completedAt,
      utrNumber: status.utrNumber,
      bankReference: status.bankReference
    });

    // Update invoice
    await invoiceRepository.update(disbursement.invoiceId, {
      financingStatus: 'DISBURSED',
      financingDisbursedAt: status.completedAt,
      financingDisbursedAmount: status.amount
    });

    // Notify supplier
    await notificationService.notify(disbursement.supplierId, {
      type: 'FINANCING_DISBURSED',
      invoiceId: disbursement.invoiceId,
      amount: status.amount,
      utrNumber: status.utrNumber
    });

    // Resume workflow
    await workflowEngine.resume(disbursement.workflowId, {
      disbursement: status
    });
  }
}
```

### Repayment Flow

```typescript
// finance/services/repayment.service.ts
@Injectable()
export class RepaymentService {
  @OnEvent('payment.received')
  async handleBuyerPayment(event: PaymentReceivedEvent): Promise<void> {
    const { invoiceId, amount, paymentReference } = event;

    // Check if invoice has financing
    const invoice = await invoiceRepository.findById(invoiceId);

    if (invoice.financingStatus !== 'DISBURSED') {
      return;  // No financing, normal payment flow
    }

    const financing = await financingRepository.findByInvoiceId(invoiceId);

    // Calculate amounts
    const repaymentAmount = financing.principal + financing.discountAmount;
    const supplierAmount = amount - repaymentAmount;

    // Create repayment record
    await repaymentRepository.create({
      financingId: financing.id,
      invoiceId,
      totalReceived: amount,
      repaymentAmount,
      supplierAmount,
      paymentReference,
      status: 'PENDING_TRANSFER'
    });

    // Initiate transfer to lender
    await this.transferToLender(financing, repaymentAmount);

    // Transfer remainder to supplier
    if (supplierAmount > 0) {
      await this.transferToSupplier(invoice.supplierId, supplierAmount);
    }
  }

  private async transferToLender(
    financing: Financing,
    amount: number
  ): Promise<void> {
    await financeMiddleware.initiateRepayment({
      financingId: financing.middlewareFinancingId,
      amount,
      reference: `REP-${financing.id}`
    });
  }
}
```

### Dependencies
- ADR-FN-016: Embedded Finance Architecture
- ADR-FN-022: Order Lifecycle & Fulfillment
- ADR-NF-010: Saga Pattern for Transactions
- ADR-NF-009: Event-Driven Communication

### Migration Strategy
1. Implement saga workflow engine integration
2. Create financing state machine
3. Build step implementations
4. Add compensation handlers
5. Implement disbursement tracking
6. Create repayment reconciliation
7. Build supplier financing dashboard

---

## Operational Considerations

### Eligibility Criteria, Risk Scoring, and Repayment Tracking

#### Invoice Financing Eligibility Matrix

| Criterion | Requirement | Verification Method | Auto-Reject Threshold |
|-----------|-------------|---------------------|----------------------|
| **Invoice Status** | Acknowledged by buyer | Platform confirmation | Not acknowledged |
| **Invoice Age** | <= 60 days from invoice date | Date calculation | > 60 days |
| **Invoice Amount** | >= Rs 10,000 | Direct check | < Rs 10,000 |
| **Days to Due Date** | >= 15 days remaining | Date calculation | < 15 days |
| **Supplier KYC** | Completed and valid | KYC service | Incomplete/expired |
| **Supplier Status** | Active, no blocks | Account status | Blocked/suspended |
| **Previous Financing** | No active financing on invoice | DB check | Already financed |
| **Dispute Status** | No open disputes | Dispute service | Active dispute |
| **Buyer Creditworthiness** | No payment defaults > 30 days | Payment history | 3+ defaults in 12 months |
| **Platform Tenure** | >= 30 days for supplier | Account age | < 30 days |

```typescript
// Eligibility checker implementation
interface EligibilityResult {
  eligible: boolean;
  checks: EligibilityCheck[];
  maxFinancingAmount?: number;
  suggestedTenure?: number;
  ineligibilityReasons?: string[];
}

@Injectable()
export class FinancingEligibilityService {
  async checkEligibility(invoiceId: string): Promise<EligibilityResult> {
    const invoice = await this.invoiceRepository.findById(invoiceId);
    const supplier = await this.supplierRepository.findById(invoice.supplierId);
    const buyer = await this.buyerRepository.findById(invoice.buyerId);

    const checks: EligibilityCheck[] = [];

    // Invoice status check
    checks.push({
      criterion: 'invoice_acknowledged',
      passed: invoice.status === 'ACKNOWLEDGED',
      message: invoice.status === 'ACKNOWLEDGED'
        ? 'Invoice acknowledged by buyer'
        : 'Invoice must be acknowledged by buyer'
    });

    // Invoice age check
    const invoiceAge = differenceInDays(new Date(), invoice.invoiceDate);
    checks.push({
      criterion: 'invoice_age',
      passed: invoiceAge <= 60,
      message: invoiceAge <= 60
        ? `Invoice is ${invoiceAge} days old (within 60-day limit)`
        : `Invoice is ${invoiceAge} days old (exceeds 60-day limit)`
    });

    // Amount check
    checks.push({
      criterion: 'minimum_amount',
      passed: invoice.amount >= 10000,
      message: invoice.amount >= 10000
        ? `Invoice amount Rs ${invoice.amount.toLocaleString()} meets minimum`
        : `Invoice amount Rs ${invoice.amount.toLocaleString()} below Rs 10,000 minimum`
    });

    // Days to due date
    const daysTodue = differenceInDays(invoice.dueDate, new Date());
    checks.push({
      criterion: 'days_to_due',
      passed: daysTodue >= 15,
      message: daysTodue >= 15
        ? `${daysTodue} days until due date`
        : `Only ${daysTodue} days until due date (minimum 15 required)`
    });

    // Supplier KYC
    const kycStatus = await this.kycService.getStatus(supplier.id);
    checks.push({
      criterion: 'supplier_kyc',
      passed: kycStatus.status === 'VERIFIED',
      message: kycStatus.status === 'VERIFIED'
        ? 'Supplier KYC verified'
        : `Supplier KYC status: ${kycStatus.status}`
    });

    // Buyer payment history
    const buyerDefaults = await this.paymentHistoryService.getDefaults(buyer.id, 12);
    checks.push({
      criterion: 'buyer_creditworthiness',
      passed: buyerDefaults.count < 3,
      message: buyerDefaults.count < 3
        ? 'Buyer has acceptable payment history'
        : `Buyer has ${buyerDefaults.count} payment defaults in last 12 months`
    });

    const eligible = checks.every(c => c.passed);

    return {
      eligible,
      checks,
      maxFinancingAmount: eligible ? this.calculateMaxFinancing(invoice) : undefined,
      suggestedTenure: eligible ? daysTodue : undefined,
      ineligibilityReasons: checks.filter(c => !c.passed).map(c => c.message)
    };
  }

  private calculateMaxFinancing(invoice: Invoice): number {
    // Maximum 85% of invoice value
    return Math.floor(invoice.amount * 0.85);
  }
}
```

#### Risk Scoring Model

| Factor | Weight | Data Source | Score Range |
|--------|--------|-------------|-------------|
| **Platform transaction history** | 25% | Order history | 0-100 |
| **Fulfillment rate** | 15% | Fulfillment records | 0-100 |
| **Payment collection history** | 20% | Payment records | 0-100 |
| **GST compliance score** | 15% | GST API | 0-100 |
| **Buyer relationship length** | 10% | Platform data | 0-100 |
| **Industry risk** | 10% | Sector classification | 0-100 |
| **Invoice characteristics** | 5% | Invoice details | 0-100 |

```typescript
// Risk scoring implementation
interface RiskScoreBreakdown {
  overallScore: number;        // 0-100
  riskCategory: 'low' | 'medium' | 'high';
  factors: RiskFactor[];
  recommendedRate: number;     // Suggested discount rate
  maxFinancingPercent: number; // Max % of invoice
}

@Injectable()
export class RiskScoringService {
  private readonly WEIGHTS = {
    transactionHistory: 0.25,
    fulfillmentRate: 0.15,
    paymentHistory: 0.20,
    gstCompliance: 0.15,
    relationshipLength: 0.10,
    industryRisk: 0.10,
    invoiceCharacteristics: 0.05
  };

  async calculateRiskScore(
    supplierId: string,
    buyerId: string,
    invoiceId: string
  ): Promise<RiskScoreBreakdown> {
    const factors: RiskFactor[] = [];

    // Transaction history score
    const txHistory = await this.getTransactionHistory(supplierId);
    const txScore = this.scoreTransactionHistory(txHistory);
    factors.push({ name: 'transactionHistory', score: txScore, weight: this.WEIGHTS.transactionHistory });

    // Fulfillment rate score
    const fulfillment = await this.getFulfillmentMetrics(supplierId);
    const fulfillScore = fulfillment.rate * 100;
    factors.push({ name: 'fulfillmentRate', score: fulfillScore, weight: this.WEIGHTS.fulfillmentRate });

    // Payment history score
    const paymentHistory = await this.getPaymentHistory(supplierId);
    const paymentScore = this.scorePaymentHistory(paymentHistory);
    factors.push({ name: 'paymentHistory', score: paymentScore, weight: this.WEIGHTS.paymentHistory });

    // GST compliance
    const gstData = await this.gstService.getComplianceScore(supplierId);
    factors.push({ name: 'gstCompliance', score: gstData.score, weight: this.WEIGHTS.gstCompliance });

    // Relationship length
    const relationship = await this.getRelationshipMetrics(supplierId, buyerId);
    const relationshipScore = Math.min(relationship.months * 5, 100);
    factors.push({ name: 'relationshipLength', score: relationshipScore, weight: this.WEIGHTS.relationshipLength });

    // Industry risk
    const supplier = await this.supplierRepository.findById(supplierId);
    const industryScore = this.getIndustryRiskScore(supplier.industrySector);
    factors.push({ name: 'industryRisk', score: industryScore, weight: this.WEIGHTS.industryRisk });

    // Invoice characteristics
    const invoice = await this.invoiceRepository.findById(invoiceId);
    const invoiceScore = this.scoreInvoiceCharacteristics(invoice);
    factors.push({ name: 'invoiceCharacteristics', score: invoiceScore, weight: this.WEIGHTS.invoiceCharacteristics });

    // Calculate weighted score
    const overallScore = factors.reduce((sum, f) => sum + (f.score * f.weight), 0);

    return {
      overallScore: Math.round(overallScore),
      riskCategory: this.categorizeRisk(overallScore),
      factors,
      recommendedRate: this.calculateRecommendedRate(overallScore),
      maxFinancingPercent: this.calculateMaxFinancingPercent(overallScore)
    };
  }

  private categorizeRisk(score: number): 'low' | 'medium' | 'high' {
    if (score >= 75) return 'low';
    if (score >= 50) return 'medium';
    return 'high';
  }

  private calculateRecommendedRate(score: number): number {
    // Higher score = lower rate
    // Range: 12% (high risk) to 8% (low risk) annual
    return 12 - (score / 100) * 4;
  }
}
```

#### Repayment Tracking System

```typescript
// Repayment tracking schema
interface RepaymentSchedule {
  financingId: string;
  invoiceId: string;
  principal: number;
  discountAmount: number;
  totalDue: number;
  dueDate: Date;
  status: 'pending' | 'partially_paid' | 'paid' | 'overdue' | 'defaulted';
  payments: RepaymentPayment[];
  remindersSent: ReminderRecord[];
}

interface RepaymentPayment {
  id: string;
  amount: number;
  paymentDate: Date;
  source: 'buyer_payment' | 'supplier_payment' | 'platform_recovery';
  reference: string;
  verificationStatus: 'pending' | 'verified' | 'failed';
}

@Injectable()
export class RepaymentTrackingService {
  // Daily check for due payments
  @Cron('0 9 * * *')  // 9 AM daily
  async checkDuePayments(): Promise<void> {
    const today = startOfDay(new Date());

    // Find payments due today
    const dueToday = await this.repaymentRepository.findByDueDate(today);

    for (const repayment of dueToday) {
      if (repayment.status === 'pending') {
        await this.sendDueDateReminder(repayment);
      }
    }

    // Find overdue payments
    const overdue = await this.repaymentRepository.findOverdue();

    for (const repayment of overdue) {
      const daysOverdue = differenceInDays(today, repayment.dueDate);

      if (daysOverdue === 1) {
        await this.handleOneDayOverdue(repayment);
      } else if (daysOverdue === 3) {
        await this.handleThreeDaysOverdue(repayment);
      } else if (daysOverdue === 7) {
        await this.handleSevenDaysOverdue(repayment);
      } else if (daysOverdue >= 30) {
        await this.handleDefault(repayment);
      }
    }
  }

  // Process buyer payment and route to lender
  async processRepayment(invoiceId: string, payment: IncomingPayment): Promise<void> {
    const financing = await this.financingRepository.findByInvoiceId(invoiceId);

    if (!financing) {
      // No financing on this invoice - normal payment flow
      return;
    }

    const repayment = await this.repaymentRepository.findByFinancingId(financing.id);

    // Calculate amounts
    const repaymentAmount = Math.min(payment.amount, repayment.totalDue - repayment.amountPaid);
    const supplierAmount = payment.amount - repaymentAmount;

    // Record payment
    await this.repaymentRepository.addPayment(repayment.id, {
      amount: repaymentAmount,
      paymentDate: new Date(),
      source: 'buyer_payment',
      reference: payment.reference,
      verificationStatus: 'pending'
    });

    // Transfer to lender
    await this.transferToLender(financing.lenderId, repaymentAmount, financing.id);

    // Transfer remainder to supplier (if any)
    if (supplierAmount > 0) {
      await this.transferToSupplier(financing.supplierId, supplierAmount, invoiceId);
    }

    // Update status
    const newStatus = repayment.amountPaid + repaymentAmount >= repayment.totalDue
      ? 'paid'
      : 'partially_paid';

    await this.repaymentRepository.updateStatus(repayment.id, newStatus);

    // Notify parties
    await this.notifyRepaymentProcessed(financing, repaymentAmount, newStatus);
  }
}
```

### Exception Paths: Disputes, Chargebacks, and Delayed Payments

#### Exception Handling Matrix

| Exception Type | Trigger | Immediate Action | Resolution Path | Financial Impact |
|----------------|---------|------------------|-----------------|------------------|
| **Invoice dispute** | Buyer disputes invoice | Pause financing request | Dispute resolution workflow | Financing blocked until resolved |
| **Quality dispute** | Delivery acceptance issues | Notify lender | Pro-rata adjustment | Reduce financing amount |
| **Partial payment** | Buyer pays less than due | Calculate shortfall | Collection from supplier | Supplier liability for shortfall |
| **Payment delay** | T+3 after due date | Reminder escalation | Grace period + penalties | Interest accrual |
| **Payment default** | T+30 after due date | Notify lender, initiate recovery | Legal/collection process | Platform recovery from supplier |
| **Supplier bankruptcy** | Insolvency notice | Freeze accounts | Lender insurance claim | Without-recourse (TReDS) or with-recourse |
| **Buyer bankruptcy** | Insolvency notice | Notify lender | Insurance/legal | Depends on financing type |
| **Chargeback** | Payment reversal | Block supplier payout | Investigation | Hold funds |

```typescript
// Exception handling implementation
interface FinancingException {
  id: string;
  financingId: string;
  type: ExceptionType;
  status: 'open' | 'investigating' | 'resolved' | 'escalated';
  createdAt: Date;
  resolvedAt?: Date;
  resolution?: ExceptionResolution;
  financialImpact: FinancialImpact;
}

enum ExceptionType {
  INVOICE_DISPUTE = 'INVOICE_DISPUTE',
  QUALITY_DISPUTE = 'QUALITY_DISPUTE',
  PARTIAL_PAYMENT = 'PARTIAL_PAYMENT',
  PAYMENT_DELAY = 'PAYMENT_DELAY',
  PAYMENT_DEFAULT = 'PAYMENT_DEFAULT',
  CHARGEBACK = 'CHARGEBACK',
  SUPPLIER_INSOLVENCY = 'SUPPLIER_INSOLVENCY',
  BUYER_INSOLVENCY = 'BUYER_INSOLVENCY'
}

@Injectable()
export class FinancingExceptionService {
  @OnEvent('invoice.disputed')
  async handleInvoiceDispute(event: InvoiceDisputedEvent): Promise<void> {
    const { invoiceId, disputeReason, raisedBy } = event;

    // Check if invoice has active financing
    const financing = await this.financingRepository.findByInvoiceId(invoiceId);

    if (financing && financing.status === 'PENDING_DISBURSEMENT') {
      // Pause disbursement
      await this.financingRepository.updateStatus(financing.id, 'ON_HOLD');

      // Create exception record
      await this.exceptionRepository.create({
        financingId: financing.id,
        type: ExceptionType.INVOICE_DISPUTE,
        status: 'open',
        metadata: { disputeReason, raisedBy }
      });

      // Notify all parties
      await this.notifyDisputeCreated(financing, disputeReason);
    }

    if (financing && financing.status === 'DISBURSED') {
      // Already disbursed - more complex
      await this.handlePostDisbursementDispute(financing, event);
    }
  }

  @OnEvent('payment.delayed')
  async handlePaymentDelay(event: PaymentDelayedEvent): Promise<void> {
    const { financingId, daysOverdue } = event;
    const financing = await this.financingRepository.findById(financingId);

    // Create or update exception
    let exception = await this.exceptionRepository.findByFinancingAndType(
      financingId,
      ExceptionType.PAYMENT_DELAY
    );

    if (!exception) {
      exception = await this.exceptionRepository.create({
        financingId,
        type: ExceptionType.PAYMENT_DELAY,
        status: 'open'
      });
    }

    // Escalation based on days overdue
    if (daysOverdue >= 30) {
      await this.escalateToDefault(financing, exception);
    } else if (daysOverdue >= 7) {
      await this.initiateCollectionProcess(financing);
      await this.chargeLateFee(financing, daysOverdue);
    } else if (daysOverdue >= 3) {
      await this.sendEscalatedReminder(financing);
    }
  }

  private async handlePostDisbursementDispute(
    financing: Financing,
    event: InvoiceDisputedEvent
  ): Promise<void> {
    // Notify lender immediately
    await this.middlewareClient.reportDispute(financing.middlewareFinancingId, {
      reason: event.disputeReason,
      invoiceAmount: financing.invoiceAmount,
      financedAmount: financing.principal
    });

    // Create exception with higher severity
    await this.exceptionRepository.create({
      financingId: financing.id,
      type: ExceptionType.INVOICE_DISPUTE,
      status: 'escalated',
      metadata: {
        disputeReason: event.disputeReason,
        disbursedAmount: financing.disbursedAmount,
        disbursedAt: financing.disbursedAt
      }
    });

    // Alert operations team
    await this.alertService.sendCritical('post_disbursement_dispute', {
      financingId: financing.id,
      amount: financing.principal,
      supplier: financing.supplierId
    });
  }

  // Chargeback handling
  @OnEvent('payment.chargeback')
  async handleChargeback(event: ChargebackEvent): Promise<void> {
    const { paymentId, amount, reason } = event;

    // Find associated financing
    const repayment = await this.repaymentRepository.findByPaymentId(paymentId);
    if (!repayment) return;

    const financing = await this.financingRepository.findById(repayment.financingId);

    // Reverse the payment record
    await this.repaymentRepository.reversePayment(paymentId, {
      reason: 'chargeback',
      chargebackReference: event.chargebackReference
    });

    // Block any pending payouts to supplier
    await this.payoutService.blockPayouts(financing.supplierId, {
      reason: 'chargeback_investigation',
      relatedFinancingId: financing.id
    });

    // Create exception
    await this.exceptionRepository.create({
      financingId: financing.id,
      type: ExceptionType.CHARGEBACK,
      status: 'investigating',
      financialImpact: {
        amount,
        type: 'liability',
        responsibleParty: 'pending_investigation'
      }
    });

    // Initiate investigation
    await this.investigationService.createInvestigation({
      type: 'chargeback',
      financingId: financing.id,
      amount,
      parties: [financing.supplierId, financing.buyerId]
    });
  }
}
```

### Open Questions

- **Q:** How will funding status updates be communicated to buyers and suppliers?
  - **A:** Multi-channel communication strategy:

  **Communication Channels by Event:**
  | Event | Supplier Channel | Buyer Channel | Urgency |
  |-------|------------------|---------------|---------|
  | Financing requested | Email + In-app | N/A | Normal |
  | Offers received | Email + Push + In-app | N/A | High |
  | Offer selected | Email + In-app | Email (acknowledgment request) | Normal |
  | Disbursement pending | Push + In-app | N/A | Normal |
  | Funds disbursed | Email + SMS + Push | Email (payment notice) | High |
  | Payment reminder (T-7) | N/A | Email + In-app | Normal |
  | Payment reminder (T-1) | N/A | Email + Push | High |
  | Payment due today | In-app | Email + SMS + Push | Critical |
  | Payment overdue | Email | Email + SMS + Push + Call | Critical |
  | Payment received | Email + In-app | Email + In-app | Normal |
  | Financing completed | Email + In-app | Email | Normal |

  **Notification Implementation:**
  ```typescript
  // Notification templates by event
  interface NotificationConfig {
    event: string;
    channels: {
      supplier?: ChannelConfig[];
      buyer?: ChannelConfig[];
    };
    priority: 'low' | 'normal' | 'high' | 'critical';
  }

  const NOTIFICATION_CONFIGS: NotificationConfig[] = [
    {
      event: 'financing.disbursed',
      channels: {
        supplier: [
          { type: 'email', template: 'financing-disbursed-supplier' },
          { type: 'sms', template: 'disbursed-sms' },
          { type: 'push', template: 'disbursed-push' },
          { type: 'in_app', template: 'disbursed-notification' }
        ],
        buyer: [
          { type: 'email', template: 'payment-notice-buyer' }
        ]
      },
      priority: 'high'
    },
    {
      event: 'repayment.overdue',
      channels: {
        supplier: [
          { type: 'email', template: 'overdue-notice-supplier' }
        ],
        buyer: [
          { type: 'email', template: 'overdue-reminder-buyer' },
          { type: 'sms', template: 'overdue-sms' },
          { type: 'push', template: 'overdue-push' },
          { type: 'phone_call', template: 'overdue-call-script', afterDays: 7 }
        ]
      },
      priority: 'critical'
    }
  ];

  @Injectable()
  export class FinancingNotificationService {
    async notifyStatusChange(
      financingId: string,
      event: string,
      data: Record<string, any>
    ): Promise<void> {
      const config = NOTIFICATION_CONFIGS.find(c => c.event === event);
      if (!config) return;

      const financing = await this.financingRepository.findById(financingId);

      // Supplier notifications
      if (config.channels.supplier) {
        for (const channel of config.channels.supplier) {
          await this.sendNotification(
            financing.supplierId,
            'supplier',
            channel,
            { ...data, financing }
          );
        }
      }

      // Buyer notifications
      if (config.channels.buyer) {
        for (const channel of config.channels.buyer) {
          await this.sendNotification(
            financing.buyerId,
            'buyer',
            channel,
            { ...data, financing }
          );
        }
      }
    }

    private async sendNotification(
      recipientId: string,
      recipientType: 'supplier' | 'buyer',
      channel: ChannelConfig,
      data: any
    ): Promise<void> {
      const recipient = recipientType === 'supplier'
        ? await this.supplierRepository.findById(recipientId)
        : await this.buyerRepository.findById(recipientId);

      const content = await this.templateService.render(channel.template, data);

      switch (channel.type) {
        case 'email':
          await this.emailService.send(recipient.email, content);
          break;
        case 'sms':
          await this.smsService.send(recipient.phone, content);
          break;
        case 'push':
          await this.pushService.send(recipientId, content);
          break;
        case 'in_app':
          await this.inAppNotificationService.create(recipientId, content);
          break;
        case 'phone_call':
          await this.callService.scheduleCall(recipient.phone, content);
          break;
      }

      // Log for audit
      await this.notificationLogRepository.insert({
        recipientId,
        recipientType,
        channel: channel.type,
        template: channel.template,
        sentAt: new Date(),
        financingId: data.financing.id
      });
    }
  }
  ```

  **Real-time Status Dashboard:**
  - Supplier dashboard shows: Current financing status, expected disbursement date, repayment schedule
  - Buyer dashboard shows: Financed invoices pending payment, due dates, payment instructions
  - WebSocket updates for status changes ensure real-time visibility

---

## References
- [Saga Pattern](https://microservices.io/patterns/data/saga.html)
- [Medusa Workflows](https://docs.medusajs.com/development/workflows/overview)
- [Invoice Financing Best Practices](https://www.credable.in/blog/)
