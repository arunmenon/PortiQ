# ADR-FN-018: TReDS Platform Integration

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

TReDS (Trade Receivables Discounting System) is an RBI-regulated platform for invoice discounting that provides "without recourse" financing—meaning suppliers have no liability if buyers default.

### Business Context
India has five licensed TReDS platforms:
- **M1xchange**: Largest platform, 66+ banks, ₹1.7 Lakh Cr+ discounted
- **RXIL**: NSE + SIDBI backed, pioneer platform
- **Invoicemart**: Axis Bank + mjunction backed
- **C2treds**: C2FO international technology
- **DTX (KredX)**: Newest license (January 2025)

TReDS offers unique advantages:
- RBI-mandated "without recourse" (no supplier liability on default)
- Competitive rates through auction among financiers
- Large buyer participation (companies >₹250 Cr turnover must register by June 2025)
- Trusted infrastructure for large transactions

### Technical Context
- Each TReDS platform has its own API and integration requirements
- GST verification and MSME registration required
- Invoice must be acknowledged by buyer on platform
- Auction-based pricing among registered financiers
- Typically T+1 to T+3 disbursement

### Assumptions
- Suppliers have MSME registration (Udyam)
- Buyers are willing to acknowledge invoices
- API access available for licensed integrators
- Volume justifies integration complexity

---

## Decision Drivers

- Access to "without recourse" financing
- Competitive rates through auction
- Regulatory compliance and trust
- Integration complexity vs. benefit
- Coverage of buyer universe
- Operational efficiency

---

## Considered Options

### Option 1: Single TReDS Platform Integration
**Description:** Integrate with one TReDS platform (M1xchange as largest).

**Pros:**
- Simpler integration
- Lower maintenance
- Single relationship

**Cons:**
- Limited to one platform's financiers
- No rate comparison
- Platform dependency

### Option 2: Multi-Platform Integration
**Description:** Integrate with multiple TReDS platforms for best rate access.

**Pros:**
- Access to all financiers
- Best rate through comparison
- Platform redundancy

**Cons:**
- Multiple integrations to maintain
- Complex rate comparison logic
- Higher implementation cost

### Option 3: TReDS Aggregator Approach
**Description:** Use aggregator service that connects to multiple TReDS platforms.

**Pros:**
- Single integration point
- Automatic platform selection
- Reduced complexity

**Cons:**
- Aggregator fees
- Third-party dependency
- Limited market (aggregators emerging)

---

## Decision

**Chosen Option:** Multi-Platform Integration (M1xchange + RXIL)

We will integrate directly with M1xchange (largest) and RXIL (most transparent) initially, with architecture supporting additional platforms over time.

### Rationale
Direct integration with two major platforms provides access to a broad financier base while maintaining manageable complexity. M1xchange offers the largest network, while RXIL provides transparent auction mechanics. The architecture will support adding more platforms as volume grows.

---

## Consequences

### Positive
- Access to "without recourse" financing
- Competitive rates through auction
- Broad financier network coverage
- Platform redundancy
- Regulatory compliance

### Negative
- Two integrations to maintain
- **Mitigation:** Abstract behind common interface
- Different API patterns per platform
- **Mitigation:** Adapter pattern, normalization layer

### Risks
- API changes by platforms: Version management, monitoring
- Platform downtime: Failover between platforms
- Buyer non-acknowledgment: Clear communication, reminders

---

## Implementation Notes

### Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       TReDS Integration Layer                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   TReDS Adapter Interface                     │   │
│  │                                                               │   │
│  │   uploadInvoice()    │ getAuctionStatus()  │ getBids()       │   │
│  │   acknowledgeInvoice()│ acceptBid()        │ getDisbursement()│   │
│  │                                                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                            │                                         │
│              ┌─────────────┴─────────────┐                          │
│              │                           │                          │
│  ┌───────────▼───────────┐   ┌──────────▼────────────┐             │
│  │   M1xchange Adapter   │   │     RXIL Adapter      │             │
│  │                       │   │                       │             │
│  │  - OAuth2 Auth       │   │  - API Key Auth       │             │
│  │  - REST API          │   │  - REST API           │             │
│  │  - Webhook Events    │   │  - Polling            │             │
│  │                       │   │                       │             │
│  └───────────────────────┘   └───────────────────────┘             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### TReDS Adapter Interface

