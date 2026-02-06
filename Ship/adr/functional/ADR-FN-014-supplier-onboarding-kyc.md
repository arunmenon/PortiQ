# ADR-FN-014: Supplier Onboarding & KYC

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

The marketplace requires a robust supplier onboarding process with KYC (Know Your Customer) verification to ensure quality, compliance, and trust in the supplier network.

### Business Context
Maritime supply involves regulated products (safety equipment, medicines), financial transactions with credit risk, and quality requirements affecting vessel operations. Unverified suppliers pose risks:
- Counterfeit or substandard products
- Non-compliance with maritime regulations (SOLAS, MED)
- Financial fraud or default
- Reputation damage to platform

A structured onboarding process with verification builds the trusted supplier network essential for marketplace success.

### Technical Context
- Multi-tenant user model (ADR-FN-023)
- Document storage for verification documents (ADR-NF-013)
- Integration with external verification services
- Workflow state management for approval process
- RBAC for internal reviewer roles

### Assumptions
- Suppliers will provide required documentation
- Verification can be partially automated
- Some manual review is acceptable for initial launch
- Indian business verification services available (GST, MCA)

---

## Decision Drivers

- Risk mitigation for platform and buyers
- Compliance with maritime regulations
- Efficient onboarding without excessive friction
- Scalable verification process
- Clear approval workflow
- Support for different supplier tiers

---

## Considered Options

### Option 1: Self-Service with Post-Hoc Verification
**Description:** Allow immediate supplier access with background verification, suspend if issues found.

**Pros:**
- Fast supplier onboarding
- Lower friction
- Quick marketplace growth

**Cons:**
- Risk of fraud before detection
- Potential buyer harm
- Reactive rather than preventive

### Option 2: Full Manual Review
**Description:** Require complete documentation upfront with manual verification of all suppliers.

**Pros:**
- Highest assurance level
- Complete control
- Personal relationship building

**Cons:**
- Slow onboarding (days/weeks)
- Not scalable
- High operational cost

### Option 3: Tiered Verification with Automated Checks
**Description:** Progressive verification with automated checks for basics, manual review for elevated tiers.

**Pros:**
- Balanced risk/friction trade-off
- Scalable automated checks
- Progressive trust building
- Efficient reviewer time use

**Cons:**
- More complex implementation
- Tier management overhead

---

## Decision

**Chosen Option:** Tiered Verification with Automated Checks

We will implement a tiered supplier verification system with automated checks for basic verification and manual review for elevated trust tiers, enabling progressive access to platform features.

### Rationale
The tiered approach balances marketplace growth velocity with risk management. Automated verification of government databases (GST, MCA) handles basic checks efficiently, while manual review focuses on high-value verification tasks. Suppliers can start with limited access and unlock features as trust is established.

---

## Consequences

### Positive
- Scalable verification process
- Progressive trust building
- Efficient use of review resources
- Clear supplier progression path
- Risk-appropriate access controls

### Negative
- Initial feature limitations may frustrate suppliers
- **Mitigation:** Clear communication of tier benefits and upgrade path
- Automated checks have limitations
- **Mitigation:** Manual review capability for edge cases

### Risks
- Verification service downtime: Queue for retry, manual fallback
- Gaming of verification: Periodic re-verification, performance monitoring
- False positives/negatives: Appeal process, human review option

---

## Implementation Notes

### Supplier Tier Model

```typescript
// supplier/enums/supplier-tier.enum.ts
export enum SupplierTier {
  PENDING = 'PENDING',       // Initial registration
  BASIC = 'BASIC',           // Automated verification passed
  VERIFIED = 'VERIFIED',     // Manual document review passed
  PREFERRED = 'PREFERRED',   // Track record + enhanced review
  PREMIUM = 'PREMIUM'        // Strategic partnership level
}

export interface TierCapabilities {
  maxActiveQuotes: number;
  canBidOnRfqs: boolean;
  canAccessFinancing: boolean;
  visibilityLevel: 'LIMITED' | 'STANDARD' | 'ENHANCED';
  commissionRate: number;
  paymentTerms: number;
  supportLevel: 'SELF_SERVICE' | 'STANDARD' | 'PRIORITY';
}

export const TIER_CAPABILITIES: Record<SupplierTier, TierCapabilities> = {
  [SupplierTier.PENDING]: {
    maxActiveQuotes: 0,
    canBidOnRfqs: false,
    canAccessFinancing: false,
    visibilityLevel: 'LIMITED',
    commissionRate: 0,
    paymentTerms: 0,
    supportLevel: 'SELF_SERVICE'
  },
  [SupplierTier.BASIC]: {
    maxActiveQuotes: 5,
    canBidOnRfqs: true,
    canAccessFinancing: false,
    visibilityLevel: 'LIMITED',
    commissionRate: 5,
    paymentTerms: 15,
    supportLevel: 'SELF_SERVICE'
  },
  [SupplierTier.VERIFIED]: {
    maxActiveQuotes: 20,
    canBidOnRfqs: true,
    canAccessFinancing: true,
    visibilityLevel: 'STANDARD',
    commissionRate: 4,
    paymentTerms: 30,
    supportLevel: 'STANDARD'
  },
  [SupplierTier.PREFERRED]: {
    maxActiveQuotes: 50,
    canBidOnRfqs: true,
    canAccessFinancing: true,
    visibilityLevel: 'ENHANCED',
    commissionRate: 3,
    paymentTerms: 45,
    supportLevel: 'PRIORITY'
  },
  [SupplierTier.PREMIUM]: {
    maxActiveQuotes: -1, // Unlimited
    canBidOnRfqs: true,
    canAccessFinancing: true,
    visibilityLevel: 'ENHANCED',
    commissionRate: 2,
    paymentTerms: 60,
    supportLevel: 'PRIORITY'
  }
};
```

### Onboarding Workflow

```typescript
// supplier/enums/onboarding-status.enum.ts
export enum OnboardingStatus {
  STARTED = 'STARTED',
  DOCUMENTS_PENDING = 'DOCUMENTS_PENDING',
  DOCUMENTS_SUBMITTED = 'DOCUMENTS_SUBMITTED',
  AUTO_VERIFICATION_IN_PROGRESS = 'AUTO_VERIFICATION_IN_PROGRESS',
  AUTO_VERIFICATION_PASSED = 'AUTO_VERIFICATION_PASSED',
  AUTO_VERIFICATION_FAILED = 'AUTO_VERIFICATION_FAILED',
  MANUAL_REVIEW_PENDING = 'MANUAL_REVIEW_PENDING',
  MANUAL_REVIEW_IN_PROGRESS = 'MANUAL_REVIEW_IN_PROGRESS',
  APPROVED = 'APPROVED',
  REJECTED = 'REJECTED',
  SUSPENDED = 'SUSPENDED'
}

// Required documents by tier
export const TIER_REQUIREMENTS: Record<SupplierTier, DocumentRequirement[]> = {
  [SupplierTier.BASIC]: [
    { type: 'GST_CERTIFICATE', required: true },
    { type: 'PAN_CARD', required: true },
    { type: 'BUSINESS_ADDRESS_PROOF', required: true }
  ],
  [SupplierTier.VERIFIED]: [
    { type: 'INCORPORATION_CERTIFICATE', required: true },
    { type: 'BANK_STATEMENT', required: true, months: 6 },
    { type: 'REFERENCE_LETTERS', required: true, count: 2 },
    { type: 'PRODUCT_CERTIFICATIONS', required: false }
  ],
  [SupplierTier.PREFERRED]: [
    { type: 'AUDITED_FINANCIALS', required: true, years: 2 },
    { type: 'INSURANCE_CERTIFICATE', required: true },
    { type: 'QUALITY_CERTIFICATIONS', required: true }
  ],
  // ... additional tiers
};
```

### Onboarding Service