```typescript
// treds/interfaces/treds-adapter.interface.ts
export interface TredsAdapter {
  platform: TredsPlatform;

  // Invoice operations
  uploadInvoice(invoice: TredsInvoice): Promise<TredsInvoiceResponse>;
  getInvoiceStatus(invoiceId: string): Promise<TredsInvoiceStatus>;

  // Buyer acknowledgment
  requestAcknowledgment(invoiceId: string): Promise<AckRequestResponse>;
  getAcknowledgmentStatus(invoiceId: string): Promise<AckStatus>;

  // Auction operations
  startAuction(invoiceId: string, params: AuctionParams): Promise<AuctionResponse>;
  getAuctionBids(auctionId: string): Promise<TredsBid[]>;
  acceptBid(auctionId: string, bidId: string): Promise<BidAcceptance>;

  // Disbursement
  getDisbursementStatus(acceptanceId: string): Promise<DisbursementStatus>;

  // Utility
  validateGstin(gstin: string): Promise<GstinValidation>;
  checkBuyerRegistration(buyerGstin: string): Promise<BuyerRegistration>;
}

export enum TredsPlatform {
  M1XCHANGE = 'M1XCHANGE',
  RXIL = 'RXIL',
  INVOICEMART = 'INVOICEMART'
}

export interface TredsInvoice {
  invoiceNumber: string;
  invoiceDate: Date;
  amount: number;
  gstin: {
    seller: string;
    buyer: string;
  };
  dueDate: Date;
  description: string;
  lineItems: TredsLineItem[];
  supportingDocuments: DocumentReference[];
}

export interface TredsBid {
  bidId: string;
  financierId: string;
  financierName: string;
  bidAmount: number;
  discountRate: number;  // Annual %
  netAmount: number;     // After discount
  validUntil: Date;
  tenure: number;        // Days
}
```

### M1xchange Adapter Implementation

```typescript
// treds/adapters/m1xchange.adapter.ts
@Injectable()
export class M1xchangeAdapter implements TredsAdapter {
  platform = TredsPlatform.M1XCHANGE;

  private readonly baseUrl: string;
  private accessToken: string;
  private tokenExpiry: Date;

  constructor(
    private readonly httpService: HttpService,
    private readonly configService: ConfigService
  ) {
    this.baseUrl = this.configService.get('M1XCHANGE_API_URL');
  }

  private async ensureAuthenticated(): Promise<void> {
    if (this.accessToken && this.tokenExpiry > new Date()) {
      return;
    }

    const response = await this.httpService.post(
      `${this.baseUrl}/oauth/token`,
      {
        grant_type: 'client_credentials',
        client_id: this.configService.get('M1XCHANGE_CLIENT_ID'),
        client_secret: this.configService.get('M1XCHANGE_CLIENT_SECRET'),
        scope: 'invoice auction'
      }
    ).toPromise();

    this.accessToken = response.data.access_token;
    this.tokenExpiry = new Date(Date.now() + response.data.expires_in * 1000);
  }

  async uploadInvoice(invoice: TredsInvoice): Promise<TredsInvoiceResponse> {
    await this.ensureAuthenticated();

    const payload = this.mapToM1xchangeFormat(invoice);

    const response = await this.httpService.post(
      `${this.baseUrl}/v1/invoices`,
      payload,
      {
        headers: {
          'Authorization': `Bearer ${this.accessToken}`,
          'Content-Type': 'application/json'
        }
      }
    ).toPromise();

    return {
      platformInvoiceId: response.data.invoice_id,
      status: this.mapStatus(response.data.status),
      uploadedAt: new Date(),
      platform: this.platform
    };
  }

  async startAuction(
    invoiceId: string,
    params: AuctionParams
  ): Promise<AuctionResponse> {
    await this.ensureAuthenticated();

    const response = await this.httpService.post(
      `${this.baseUrl}/v1/invoices/${invoiceId}/auction`,
      {
        start_time: params.startTime.toISOString(),
        end_time: params.endTime.toISOString(),
        min_bid_amount: params.minBidAmount,
        factoring_unit_id: params.factoringUnitId
      },
      {
        headers: { 'Authorization': `Bearer ${this.accessToken}` }
      }
    ).toPromise();

    return {
      auctionId: response.data.auction_id,
      status: 'ACTIVE',
      startTime: new Date(response.data.start_time),
      endTime: new Date(response.data.end_time),
      platform: this.platform
    };
  }

  async getAuctionBids(auctionId: string): Promise<TredsBid[]> {
    await this.ensureAuthenticated();

    const response = await this.httpService.get(
      `${this.baseUrl}/v1/auctions/${auctionId}/bids`,
      {
        headers: { 'Authorization': `Bearer ${this.accessToken}` }
      }
    ).toPromise();

    return response.data.bids.map(bid => ({
      bidId: bid.bid_id,
      financierId: bid.financier_id,
      financierName: bid.financier_name,
      bidAmount: bid.bid_amount,
      discountRate: bid.discount_rate,
      netAmount: bid.net_amount,
      validUntil: new Date(bid.valid_until),
      tenure: bid.tenure_days
    }));
  }

  private mapToM1xchangeFormat(invoice: TredsInvoice): object {
    return {
      invoice_number: invoice.invoiceNumber,
      invoice_date: invoice.invoiceDate.toISOString().split('T')[0],
      invoice_amount: invoice.amount,
      seller_gstin: invoice.gstin.seller,
      buyer_gstin: invoice.gstin.buyer,
      due_date: invoice.dueDate.toISOString().split('T')[0],
      description: invoice.description,
      line_items: invoice.lineItems.map(item => ({
        description: item.description,
        quantity: item.quantity,
        unit_price: item.unitPrice,
        amount: item.amount,
        hsn_code: item.hsnCode
      }))
    };
  }
}
```