```typescript
// supplier/services/supplier-onboarding.service.ts
@Injectable()
export class SupplierOnboardingService {
  constructor(
    private readonly supplierRepository: SupplierRepository,
    private readonly documentService: DocumentService,
    private readonly verificationService: VerificationService,
    private readonly eventEmitter: EventEmitter2
  ) {}

  async startOnboarding(registration: SupplierRegistration): Promise<Supplier> {
    // Create supplier record
    const supplier = await this.supplierRepository.create({
      ...registration,
      tier: SupplierTier.PENDING,
      onboardingStatus: OnboardingStatus.STARTED,
      createdAt: new Date()
    });

    // Emit event for tracking
    this.eventEmitter.emit('supplier.onboarding.started', { supplier });

    return supplier;
  }

  async submitDocuments(
    supplierId: string,
    documents: UploadedDocument[]
  ): Promise<void> {
    // Store documents
    for (const doc of documents) {
      await this.documentService.store({
        supplierId,
        type: doc.type,
        fileKey: doc.fileKey,
        uploadedAt: new Date()
      });
    }

    // Update status
    await this.supplierRepository.update(supplierId, {
      onboardingStatus: OnboardingStatus.DOCUMENTS_SUBMITTED
    });

    // Trigger automated verification
    await this.triggerAutoVerification(supplierId);
  }

  async triggerAutoVerification(supplierId: string): Promise<void> {
    await this.supplierRepository.update(supplierId, {
      onboardingStatus: OnboardingStatus.AUTO_VERIFICATION_IN_PROGRESS
    });

    const supplier = await this.supplierRepository.findById(supplierId);
    const results: VerificationResult[] = [];

    // GST Verification
    if (supplier.gstNumber) {
      const gstResult = await this.verificationService.verifyGst(supplier.gstNumber);
      results.push(gstResult);
    }

    // PAN Verification
    if (supplier.panNumber) {
      const panResult = await this.verificationService.verifyPan(supplier.panNumber);
      results.push(panResult);
    }

    // MCA (Company Registration) Verification
    if (supplier.cinNumber) {
      const mcaResult = await this.verificationService.verifyMca(supplier.cinNumber);
      results.push(mcaResult);
    }

    // Bank Account Verification
    if (supplier.bankAccount) {
      const bankResult = await this.verificationService.verifyBankAccount(
        supplier.bankAccount
      );
      results.push(bankResult);
    }

    // Evaluate results
    const allPassed = results.every(r => r.status === 'PASSED');
    const anyFailed = results.some(r => r.status === 'FAILED');

    await this.supplierRepository.update(supplierId, {
      verificationResults: results,
      onboardingStatus: anyFailed
        ? OnboardingStatus.AUTO_VERIFICATION_FAILED
        : OnboardingStatus.AUTO_VERIFICATION_PASSED,
      ...(allPassed && { tier: SupplierTier.BASIC })
    });

    if (allPassed) {
      this.eventEmitter.emit('supplier.verified.basic', { supplierId });
    } else if (anyFailed) {
      this.eventEmitter.emit('supplier.verification.failed', {
        supplierId,
        results: results.filter(r => r.status === 'FAILED')
      });
    }
  }

  async requestTierUpgrade(
    supplierId: string,
    targetTier: SupplierTier
  ): Promise<TierUpgradeRequest> {
    const supplier = await this.supplierRepository.findById(supplierId);

    // Check eligibility
    const eligibility = await this.checkUpgradeEligibility(supplier, targetTier);
    if (!eligibility.eligible) {
      throw new BadRequestException(eligibility.reason);
    }

    // Create upgrade request
    const request = await this.upgradeRequestRepository.create({
      supplierId,
      currentTier: supplier.tier,
      targetTier,
      status: 'PENDING',
      requiredDocuments: TIER_REQUIREMENTS[targetTier],
      createdAt: new Date()
    });

    return request;
  }

  async reviewSupplier(
    supplierId: string,
    reviewerId: string,
    decision: ReviewDecision
  ): Promise<void> {
    const supplier = await this.supplierRepository.findById(supplierId);

    await this.supplierRepository.transaction(async (tx) => {
      // Update supplier status
      await tx.supplier.update({
        where: { id: supplierId },
        data: {
          onboardingStatus: decision.approved
            ? OnboardingStatus.APPROVED
            : OnboardingStatus.REJECTED,
          tier: decision.approved
            ? decision.approvedTier
            : supplier.tier,
          reviewedAt: new Date(),
          reviewedBy: reviewerId
        }
      });

      // Record review decision
      await tx.reviewLog.create({
        data: {
          supplierId,
          reviewerId,
          decision: decision.approved ? 'APPROVED' : 'REJECTED',
          tier: decision.approvedTier,
          notes: decision.notes,
          timestamp: new Date()
        }
      });
    });

    // Notify supplier
    this.eventEmitter.emit(
      decision.approved ? 'supplier.approved' : 'supplier.rejected',
      { supplierId, decision }
    );
  }
}
```

### Verification Service Integration

```typescript
// supplier/services/verification.service.ts
@Injectable()
export class VerificationService {
  constructor(
    private readonly httpService: HttpService,
    private readonly configService: ConfigService
  ) {}

  async verifyGst(gstNumber: string): Promise<VerificationResult> {
    try {
      const response = await this.httpService.post(
        this.configService.get('GST_VERIFY_API_URL'),
        { gstin: gstNumber },
        {
          headers: {
            'Authorization': `Bearer ${this.configService.get('GST_API_KEY')}`
          }
        }
      ).toPromise();

      const data = response.data;

      return {
        type: 'GST',
        status: data.valid ? 'PASSED' : 'FAILED',
        verifiedData: {
          businessName: data.tradeName,
          registrationDate: data.registrationDate,
          status: data.status,
          businessType: data.constitutionOfBusiness
        },
        verifiedAt: new Date()
      };
    } catch (error) {
      return {
        type: 'GST',
        status: 'ERROR',
        error: error.message,
        verifiedAt: new Date()
      };
    }
  }

  async verifyPan(panNumber: string): Promise<VerificationResult> {
    // Similar implementation for PAN verification
    // Using NSDL or authorized verification service
  }

  async verifyMca(cinNumber: string): Promise<VerificationResult> {
    // Ministry of Corporate Affairs verification
    // For company incorporation details
  }

  async verifyBankAccount(account: BankAccount): Promise<VerificationResult> {
    // Bank account verification via penny drop or NPCI
  }
}
```

### Database Schema

```sql
-- Suppliers table
CREATE TABLE suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    business_name VARCHAR(255) NOT NULL,
    legal_name VARCHAR(255),
    gst_number VARCHAR(15),
    pan_number VARCHAR(10),
    cin_number VARCHAR(21),

    -- Tier and status
    tier VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    onboarding_status VARCHAR(50) NOT NULL DEFAULT 'STARTED',

    -- Verification data
    verification_results JSONB DEFAULT '[]',
    verified_at TIMESTAMPTZ,
    verified_by UUID REFERENCES users(id),

    -- Contact
    primary_contact_name VARCHAR(100),
    primary_contact_email VARCHAR(255),
    primary_contact_phone VARCHAR(20),

    -- Address
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(10),
    country VARCHAR(2) DEFAULT 'IN',

    -- Banking
    bank_account_number VARCHAR(20),
    bank_ifsc VARCHAR(11),
    bank_name VARCHAR(100),

    -- Metadata
    categories TEXT[],  -- Product categories they supply
    port_coverage TEXT[],  -- Ports they can serve

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Supplier documents
CREATE TABLE supplier_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id UUID REFERENCES suppliers(id),
    type VARCHAR(50) NOT NULL,
    file_key VARCHAR(500) NOT NULL,
    file_name VARCHAR(255),
    status VARCHAR(20) DEFAULT 'PENDING',
    verified_at TIMESTAMPTZ,
    verified_by UUID REFERENCES users(id),
    expiry_date DATE,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Review log
CREATE TABLE supplier_review_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id UUID REFERENCES suppliers(id),
    reviewer_id UUID REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    from_tier VARCHAR(20),
    to_tier VARCHAR(20),
    notes TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);
```

### Dependencies
- ADR-FN-023: Multi-Tenant User Model
- ADR-NF-013: Object Storage (S3)
- ADR-NF-015: Authentication Strategy