### RXIL Adapter Implementation

```typescript
// treds/adapters/rxil.adapter.ts
@Injectable()
export class RxilAdapter implements TredsAdapter {
  platform = TredsPlatform.RXIL;

  private readonly baseUrl: string;
  private readonly apiKey: string;

  constructor(
    private readonly httpService: HttpService,
    private readonly configService: ConfigService
  ) {
    this.baseUrl = this.configService.get('RXIL_API_URL');
    this.apiKey = this.configService.get('RXIL_API_KEY');
  }

  async uploadInvoice(invoice: TredsInvoice): Promise<TredsInvoiceResponse> {
    const payload = this.mapToRxilFormat(invoice);

    const response = await this.httpService.post(
      `${this.baseUrl}/api/v2/invoice/upload`,
      payload,
      {
        headers: {
          'X-API-Key': this.apiKey,
          'Content-Type': 'application/json'
        }
      }
    ).toPromise();

    return {
      platformInvoiceId: response.data.invoiceRefNo,
      status: this.mapStatus(response.data.status),
      uploadedAt: new Date(),
      platform: this.platform
    };
  }

  // ... other method implementations similar to M1xchange
}
```

### TReDS Service (Orchestrator)

```typescript
// treds/services/treds.service.ts
@Injectable()
export class TredsService {
  private adapters: Map<TredsPlatform, TredsAdapter>;

  constructor(
    private readonly m1xchangeAdapter: M1xchangeAdapter,
    private readonly rxilAdapter: RxilAdapter
  ) {
    this.adapters = new Map([
      [TredsPlatform.M1XCHANGE, m1xchangeAdapter],
      [TredsPlatform.RXIL, rxilAdapter]
    ]);
  }

  async submitInvoice(
    invoice: TredsInvoice,
    preferredPlatform?: TredsPlatform
  ): Promise<TredsInvoiceResponse> {
    // Check buyer registration on each platform
    const registrations = await this.checkBuyerRegistrations(invoice.gstin.buyer);

    // Select platform based on registration and preference
    const platform = this.selectPlatform(registrations, preferredPlatform);

    if (!platform) {
      throw new Error('Buyer not registered on any TReDS platform');
    }

    const adapter = this.adapters.get(platform);
    return adapter.uploadInvoice(invoice);
  }

  async getBestBids(auctionIds: Map<TredsPlatform, string>): Promise<TredsBid[]> {
    const allBids: TredsBid[] = [];

    for (const [platform, auctionId] of auctionIds) {
      const adapter = this.adapters.get(platform);
      const bids = await adapter.getAuctionBids(auctionId);
      allBids.push(...bids.map(bid => ({ ...bid, platform })));
    }

    // Sort by effective rate (lower is better)
    allBids.sort((a, b) => a.discountRate - b.discountRate);

    return allBids;
  }

  async acceptBestBid(bid: TredsBid): Promise<BidAcceptance> {
    const adapter = this.adapters.get(bid.platform);
    return adapter.acceptBid(bid.auctionId, bid.bidId);
  }

  private async checkBuyerRegistrations(
    buyerGstin: string
  ): Promise<Map<TredsPlatform, BuyerRegistration>> {
    const registrations = new Map<TredsPlatform, BuyerRegistration>();

    const checks = await Promise.all(
      Array.from(this.adapters.entries()).map(async ([platform, adapter]) => {
        try {
          const registration = await adapter.checkBuyerRegistration(buyerGstin);
          return { platform, registration };
        } catch {
          return { platform, registration: null };
        }
      })
    );

    for (const { platform, registration } of checks) {
      if (registration?.registered) {
        registrations.set(platform, registration);
      }
    }

    return registrations;
  }

  private selectPlatform(
    registrations: Map<TredsPlatform, BuyerRegistration>,
    preferred?: TredsPlatform
  ): TredsPlatform | null {
    if (preferred && registrations.has(preferred)) {
      return preferred;
    }

    // Default priority: M1xchange > RXIL > others
    const priority = [TredsPlatform.M1XCHANGE, TredsPlatform.RXIL];

    for (const platform of priority) {
      if (registrations.has(platform)) {
        return platform;
      }
    }

    return registrations.size > 0 ? registrations.keys().next().value : null;
  }
}
```

### Database Schema