### Migration Strategy
1. Create supplier and document tables
2. Implement basic registration flow
3. Integrate GST verification API
4. Add manual review workflow
5. Build reviewer dashboard
6. Implement tier upgrade process
7. Add periodic re-verification

---

## Operational Considerations

### KYC Tiers by Risk Level

#### Tier Definitions and Risk Scoring

| Tier | Risk Level | Annual Transaction Limit | Product Categories | Verification Level |
|------|------------|--------------------------|-------------------|-------------------|
| PENDING | Unverified | $0 | None | Registration only |
| BASIC | Low | $50,000 | General provisions, cleaning supplies | Automated only |
| VERIFIED | Medium | $500,000 | Technical equipment, safety gear | Automated + document review |
| PREFERRED | Low-Medium | $2,000,000 | All categories including regulated | Full verification + site visit |
| PREMIUM | Lowest | Unlimited | All categories + priority access | Enhanced due diligence |

#### Risk Scoring Model

```typescript
// Risk score calculation (0-100, lower is better)
interface SupplierRiskScore {
  supplierId: string;
  calculatedAt: Date;
  overallScore: number;
  components: {
    businessAge: { score: number; weight: 15 };
    financialHealth: { score: number; weight: 20 };
    regulatoryCompliance: { score: number; weight: 25 };
    transactionHistory: { score: number; weight: 20 };
    externalRatings: { score: number; weight: 10 };
    geographicRisk: { score: number; weight: 10 };
  };
  flags: RiskFlag[];
}

interface RiskFlag {
  type: 'adverse_media' | 'sanctions_proximity' | 'ownership_opacity' | 'regulatory_action';
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  source: string;
  detectedAt: Date;
}

// Risk thresholds for tier eligibility
const TIER_RISK_THRESHOLDS = {
  BASIC: { maxScore: 70, requiredVerifications: ['gst', 'pan'] },
  VERIFIED: { maxScore: 50, requiredVerifications: ['gst', 'pan', 'bank', 'documents'] },
  PREFERRED: { maxScore: 30, requiredVerifications: ['gst', 'pan', 'bank', 'documents', 'site_visit', 'financials'] },
  PREMIUM: { maxScore: 20, requiredVerifications: ['all', 'enhanced_due_diligence'] }
};
```

### Re-verification Cadence

| Tier | Standard Re-verification | Document Refresh | Trigger-Based Review |
|------|-------------------------|------------------|---------------------|
| BASIC | 12 months | On expiry | Transaction anomaly, complaint |
| VERIFIED | 12 months | 6 months or expiry | Risk score increase >15 points |
| PREFERRED | 6 months | 6 months or expiry | Any adverse media hit |
| PREMIUM | 6 months | 3 months or expiry | Any flag, relationship change |

#### Re-verification Triggers

| Trigger | Action | Timeline |
|---------|--------|----------|
| Document expiry (30 days) | Email reminder, dashboard alert | Immediate |
| Document expiry (7 days) | Restrict new quotes, urgent notification | Immediate |
| Document expired | Downgrade to PENDING, block transactions | Immediate |
| Risk score increase >10 | Queue for review | Within 48 hours |
| Risk score increase >20 | Immediate review, potential suspension | Within 24 hours |
| Adverse media detection | Immediate review | Within 4 hours |
| Sanctions list match | Immediate suspension pending review | Immediate |
| Customer complaint (quality) | Flag for next review | At next cycle |
| Customer complaint (fraud) | Immediate investigation | Within 4 hours |

### Data Retention Policies

| Data Category | Active Retention | Archive Retention | Deletion |
|---------------|------------------|-------------------|----------|
| KYC Documents (ID, registration) | Supplier lifetime + 5 years | +5 years cold storage | Hard delete |
| Financial Documents | 7 years from upload | +3 years cold storage | Hard delete |
| Verification Results | 7 years | +3 years | Hard delete |
| Risk Assessments | 7 years | +3 years | Hard delete |
| Communication Records | 3 years | +2 years | Hard delete |
| Site Visit Reports | Supplier lifetime + 7 years | +3 years | Hard delete |
| Rejected Applications | 5 years | +2 years | Hard delete |

#### Document Storage Specifications