```sql
-- TReDS transactions
CREATE TABLE treds_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID REFERENCES invoices(id),
    platform VARCHAR(20) NOT NULL,
    platform_invoice_id VARCHAR(100),
    platform_auction_id VARCHAR(100),

    -- Status tracking
    status VARCHAR(30) NOT NULL DEFAULT 'UPLOADED',
    acknowledgment_status VARCHAR(30),
    auction_status VARCHAR(30),
    disbursement_status VARCHAR(30),

    -- Auction details
    auction_start TIMESTAMPTZ,
    auction_end TIMESTAMPTZ,
    bids_received INTEGER DEFAULT 0,

    -- Accepted bid
    accepted_bid_id VARCHAR(100),
    accepted_financier VARCHAR(100),
    accepted_rate DECIMAL(5, 2),
    accepted_amount DECIMAL(15, 2),

    -- Disbursement
    disbursed_amount DECIMAL(15, 2),
    disbursed_at TIMESTAMPTZ,
    utr_number VARCHAR(50),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_treds_invoice ON treds_transactions(invoice_id);
CREATE INDEX idx_treds_status ON treds_transactions(status);
```

### Dependencies
- ADR-FN-016: Embedded Finance Architecture
- ADR-FN-017: Invoice Financing Workflow
- ADR-NF-017: Data Encryption

### Migration Strategy
1. Register as authorized TReDS integrator
2. Complete platform onboarding (M1xchange, RXIL)
3. Implement adapter interfaces
4. Build M1xchange integration
5. Add RXIL integration
6. Create unified orchestration service
7. Implement monitoring and reconciliation

---

## Operational Considerations

### Certification and Onboarding Steps

#### TReDS Platform Onboarding Timeline

| Phase | Duration | M1xchange Steps | RXIL Steps | Deliverables |
|-------|----------|-----------------|------------|--------------|
| **1. Application** | 2-4 weeks | Submit application form, company docs | Submit application, DPIIT recognition | Approved application |
| **2. Agreement** | 2-3 weeks | Sign Participant Agreement | Sign Platform Agreement | Executed contracts |
| **3. Technical Setup** | 3-4 weeks | API credentials, sandbox access | API keys, test environment | Integration docs |
| **4. Integration** | 4-6 weeks | Build adapter, test flows | Build adapter, test flows | Working integration |
| **5. UAT** | 2-3 weeks | End-to-end testing | End-to-end testing | UAT sign-off |
| **6. Go-Live** | 1-2 weeks | Production credentials | Production access | Live transactions |
| **Total** | **14-22 weeks** | | | |

#### Detailed Onboarding Checklist

```typescript
// TReDS onboarding tracking
interface OnboardingChecklist {
  platform: TredsPlatform;
  steps: OnboardingStep[];
  startDate: Date;
  targetGoLiveDate: Date;
  currentPhase: number;
}

const M1XCHANGE_CHECKLIST: OnboardingStep[] = [
  // Phase 1: Application
  { id: 1, phase: 1, name: 'Submit company registration documents', status: 'pending', required: true },
  { id: 2, phase: 1, name: 'Submit PAN and GST registration', status: 'pending', required: true },
  { id: 3, phase: 1, name: 'Submit board resolution for TReDS participation', status: 'pending', required: true },
  { id: 4, phase: 1, name: 'Submit list of authorized signatories', status: 'pending', required: true },
  { id: 5, phase: 1, name: 'Complete online application form', status: 'pending', required: true },

  // Phase 2: Agreement
  { id: 6, phase: 2, name: 'Review Participant Agreement', status: 'pending', required: true },
  { id: 7, phase: 2, name: 'Legal review of terms', status: 'pending', required: true },
  { id: 8, phase: 2, name: 'Execute agreement (digital signature)', status: 'pending', required: true },
  { id: 9, phase: 2, name: 'Submit agreement fee (if applicable)', status: 'pending', required: true },

  // Phase 3: Technical Setup
  { id: 10, phase: 3, name: 'Receive API documentation', status: 'pending', required: true },
  { id: 11, phase: 3, name: 'Receive sandbox credentials', status: 'pending', required: true },
  { id: 12, phase: 3, name: 'Configure webhook endpoints', status: 'pending', required: true },
  { id: 13, phase: 3, name: 'Set up IP whitelisting', status: 'pending', required: true },
  { id: 14, phase: 3, name: 'Configure SSL certificates', status: 'pending', required: true },

  // Phase 4: Integration
  { id: 15, phase: 4, name: 'Implement authentication flow', status: 'pending', required: true },
  { id: 16, phase: 4, name: 'Implement invoice upload API', status: 'pending', required: true },
  { id: 17, phase: 4, name: 'Implement buyer acknowledgment API', status: 'pending', required: true },
  { id: 18, phase: 4, name: 'Implement auction APIs', status: 'pending', required: true },
  { id: 19, phase: 4, name: 'Implement bid acceptance API', status: 'pending', required: true },
  { id: 20, phase: 4, name: 'Implement disbursement tracking', status: 'pending', required: true },
  { id: 21, phase: 4, name: 'Implement webhook handlers', status: 'pending', required: true },

  // Phase 5: UAT
  { id: 22, phase: 5, name: 'Complete happy path testing', status: 'pending', required: true },
  { id: 23, phase: 5, name: 'Complete error handling testing', status: 'pending', required: true },
  { id: 24, phase: 5, name: 'Complete edge case testing', status: 'pending', required: true },
  { id: 25, phase: 5, name: 'Performance testing (load)', status: 'pending', required: true },
  { id: 26, phase: 5, name: 'Security assessment', status: 'pending', required: true },
  { id: 27, phase: 5, name: 'M1xchange UAT certification', status: 'pending', required: true },

  // Phase 6: Go-Live
  { id: 28, phase: 6, name: 'Receive production credentials', status: 'pending', required: true },
  { id: 29, phase: 6, name: 'Configure production environment', status: 'pending', required: true },
  { id: 30, phase: 6, name: 'Pilot transaction (single invoice)', status: 'pending', required: true },
  { id: 31, phase: 6, name: 'Full production rollout', status: 'pending', required: true }
];
```

#### API SLAs and Monitoring

| API Endpoint | Expected Response Time | Timeout | Retry Strategy | Alert Threshold |
|--------------|------------------------|---------|----------------|-----------------|
| Authentication | < 500ms | 5s | 3 retries, exp backoff | > 1s P95 |
| Invoice Upload | < 2s | 30s | 3 retries | > 5s P95 |
| Get Invoice Status | < 500ms | 5s | 3 retries | > 1s P95 |
| Start Auction | < 2s | 30s | No retry (idempotent check) | > 5s P95 |
| Get Bids | < 1s | 10s | 3 retries | > 2s P95 |
| Accept Bid | < 2s | 30s | No retry (idempotent check) | > 5s P95 |
| Disbursement Status | < 1s | 10s | 3 retries | > 2s P95 |
| Webhook Delivery | N/A (inbound) | N/A | Platform retries 3x | Miss rate > 1% |

```typescript
// SLA monitoring implementation
interface TredsSLAConfig {
  endpoint: string;
  expectedLatencyMs: number;
  timeoutMs: number;
  retries: number;
  circuitBreaker: {
    failureThreshold: number;
    resetTimeoutMs: number;
  };
}

const TREDS_SLA_CONFIGS: Record<string, TredsSLAConfig> = {
  'uploadInvoice': {
    endpoint: '/v1/invoices',
    expectedLatencyMs: 2000,
    timeoutMs: 30000,
    retries: 3,
    circuitBreaker: { failureThreshold: 5, resetTimeoutMs: 60000 }
  },
  'getAuctionBids': {
    endpoint: '/v1/auctions/{id}/bids',
    expectedLatencyMs: 1000,
    timeoutMs: 10000,
    retries: 3,
    circuitBreaker: { failureThreshold: 5, resetTimeoutMs: 30000 }
  }
};

@Injectable()
export class TredsSLAMonitor {
  @Cron('*/5 * * * *')  // Every 5 minutes
  async checkPlatformHealth(): Promise<void> {
    for (const platform of [TredsPlatform.M1XCHANGE, TredsPlatform.RXIL]) {
      const adapter = this.adapters.get(platform);

      try {
        const start = Date.now();
        await adapter.healthCheck();
        const latency = Date.now() - start;

        metrics.tredsHealthCheckLatency.observe({ platform }, latency / 1000);

        if (latency > 1000) {
          await this.alertService.sendWarning('treds_slow_response', { platform, latency });
        }
      } catch (error) {
        metrics.tredsHealthCheckFailure.inc({ platform });
        await this.alertService.sendCritical('treds_health_check_failed', { platform, error: error.message });
      }
    }
  }
}
```

#### Failure Recovery Procedures

| Failure Type | Detection | Auto-Recovery | Manual Recovery | RTO |
|--------------|-----------|---------------|-----------------|-----|
| **API timeout** | Request timeout | Retry with backoff | N/A | Immediate |
| **Auth failure** | 401 response | Refresh token | Check credentials | 5 min |
| **Rate limit** | 429 response | Queue + backoff | Request limit increase | 15 min |
| **Platform downtime** | Health check fail | Failover to secondary | Contact support | 30 min |
| **Webhook miss** | Missing callback | Poll for status | Manual reconciliation | 1 hour |
| **Data mismatch** | Reconciliation job | Alert + investigate | Manual correction | 4 hours |
| **Certificate expiry** | Pre-expiry check | Auto-renewal | Manual renewal | 24 hours |