```typescript
interface KycDocumentStorage {
  document_id: string;
  supplier_id: string;
  document_type: KycDocumentType;
  storage: {
    bucket: 'kyc-documents-active' | 'kyc-documents-archive';
    key: string;
    encryption: 'AES-256-GCM';
    kms_key_id: string;
  };
  metadata: {
    original_filename: string;
    upload_date: Date;
    expiry_date?: Date;
    verified_date?: Date;
    verified_by?: string;
    hash_sha256: string;
  };
  retention: {
    active_until: Date;
    archive_until: Date;
    deletion_scheduled: Date;
    legal_hold: boolean;
  };
}

type KycDocumentType =
  | 'gst_certificate'
  | 'pan_card'
  | 'incorporation_certificate'
  | 'bank_statement'
  | 'audited_financials'
  | 'insurance_certificate'
  | 'quality_certification'
  | 'reference_letter'
  | 'address_proof'
  | 'director_id';
```

### KYC Provider Integration

#### Primary KYC Provider: Signzy

| Verification Type | API Endpoint | SLA | Fallback |
|-------------------|--------------|-----|----------|
| GST Verification | `/gst/verify` | 5 seconds | Manual + Karza |
| PAN Verification | `/pan/verify` | 3 seconds | Manual + NSDL |
| Bank Account | `/bank/penny-drop` | 30 seconds | Manual + NPCI |
| Company (MCA) | `/mca/company` | 10 seconds | Manual + MCA portal |
| Director KYC | `/director/verify` | 15 seconds | Manual |
| Address (Aadhaar) | `/aadhaar/okyc` | 10 seconds | Manual verification |

#### Fallback Provider: Karza

| Verification Type | API Endpoint | When Used |
|-------------------|--------------|-----------|
| GST Verification | `/v3/gst` | Signzy timeout/failure |
| PAN Verification | `/v3/pan` | Signzy timeout/failure |
| Company Details | `/v3/mca` | Signzy timeout/failure |

#### Coverage Gaps and Manual Processes

| Gap Scenario | Manual Process | SLA |
|--------------|----------------|-----|
| Foreign supplier (non-Indian) | Manual document review + trade reference check | 5 business days |
| Sole proprietorship without GST | Alternative ID verification + bank statement analysis | 3 business days |
| New business (<1 year) | Enhanced reference checks + smaller initial limits | 3 business days |
| API service outage | Queue for retry (4 hours) then manual processing | 24 hours |
| Inconclusive automated result | Manual review with original documents | 2 business days |
| High-risk flag detected | Enhanced due diligence team review | 3-5 business days |

```typescript
// Coverage gap handling
interface KycCoverageGap {
  supplierId: string;
  gapType: 'foreign_entity' | 'no_gst' | 'new_business' | 'api_failure' | 'inconclusive' | 'high_risk';
  detectedAt: Date;
  manualProcessRequired: ManualProcess[];
  assignedTo?: string;
  dueDate: Date;
  status: 'pending' | 'in_progress' | 'completed' | 'escalated';
}

interface ManualProcess {
  type: 'document_review' | 'reference_check' | 'site_visit' | 'video_kyc' | 'enhanced_due_diligence';
  description: string;
  requiredEvidence: string[];
  completedAt?: Date;
  completedBy?: string;
  outcome?: 'passed' | 'failed' | 'needs_info';
  notes?: string;
}
```

### Verification SLA Matrix

| Verification Type | Automated SLA | Manual Review SLA | Escalation Threshold |
|-------------------|---------------|-------------------|---------------------|
| GST/PAN (Basic tier) | 5 minutes | 4 hours | 8 hours |
| Bank Account | 1 hour | 8 hours | 24 hours |
| Document Review | N/A | 24 hours | 48 hours |
| Full Verification (Verified tier) | 4 hours | 2 business days | 3 business days |
| Enhanced DD (Preferred/Premium) | N/A | 5 business days | 7 business days |
| Re-verification | 1 hour | 24 hours | 48 hours |

#### SLA Monitoring and Alerts