```typescript
// Failure recovery implementation
@Injectable()
export class TredsFailureRecovery {
  @OnEvent('treds.api.failed')
  async handleApiFailure(event: TredsApiFailureEvent): Promise<void> {
    const { platform, endpoint, error, requestId } = event;

    // Log for audit
    await this.failureLogRepository.insert({
      platform,
      endpoint,
      errorCode: error.code,
      errorMessage: error.message,
      requestId,
      timestamp: new Date()
    });

    // Determine recovery action
    switch (error.code) {
      case 'ETIMEDOUT':
      case 'ECONNREFUSED':
        await this.handleConnectivityFailure(platform, requestId);
        break;

      case 'AUTH_EXPIRED':
        await this.handleAuthFailure(platform);
        break;

      case 'RATE_LIMITED':
        await this.handleRateLimit(platform, requestId);
        break;

      case 'INVOICE_NOT_FOUND':
      case 'AUCTION_EXPIRED':
        await this.handleBusinessError(platform, requestId, error);
        break;

      default:
        await this.handleUnknownError(platform, requestId, error);
    }
  }

  private async handleConnectivityFailure(platform: TredsPlatform, requestId: string): Promise<void> {
    // Check if it's a broader outage
    const recentFailures = await this.getRecentFailures(platform, 5);

    if (recentFailures >= 3) {
      // Likely platform outage - switch to secondary
      await this.failoverToSecondary(platform);
    } else {
      // Isolated failure - retry
      await this.queueRetry(requestId, { delay: 30000 });
    }
  }

  private async handleAuthFailure(platform: TredsPlatform): Promise<void> {
    const adapter = this.adapters.get(platform);

    try {
      await adapter.refreshAuthentication();
    } catch (error) {
      // Auth refresh failed - escalate
      await this.alertService.sendCritical('treds_auth_failure', {
        platform,
        error: error.message
      });
    }
  }

  private async failoverToSecondary(failedPlatform: TredsPlatform): Promise<void> {
    const secondary = failedPlatform === TredsPlatform.M1XCHANGE
      ? TredsPlatform.RXIL
      : TredsPlatform.M1XCHANGE;

    await this.configService.set(`treds.primaryPlatform`, secondary);

    await this.alertService.sendWarning('treds_failover', {
      from: failedPlatform,
      to: secondary
    });
  }
}
```

### Data Mapping and Reconciliation

#### Field Mapping Between Platform and TReDS

| Platform Field | M1xchange Field | RXIL Field | Transformation |
|----------------|-----------------|------------|----------------|
| `invoice.number` | `invoice_number` | `invoiceNo` | Direct |
| `invoice.date` | `invoice_date` (YYYY-MM-DD) | `invoiceDate` (DD-MM-YYYY) | Date format |
| `invoice.amount` | `invoice_amount` (paise) | `amount` (rupees) | Unit conversion |
| `invoice.dueDate` | `due_date` | `paymentDueDate` | Date format |
| `supplier.gstin` | `seller_gstin` | `sellerGSTIN` | Direct |
| `buyer.gstin` | `buyer_gstin` | `buyerGSTIN` | Direct |
| `lineItem.hsnCode` | `hsn_code` | `hsnSacCode` | Direct |
| `lineItem.quantity` | `quantity` | `qty` | Direct |
| `lineItem.unitPrice` | `unit_price` (paise) | `rate` (rupees) | Unit conversion |

```typescript
// Data mapping implementation
interface FieldMapping {
  platformField: string;
  tredsField: string;
  transform?: (value: any, platform: TredsPlatform) => any;
}

const INVOICE_FIELD_MAPPINGS: FieldMapping[] = [
  { platformField: 'invoiceNumber', tredsField: 'invoice_number' },
  {
    platformField: 'invoiceDate',
    tredsField: 'invoice_date',
    transform: (value, platform) => {
      if (platform === TredsPlatform.RXIL) {
        return format(value, 'dd-MM-yyyy');
      }
      return format(value, 'yyyy-MM-dd');
    }
  },
  {
    platformField: 'amount',
    tredsField: 'invoice_amount',
    transform: (value, platform) => {
      if (platform === TredsPlatform.M1XCHANGE) {
        return Math.round(value * 100);  // Convert to paise
      }
      return value;
    }
  },
  { platformField: 'supplierGstin', tredsField: 'seller_gstin' },
  { platformField: 'buyerGstin', tredsField: 'buyer_gstin' }
];

class TredsDataMapper {
  mapToTreds(invoice: Invoice, platform: TredsPlatform): Record<string, any> {
    const mapped: Record<string, any> = {};

    for (const mapping of INVOICE_FIELD_MAPPINGS) {
      const value = this.getNestedValue(invoice, mapping.platformField);
      const transformedValue = mapping.transform
        ? mapping.transform(value, platform)
        : value;

      // Platform-specific field names
      const fieldName = platform === TredsPlatform.RXIL
        ? this.toRxilFieldName(mapping.tredsField)
        : mapping.tredsField;

      mapped[fieldName] = transformedValue;
    }

    return mapped;
  }

  mapFromTreds(tredsData: any, platform: TredsPlatform): Partial<Invoice> {
    // Reverse mapping logic
    const mapped: Partial<Invoice> = {};

    for (const mapping of INVOICE_FIELD_MAPPINGS) {
      const fieldName = platform === TredsPlatform.RXIL
        ? this.toRxilFieldName(mapping.tredsField)
        : mapping.tredsField;

      const value = tredsData[fieldName];

      if (value !== undefined) {
        // Reverse transform if needed
        const transformedValue = this.reverseTransform(value, mapping, platform);
        this.setNestedValue(mapped, mapping.platformField, transformedValue);
      }
    }

    return mapped;
  }
}
```