```typescript
// SLA tracking
interface VerificationSlaTracker {
  verificationId: string;
  supplierId: string;
  verificationType: string;
  startedAt: Date;
  slaDeadline: Date;
  currentStatus: 'pending' | 'in_progress' | 'completed' | 'breached';
  alerts: SlaAlert[];
}

interface SlaAlert {
  threshold: '50%' | '75%' | '90%' | 'breached';
  triggeredAt: Date;
  notifiedTo: string[];
  acknowledged: boolean;
}

// Alert thresholds
const SLA_ALERT_CONFIG = {
  '50%': { notify: ['assigned_reviewer'] },
  '75%': { notify: ['assigned_reviewer', 'team_lead'] },
  '90%': { notify: ['assigned_reviewer', 'team_lead', 'ops_manager'] },
  'breached': { notify: ['all_above', 'vp_operations'], escalate: true }
};
```

### Manual Review Process

#### Review Team Structure

| Role | Responsibilities | Capacity |
|------|------------------|----------|
| KYC Analyst | Basic document review, data entry verification | 30 reviews/day |
| Senior KYC Analyst | Complex cases, foreign entities, discrepancy resolution | 15 reviews/day |
| KYC Manager | Escalations, policy exceptions, tier upgrades to Preferred | 5 reviews/day |
| Compliance Officer | Premium tier approvals, high-risk flags, regulatory queries | As needed |

#### Review Workflow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Auto-Verify     │────▶│ Queue for       │────▶│ Assign to       │
│ (if possible)   │     │ Manual Review   │     │ Analyst         │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                        ┌────────────────────────────────┘
                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Document        │────▶│ Cross-Reference │────▶│ Risk            │
│ Authenticity    │     │ Verification    │     │ Assessment      │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
         ┌───────────────────┬───────────────────────────┘
         ▼                   ▼                           ▼
┌─────────────────┐  ┌─────────────────┐      ┌─────────────────┐
│ Approve         │  │ Request More    │      │ Reject /        │
│ (Update Tier)   │  │ Information     │      │ Escalate        │
└─────────────────┘  └─────────────────┘      └─────────────────┘
```

#### Review Checklist by Tier

**BASIC Tier Manual Review:**
- [ ] GST certificate matches business name
- [ ] PAN linked to GST
- [ ] Address proof matches registered address
- [ ] No adverse media in basic search

**VERIFIED Tier Manual Review:**
- [ ] All BASIC checks
- [ ] Incorporation certificate valid and current
- [ ] Bank statement shows 6 months of business activity
- [ ] At least 2 reference letters verified
- [ ] Product certifications valid (if applicable)
- [ ] Director/owner identity verified

**PREFERRED Tier Manual Review:**
- [ ] All VERIFIED checks
- [ ] 2 years audited financials reviewed
- [ ] Insurance coverage adequate
- [ ] Quality certifications current
- [ ] Site visit completed and documented
- [ ] No material litigation or regulatory actions

### Open Questions - Resolved

- **Q:** What is the manual review process and expected turnaround time?
  - **A:** Manual review follows a structured workflow with defined SLAs based on verification type:
    - **Basic tier reviews**: 4-hour SLA for simple document verification (GST/PAN discrepancies, address confirmation)
    - **Verified tier reviews**: 2 business day SLA including document authenticity, cross-reference verification, and basic risk assessment
    - **Preferred/Premium tier reviews**: 5 business day SLA including enhanced due diligence, financial analysis, and site visit coordination

    The review team consists of KYC Analysts (30 reviews/day capacity) for routine cases, Senior Analysts for complex cases, and escalation paths to KYC Manager and Compliance Officer. All reviews follow standardized checklists with mandatory fields. SLA monitoring triggers alerts at 50%, 75%, and 90% of deadline, with automatic escalation on breach. Expected queue times are factored into turnaround: 1 hour for Basic, 4 hours for Verified, and 1 business day for Preferred/Premium during normal operations.

---

## References
- [GST Verification API](https://www.gst.gov.in/help/api)
- [KYC Best Practices for B2B Platforms](https://www.seon.io/resources/kyc-for-b2b/)
- [NSDL PAN Verification](https://www.tin-nsdl.com/services/pan/pan-verification.html)