#### Daily Reconciliation Process

```typescript
// TReDS reconciliation job
@Injectable()
export class TredsReconciliationService {
  @Cron('0 3 * * *')  // 3 AM daily
  async runDailyReconciliation(): Promise<TredsReconciliationReport> {
    const yesterday = subDays(startOfDay(new Date()), 1);

    const report: TredsReconciliationReport = {
      date: yesterday,
      platforms: {},
      discrepancies: [],
      status: 'pending'
    };

    for (const platform of [TredsPlatform.M1XCHANGE, TredsPlatform.RXIL]) {
      const platformReport = await this.reconcilePlatform(platform, yesterday);
      report.platforms[platform] = platformReport;
      report.discrepancies.push(...platformReport.discrepancies);
    }

    report.status = report.discrepancies.length > 0 ? 'review_required' : 'matched';

    await this.reconciliationRepository.save(report);

    if (report.discrepancies.length > 0) {
      await this.alertService.sendWarning('treds_reconciliation_discrepancy', {
        date: yesterday,
        count: report.discrepancies.length
      });
    }

    return report;
  }

  private async reconcilePlatform(
    platform: TredsPlatform,
    date: Date
  ): Promise<PlatformReconciliation> {
    // Get our records
    const ourTransactions = await this.tredsTransactionRepository.findByDate(platform, date);

    // Get TReDS records
    const adapter = this.adapters.get(platform);
    const tredsTransactions = await adapter.getTransactionHistory(date);

    const matched: MatchedTransaction[] = [];
    const ourOnly: TredsTransaction[] = [];
    const tredsOnly: any[] = [];
    const discrepancies: Discrepancy[] = [];

    // Match by invoice ID
    for (const our of ourTransactions) {
      const treds = tredsTransactions.find(t => t.platformInvoiceId === our.platformInvoiceId);

      if (treds) {
        // Check for mismatches
        const mismatches = this.findMismatches(our, treds);

        if (mismatches.length > 0) {
          discrepancies.push({
            transactionId: our.id,
            platformInvoiceId: our.platformInvoiceId,
            type: 'field_mismatch',
            mismatches
          });
        }

        matched.push({ our, treds });
      } else {
        ourOnly.push(our);
        discrepancies.push({
          transactionId: our.id,
          platformInvoiceId: our.platformInvoiceId,
          type: 'missing_on_treds'
        });
      }
    }

    // Find TReDS records not in our system
    for (const treds of tredsTransactions) {
      const our = ourTransactions.find(o => o.platformInvoiceId === treds.platformInvoiceId);
      if (!our) {
        tredsOnly.push(treds);
        discrepancies.push({
          platformInvoiceId: treds.platformInvoiceId,
          type: 'missing_in_platform'
        });
      }
    }

    return {
      platform,
      date,
      totalOurs: ourTransactions.length,
      totalTreds: tredsTransactions.length,
      matched: matched.length,
      ourOnly: ourOnly.length,
      tredsOnly: tredsOnly.length,
      discrepancies
    };
  }

  private findMismatches(our: TredsTransaction, treds: any): FieldMismatch[] {
    const mismatches: FieldMismatch[] = [];

    // Status mismatch
    if (our.status !== this.mapTredsStatus(treds.status)) {
      mismatches.push({
        field: 'status',
        ourValue: our.status,
        tredsValue: treds.status
      });
    }

    // Amount mismatch (with tolerance for rounding)
    if (Math.abs(our.acceptedAmount - treds.acceptedAmount) > 1) {
      mismatches.push({
        field: 'acceptedAmount',
        ourValue: our.acceptedAmount,
        tredsValue: treds.acceptedAmount
      });
    }

    // Disbursement status mismatch
    if (our.disbursementStatus !== treds.disbursementStatus) {
      mismatches.push({
        field: 'disbursementStatus',
        ourValue: our.disbursementStatus,
        tredsValue: treds.disbursementStatus
      });
    }

    return mismatches;
  }
}
```

### Open Questions

- **Q:** What is the plan for sandbox versus production testing timelines?
  - **A:** Detailed testing timeline and phases:

  **Testing Environment Progression:**
  | Phase | Environment | Duration | Entry Criteria | Exit Criteria |
  |-------|-------------|----------|----------------|---------------|
  | **Dev Integration** | Sandbox | 4 weeks | API credentials received | All endpoints callable |
  | **Functional Testing** | Sandbox | 2 weeks | Dev integration complete | All happy paths pass |
  | **Error Handling** | Sandbox | 1 week | Functional testing pass | Error scenarios handled |
  | **Performance Testing** | Sandbox | 1 week | Error handling pass | Meet latency targets |
  | **UAT** | Sandbox | 2 weeks | Performance pass | Platform sign-off |
  | **Pilot** | Production | 2 weeks | UAT sign-off | 10 successful transactions |
  | **Soft Launch** | Production | 2 weeks | Pilot success | No critical issues |
  | **Full Launch** | Production | Ongoing | Soft launch stable | N/A |

  **Sandbox Testing Checklist:**
  ```typescript
  interface TestScenario {
    id: string;
    name: string;
    category: 'happy_path' | 'error' | 'edge_case' | 'performance';
    platform: TredsPlatform;
    status: 'pending' | 'passed' | 'failed' | 'blocked';
    notes?: string;
  }

  const SANDBOX_TEST_SCENARIOS: TestScenario[] = [
    // Happy Path
    { id: 'HP-001', name: 'Upload invoice successfully', category: 'happy_path', platform: TredsPlatform.M1XCHANGE, status: 'pending' },
    { id: 'HP-002', name: 'Buyer acknowledges invoice', category: 'happy_path', platform: TredsPlatform.M1XCHANGE, status: 'pending' },
    { id: 'HP-003', name: 'Start auction successfully', category: 'happy_path', platform: TredsPlatform.M1XCHANGE, status: 'pending' },
    { id: 'HP-004', name: 'Receive and display bids', category: 'happy_path', platform: TredsPlatform.M1XCHANGE, status: 'pending' },
    { id: 'HP-005', name: 'Accept bid and confirm', category: 'happy_path', platform: TredsPlatform.M1XCHANGE, status: 'pending' },
    { id: 'HP-006', name: 'Track disbursement status', category: 'happy_path', platform: TredsPlatform.M1XCHANGE, status: 'pending' },
    { id: 'HP-007', name: 'Receive disbursement webhook', category: 'happy_path', platform: TredsPlatform.M1XCHANGE, status: 'pending' },

    // Error Scenarios
    { id: 'ER-001', name: 'Handle duplicate invoice upload', category: 'error', platform: TredsPlatform.M1XCHANGE, status: 'pending' },
    { id: 'ER-002', name: 'Handle invalid GSTIN', category: 'error', platform: TredsPlatform.M1XCHANGE, status: 'pending' },
    { id: 'ER-003', name: 'Handle buyer not registered', category: 'error', platform: TredsPlatform.M1XCHANGE, status: 'pending' },
    { id: 'ER-004', name: 'Handle auction with no bids', category: 'error', platform: TredsPlatform.M1XCHANGE, status: 'pending' },
    { id: 'ER-005', name: 'Handle API timeout', category: 'error', platform: TredsPlatform.M1XCHANGE, status: 'pending' },
    { id: 'ER-006', name: 'Handle authentication expiry', category: 'error', platform: TredsPlatform.M1XCHANGE, status: 'pending' },

    // Edge Cases
    { id: 'EC-001', name: 'Process invoice with special characters', category: 'edge_case', platform: TredsPlatform.M1XCHANGE, status: 'pending' },
    { id: 'EC-002', name: 'Process high-value invoice (>1 Cr)', category: 'edge_case', platform: TredsPlatform.M1XCHANGE, status: 'pending' },
    { id: 'EC-003', name: 'Handle concurrent bid acceptance', category: 'edge_case', platform: TredsPlatform.M1XCHANGE, status: 'pending' },
    { id: 'EC-004', name: 'Process invoice near due date', category: 'edge_case', platform: TredsPlatform.M1XCHANGE, status: 'pending' },

    // Performance
    { id: 'PF-001', name: 'Upload 100 invoices in 1 hour', category: 'performance', platform: TredsPlatform.M1XCHANGE, status: 'pending' },
    { id: 'PF-002', name: 'Handle 50 concurrent bid fetches', category: 'performance', platform: TredsPlatform.M1XCHANGE, status: 'pending' },
    { id: 'PF-003', name: 'Process webhook burst (100 in 1 min)', category: 'performance', platform: TredsPlatform.M1XCHANGE, status: 'pending' }
  ];
  ```

  **Production Pilot Criteria:**
  - Minimum 5 successful end-to-end transactions in sandbox
  - Zero critical bugs in UAT
  - Performance within 120% of target SLAs
  - Security assessment passed
  - Platform certification received
  - Operations team trained
  - Monitoring and alerting configured

  **Rollout Schedule:**
  | Week | Activity | Success Metric |
  |------|----------|----------------|
  | Week 1-2 | Internal pilot (company invoices) | 5 successful transactions |
  | Week 3-4 | Beta users (3-5 suppliers) | 20 successful transactions |
  | Week 5-6 | Soft launch (25% traffic) | < 2% error rate |
  | Week 7-8 | Scaled launch (50% traffic) | < 1% error rate |
  | Week 9+ | Full launch (100% traffic) | Sustained performance |

---

## References
- [M1xchange API Documentation](https://www.m1xchange.com/developers)
- [RXIL TReDS Platform](https://www.rxil.in/)
- [RBI TReDS Guidelines](https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=10718)
- [TReDS Registration Requirements](https://www.m1xchange.com/registration)
