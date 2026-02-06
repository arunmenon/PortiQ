# ADR-FN-012: Auction Types

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

The marketplace must support multiple auction mechanisms to accommodate different procurement scenarios, from commodity purchases to complex multi-criteria sourcing.

### Business Context
Maritime procurement scenarios vary significantly:
- **Commodity purchases** (cleaning supplies, provisions): Price is primary criterion
- **Technical equipment** (engine parts, safety gear): Quality and certification matter
- **Strategic sourcing** (long-term supply agreements): Relationship and total value important
- **Urgent requirements** (emergency repairs): Speed and availability critical

Different auction types optimize for these varying priorities while maintaining fairness and competitive dynamics.

### Technical Context
- RFQ state machine manages overall workflow (ADR-FN-011)
- Real-time updates via WebSocket (ADR-UI-012)
- Quote comparison engine for evaluation (ADR-FN-013)
- Need to prevent bid manipulation and ensure fairness
- Concurrency handling for simultaneous bids

### Assumptions
- Suppliers are comfortable with different bidding formats
- Buyers can configure appropriate auction type per RFQ
- Real-time bidding requires robust infrastructure
- Fairness and transparency are paramount

---

## Decision Drivers

- Support for diverse procurement scenarios
- Fair and transparent bidding process
- Prevention of bid manipulation
- Real-time interaction capability
- Flexibility in evaluation criteria
- Compliance with procurement best practices

---

## Considered Options

### Option 1: Sealed-Bid Only
**Description:** Single confidential bid submission with evaluation after deadline.

**Pros:**
- Simple implementation
- No real-time requirements
- Prevents bidding wars
- Clear timeline

**Cons:**
- No price discovery
- Suppliers may bid conservatively
- No competitive dynamics during bidding

### Option 2: Reverse Auction Only
**Description:** Open bidding where suppliers see competing bids and can improve.

**Pros:**
- Drives competitive pricing
- Price discovery
- Dynamic bidding

**Cons:**
- Complex real-time infrastructure
- May commoditize relationships
- Race-to-bottom concerns

### Option 3: Multiple Auction Types
**Description:** Support sealed-bid, reverse auction, and multi-attribute auctions based on RFQ configuration.

**Pros:**
- Flexibility for different scenarios
- Optimal mechanism per procurement type
- Comprehensive marketplace capability
- Competitive advantage

**Cons:**
- Higher implementation complexity
- User education required
- More testing scenarios

---

## Decision

**Chosen Option:** Multiple Auction Types

We will implement three auction types: sealed-bid, reverse (British) auction, and multi-attribute auction, selectable per RFQ based on procurement requirements.

### Rationale
Different procurement scenarios demand different auction mechanisms. Sealed-bid works for strategic sourcing where relationships matter; reverse auctions drive competitive pricing for commodities; multi-attribute auctions enable sophisticated evaluation of total value. Supporting all three positions the platform as a comprehensive solution for maritime procurement.

---

## Consequences

### Positive
- Optimal auction type per procurement scenario
- Competitive platform capability
- Flexibility for buyers
- Comprehensive procurement solution

### Negative
- Higher implementation complexity
- **Mitigation:** Implement sequentially: sealed-bid → reverse → multi-attribute
- User education required
- **Mitigation:** In-app guidance, documentation, defaults

### Risks
- Bid manipulation in reverse auctions: Implement anti-sniping, bid validation
- Complex multi-attribute configuration: Provide templates, validation
- Real-time failures: Fallback to sealed-bid, extension mechanisms

---

## Implementation Notes

### Auction Type Definitions

```typescript
// auction/enums/auction-type.enum.ts
export enum AuctionType {
  SEALED_BID = 'SEALED_BID',
  REVERSE_AUCTION = 'REVERSE_AUCTION',
  MULTI_ATTRIBUTE = 'MULTI_ATTRIBUTE'
}

export interface AuctionConfig {
  type: AuctionType;
  settings: SealedBidSettings | ReverseAuctionSettings | MultiAttributeSettings;
}

// Sealed Bid Configuration
export interface SealedBidSettings {
  allowMultipleSubmissions: boolean;  // Can supplier revise before deadline
  revealBidsToSuppliers: boolean;     // Show results after award
  minimumBidders: number;
}

// Reverse Auction Configuration
export interface ReverseAuctionSettings {
  startingPrice?: number;             // Optional ceiling price
  minimumDecrement: number;           // Minimum bid improvement (amount or %)
  decrementType: 'AMOUNT' | 'PERCENTAGE';
  duration: number;                   // Auction duration in minutes
  extensionTrigger: number;           // Minutes before end to trigger extension
  extensionDuration: number;          // Extension length in minutes
  maxExtensions: number;              // Maximum number of extensions
  showRanking: boolean;               // Show supplier's rank
  showLeadingBid: boolean;           // Show current best price
  showBidCount: boolean;             // Show number of bids
}

// Multi-Attribute Configuration
export interface MultiAttributeSettings {
  criteria: EvaluationCriterion[];
  scoringMethod: 'WEIGHTED_SUM' | 'TOPSIS' | 'AHP';
  priceWeight: number;               // Price weight in overall score (0-100)
  allowPartialBids: boolean;         // Bid on subset of line items
}

export interface EvaluationCriterion {
  id: string;
  name: string;
  weight: number;                    // 0-100
  type: 'NUMERIC' | 'RATING' | 'BOOLEAN';
  higherIsBetter: boolean;
  minValue?: number;
  maxValue?: number;
}
```

### Sealed-Bid Implementation

```typescript
// auction/services/sealed-bid.service.ts
@Injectable()
export class SealedBidService implements AuctionService {
  constructor(
    private readonly quoteRepository: QuoteRepository,
    private readonly rfqRepository: RfqRepository
  ) {}

  async submitBid(rfqId: string, bid: BidSubmission): Promise<Quote> {
    const rfq = await this.rfqRepository.findById(rfqId);

    this.validateBiddingOpen(rfq);
    this.validateDeadline(rfq);

    const settings = rfq.auctionConfig.settings as SealedBidSettings;

    // Check if revision allowed
    const existingQuote = await this.quoteRepository.findByRfqAndSupplier(
      rfqId,
      bid.supplierId
    );

    if (existingQuote && !settings.allowMultipleSubmissions) {
      throw new BadRequestException('Quote revision not allowed for this RFQ');
    }

    // Create or update quote
    const quote = await this.quoteRepository.upsert({
      rfqId,
      supplierId: bid.supplierId,
      lineItems: bid.lineItems,
      totalAmount: this.calculateTotal(bid.lineItems),
      validUntil: bid.validUntil,
      terms: bid.terms,
      submittedAt: new Date(),
      version: (existingQuote?.version ?? 0) + 1
    });

    return quote;
  }

  async evaluateBids(rfqId: string): Promise<EvaluationResult> {
    const quotes = await this.quoteRepository.findByRfq(rfqId);

    // Rank by total price
    const ranked = quotes
      .filter(q => q.status === 'SUBMITTED')
      .sort((a, b) => a.totalAmount - b.totalAmount)
      .map((quote, index) => ({
        quote,
        rank: index + 1,
        priceScore: this.calculatePriceScore(quote, quotes)
      }));

    return {
      rfqId,
      rankings: ranked,
      recommendedAward: ranked[0]?.quote.id
    };
  }
}
```

### Reverse Auction Implementation

```typescript
// auction/services/reverse-auction.service.ts
@Injectable()
export class ReverseAuctionService implements AuctionService {
  constructor(
    private readonly bidRepository: BidRepository,
    private readonly rfqRepository: RfqRepository,
    private readonly websocketGateway: BiddingGateway,
    private readonly redis: Redis
  ) {}

  async submitBid(rfqId: string, bid: BidSubmission): Promise<AuctionBid> {
    const rfq = await this.rfqRepository.findById(rfqId);
    const settings = rfq.auctionConfig.settings as ReverseAuctionSettings;

    // Validate auction is active
    this.validateAuctionActive(rfq);

    // Validate bid improvement
    const currentBest = await this.getCurrentBestBid(rfqId);
    this.validateBidImprovement(bid.amount, currentBest, settings);

    // Use optimistic locking to prevent race conditions
    const auctionBid = await this.redis.transaction(async (tx) => {
      // Double-check current best within transaction
      const latestBest = await tx.get(`rfq:${rfqId}:best_bid`);

      if (latestBest && bid.amount >= parseFloat(latestBest)) {
        throw new BadRequestException('Bid must improve on current best');
      }

      // Record bid
      const newBid = await this.bidRepository.create({
        rfqId,
        supplierId: bid.supplierId,
        amount: bid.amount,
        timestamp: new Date(),
        previousBestBid: latestBest ? parseFloat(latestBest) : null
      });

      // Update best bid
      await tx.set(`rfq:${rfqId}:best_bid`, bid.amount.toString());

      return newBid;
    });

    // Check for extension trigger
    await this.checkExtension(rfq, settings);

    // Broadcast update to all participants
    await this.broadcastBidUpdate(rfqId, auctionBid, settings);

    return auctionBid;
  }

  private async checkExtension(
    rfq: Rfq,
    settings: ReverseAuctionSettings
  ): Promise<void> {
    const now = new Date();
    const deadline = new Date(rfq.biddingDeadline);
    const minutesRemaining = (deadline.getTime() - now.getTime()) / 60000;

    if (minutesRemaining <= settings.extensionTrigger) {
      const extensions = await this.getExtensionCount(rfq.id);

      if (extensions < settings.maxExtensions) {
        const newDeadline = new Date(
          deadline.getTime() + settings.extensionDuration * 60000
        );

        await this.rfqRepository.update(rfq.id, {
          biddingDeadline: newDeadline
        });

        await this.websocketGateway.broadcastExtension(rfq.id, newDeadline);
      }
    }
  }

  private async broadcastBidUpdate(
    rfqId: string,
    bid: AuctionBid,
    settings: ReverseAuctionSettings
  ): Promise<void> {
    const update: BidUpdateMessage = {
      rfqId,
      timestamp: bid.timestamp,
      ...(settings.showLeadingBid && { leadingBid: bid.amount }),
      ...(settings.showBidCount && {
        bidCount: await this.getBidCount(rfqId)
      })
    };

    // Broadcast to all connected suppliers
    await this.websocketGateway.broadcast(`rfq:${rfqId}`, update);

    // Send rank update to bid submitter
    if (settings.showRanking) {
      const rank = await this.getSupplierRank(rfqId, bid.supplierId);
      await this.websocketGateway.sendToSupplier(
        bid.supplierId,
        { rfqId, yourRank: rank }
      );
    }
  }
}
```

### Multi-Attribute Auction Implementation

```typescript
// auction/services/multi-attribute-auction.service.ts
@Injectable()
export class MultiAttributeAuctionService implements AuctionService {
  async submitBid(rfqId: string, bid: MultiAttributeBid): Promise<Quote> {
    const rfq = await this.rfqRepository.findById(rfqId);
    const settings = rfq.auctionConfig.settings as MultiAttributeSettings;

    // Validate all criteria are addressed
    this.validateCriteriaResponses(bid.criteriaResponses, settings.criteria);

    // Calculate preliminary score
    const score = this.calculateScore(bid, settings);

    const quote = await this.quoteRepository.create({
      rfqId,
      supplierId: bid.supplierId,
      lineItems: bid.lineItems,
      totalAmount: this.calculateTotal(bid.lineItems),
      criteriaResponses: bid.criteriaResponses,
      calculatedScore: score,
      submittedAt: new Date()
    });

    return quote;
  }

  private calculateScore(
    bid: MultiAttributeBid,
    settings: MultiAttributeSettings
  ): number {
    let totalScore = 0;
    let totalWeight = 0;

    for (const criterion of settings.criteria) {
      const response = bid.criteriaResponses[criterion.id];
      const normalizedValue = this.normalizeValue(response, criterion);
      const weightedScore = normalizedValue * criterion.weight;

      totalScore += weightedScore;
      totalWeight += criterion.weight;
    }

    // Add price component
    const priceScore = this.calculatePriceScore(bid.totalAmount);
    totalScore += priceScore * settings.priceWeight;
    totalWeight += settings.priceWeight;

    return totalScore / totalWeight;
  }

  async evaluateBids(rfqId: string): Promise<MultiAttributeEvaluationResult> {
    const quotes = await this.quoteRepository.findByRfq(rfqId);
    const rfq = await this.rfqRepository.findById(rfqId);
    const settings = rfq.auctionConfig.settings as MultiAttributeSettings;

    // Recalculate scores with all bids (for relative scoring)
    const scoredQuotes = quotes.map(quote => ({
      quote,
      score: this.calculateScore(
        { ...quote, totalAmount: quote.totalAmount, criteriaResponses: quote.criteriaResponses },
        settings
      ),
      breakdown: this.getScoreBreakdown(quote, settings)
    }));

    // Rank by score
    scoredQuotes.sort((a, b) => b.score - a.score);

    return {
      rfqId,
      rankings: scoredQuotes.map((sq, index) => ({
        ...sq,
        rank: index + 1
      })),
      recommendedAward: scoredQuotes[0]?.quote.id
    };
  }
}
```

### WebSocket Gateway for Real-Time Bidding

```typescript
// auction/gateways/bidding.gateway.ts
@WebSocketGateway({ namespace: '/bidding' })
export class BiddingGateway implements OnGatewayConnection, OnGatewayDisconnect {
  @WebSocketServer()
  server: Server;

  constructor(
    private readonly authService: AuthService,
    private readonly redis: Redis
  ) {}

  async handleConnection(client: Socket): Promise<void> {
    const token = client.handshake.auth.token;
    const user = await this.authService.validateToken(token);

    if (!user) {
      client.disconnect();
      return;
    }

    client.data.userId = user.id;
    client.data.supplierId = user.supplierId;
  }

  @SubscribeMessage('join_auction')
  async handleJoinAuction(
    client: Socket,
    rfqId: string
  ): Promise<AuctionState> {
    // Verify supplier is invited to this RFQ
    const isInvited = await this.verifyInvitation(rfqId, client.data.supplierId);

    if (!isInvited) {
      throw new WsException('Not authorized for this auction');
    }

    client.join(`rfq:${rfqId}`);

    // Return current auction state
    return this.getAuctionState(rfqId, client.data.supplierId);
  }

  async broadcast(room: string, message: any): Promise<void> {
    this.server.to(room).emit('auction_update', message);
  }

  async sendToSupplier(supplierId: string, message: any): Promise<void> {
    const sockets = await this.server.fetchSockets();
    const supplierSocket = sockets.find(s => s.data.supplierId === supplierId);

    if (supplierSocket) {
      supplierSocket.emit('private_update', message);
    }
  }

  async broadcastExtension(rfqId: string, newDeadline: Date): Promise<void> {
    this.server.to(`rfq:${rfqId}`).emit('deadline_extended', {
      rfqId,
      newDeadline: newDeadline.toISOString()
    });
  }
}
```

### Dependencies
- ADR-FN-011: RFQ Workflow State Machine
- ADR-FN-013: Quote Comparison & TCO Engine
- ADR-NF-005: Caching Strategy (Redis)
- ADR-UI-012: Real-Time Notifications

### Migration Strategy
1. Implement sealed-bid auction (MVP)
2. Add reverse auction with WebSocket support
3. Implement multi-attribute scoring
4. Create auction configuration UI
5. Add analytics and reporting
6. Implement anti-manipulation measures

---

## Operational Considerations

### Auction Type Rollout Strategy

#### Phase 1 (MVP Launch)

| Auction Type | Status | Timeline | Compliance Checks |
|--------------|--------|----------|-------------------|
| Sealed Bid | Ship | Day 0 | Basic bid validation |
| Reverse Auction | Deferred | Phase 2 | Real-time infrastructure validation |
| Multi-Attribute | Deferred | Phase 3 | Scoring model audit |

#### Phase 2 (6 months post-launch)

| Auction Type | Prerequisites | Compliance Checks |
|--------------|---------------|-------------------|
| Reverse Auction | WebSocket infrastructure stable, 99.9% uptime | Anti-sniping tested, bid integrity verified |

#### Phase 3 (12 months post-launch)

| Auction Type | Prerequisites | Compliance Checks |
|--------------|---------------|-------------------|
| Multi-Attribute | TCO engine validated, scoring model audited | Weight transparency, bias testing |

#### Pre-Launch Compliance Checklist

```typescript
// Auction type enablement checklist
interface AuctionTypeCompliance {
  auctionType: AuctionType;
  checks: ComplianceCheck[];
  approvals: Approval[];
  testingRequirements: TestRequirement[];
}

const SEALED_BID_COMPLIANCE: AuctionTypeCompliance = {
  auctionType: AuctionType.SEALED_BID,
  checks: [
    { id: 'bid_encryption', description: 'Bids encrypted at rest and in transit', status: 'required' },
    { id: 'access_control', description: 'Only buyer can view bids before deadline', status: 'required' },
    { id: 'timestamp_integrity', description: 'Bid timestamps are tamper-proof', status: 'required' },
    { id: 'audit_trail', description: 'All bid actions logged immutably', status: 'required' },
    { id: 'deadline_enforcement', description: 'No bids accepted after deadline', status: 'required' }
  ],
  approvals: [
    { role: 'security_team', scope: 'encryption_and_access' },
    { role: 'legal_team', scope: 'terms_and_conditions' },
    { role: 'product_owner', scope: 'user_experience' }
  ],
  testingRequirements: [
    { type: 'penetration_test', scope: 'bid_confidentiality' },
    { type: 'load_test', scope: '1000_concurrent_bids' },
    { type: 'uat', scope: 'buyer_and_supplier_flows' }
  ]
};

const REVERSE_AUCTION_COMPLIANCE: AuctionTypeCompliance = {
  auctionType: AuctionType.REVERSE_AUCTION,
  checks: [
    { id: 'realtime_infrastructure', description: 'WebSocket 99.9% availability', status: 'required' },
    { id: 'anti_sniping', description: 'Extension rules prevent last-second manipulation', status: 'required' },
    { id: 'bid_validation', description: 'Minimum decrement enforced in real-time', status: 'required' },
    { id: 'concurrency_handling', description: 'Race conditions prevented', status: 'required' },
    { id: 'fallback_mechanism', description: 'Graceful degradation to sealed bid', status: 'required' },
    { id: 'collusion_detection', description: 'Pattern analysis for bid rigging', status: 'recommended' }
  ],
  approvals: [
    { role: 'security_team', scope: 'realtime_security' },
    { role: 'legal_team', scope: 'auction_rules_fairness' },
    { role: 'infrastructure_team', scope: 'scalability_and_reliability' }
  ],
  testingRequirements: [
    { type: 'chaos_engineering', scope: 'websocket_failure_recovery' },
    { type: 'load_test', scope: '500_concurrent_bidders' },
    { type: 'soak_test', scope: '4_hour_continuous_auction' }
  ]
};
```

### Auction Rule Engine

#### Rule Categories

| Category | Rules | Enforcement |
|----------|-------|-------------|
| Eligibility | Supplier tier, KYC status, category qualification | Pre-auction check |
| Bid Format | Currency, precision, required fields | Submission validation |
| Bid Validity | Minimum decrement, maximum bid, reserve price | Real-time validation |
| Timing | Deadline, extension triggers, cool-down periods | System-enforced |
| Fairness | Anti-sniping, bid withdrawal limits, collusion detection | Automated monitoring |

#### Rule Engine Implementation

```typescript
// Auction rule engine
interface AuctionRule {
  id: string;
  name: string;
  category: 'eligibility' | 'format' | 'validity' | 'timing' | 'fairness';
  evaluator: RuleEvaluator;
  severity: 'block' | 'warn' | 'log';
  message: string;
}

type RuleEvaluator = (context: AuctionContext, bid?: Bid) => Promise<RuleResult>;

interface RuleResult {
  passed: boolean;
  reason?: string;
  metadata?: Record<string, any>;
}

// Core rules
const AUCTION_RULES: AuctionRule[] = [
  // Eligibility Rules
  {
    id: 'supplier_kyc_valid',
    name: 'Supplier KYC Verification',
    category: 'eligibility',
    severity: 'block',
    message: 'Supplier must have valid KYC status to participate',
    evaluator: async (ctx) => {
      const supplier = await supplierService.findById(ctx.supplierId);
      return {
        passed: supplier.tier !== 'PENDING' && supplier.kycStatus === 'VERIFIED',
        reason: supplier.tier === 'PENDING' ? 'KYC verification required' : undefined
      };
    }
  },
  {
    id: 'supplier_invited',
    name: 'Supplier Invitation',
    category: 'eligibility',
    severity: 'block',
    message: 'Supplier must be invited to this RFQ',
    evaluator: async (ctx) => {
      const invitation = await rfqService.checkInvitation(ctx.rfqId, ctx.supplierId);
      return { passed: invitation !== null };
    }
  },

  // Validity Rules
  {
    id: 'minimum_decrement',
    name: 'Minimum Bid Decrement',
    category: 'validity',
    severity: 'block',
    message: 'Bid must improve on current best by minimum decrement',
    evaluator: async (ctx, bid) => {
      if (ctx.auctionType !== AuctionType.REVERSE_AUCTION) return { passed: true };

      const settings = ctx.auctionConfig.settings as ReverseAuctionSettings;
      const currentBest = await auctionService.getCurrentBestBid(ctx.rfqId);

      if (!currentBest) return { passed: true }; // First bid

      const requiredImprovement = settings.decrementType === 'PERCENTAGE'
        ? currentBest.amount * (settings.minimumDecrement / 100)
        : settings.minimumDecrement;

      const improvement = currentBest.amount - bid.amount;
      return {
        passed: improvement >= requiredImprovement,
        reason: `Bid must be at least ${requiredImprovement} lower than current best`,
        metadata: { currentBest: currentBest.amount, required: currentBest.amount - requiredImprovement }
      };
    }
  },

  // Timing Rules
  {
    id: 'within_deadline',
    name: 'Bid Deadline',
    category: 'timing',
    severity: 'block',
    message: 'Bid submitted after auction deadline',
    evaluator: async (ctx, bid) => {
      const rfq = await rfqService.findById(ctx.rfqId);
      const now = new Date();
      return {
        passed: now <= new Date(rfq.biddingDeadline),
        reason: 'Auction has closed'
      };
    }
  },

  // Fairness Rules
  {
    id: 'bid_withdrawal_limit',
    name: 'Bid Withdrawal Limit',
    category: 'fairness',
    severity: 'warn',
    message: 'Supplier has exceeded bid withdrawal limit',
    evaluator: async (ctx) => {
      const withdrawals = await auctionService.getWithdrawalCount(ctx.rfqId, ctx.supplierId);
      return {
        passed: withdrawals < 3,
        reason: 'Maximum 3 bid withdrawals allowed per auction'
      };
    }
  }
];

// Rule engine execution
class AuctionRuleEngine {
  async evaluateRules(
    context: AuctionContext,
    bid?: Bid,
    categories?: string[]
  ): Promise<RuleEvaluationResult> {
    const applicableRules = AUCTION_RULES.filter(
      rule => !categories || categories.includes(rule.category)
    );

    const results: RuleResult[] = [];
    const violations: RuleViolation[] = [];

    for (const rule of applicableRules) {
      const result = await rule.evaluator(context, bid);
      results.push(result);

      if (!result.passed) {
        violations.push({
          ruleId: rule.id,
          ruleName: rule.name,
          severity: rule.severity,
          message: rule.message,
          reason: result.reason
        });
      }
    }

    const blockingViolations = violations.filter(v => v.severity === 'block');

    return {
      allowed: blockingViolations.length === 0,
      violations,
      blockingCount: blockingViolations.length,
      warningCount: violations.filter(v => v.severity === 'warn').length
    };
  }
}
```

### Anti-Sniping Mechanisms

#### Extension Rules

| Trigger | Extension Duration | Max Extensions | Cool-Down |
|---------|-------------------|----------------|-----------|
| Bid in last 5 minutes | 3 minutes | 10 | None |
| Bid in last 2 minutes | 2 minutes | 5 | 30 seconds |
| Bid in last 30 seconds | 1 minute | 3 | 60 seconds |

#### Anti-Gaming Detection

| Pattern | Detection Method | Action |
|---------|------------------|--------|
| Shill bidding | Same IP/device, bid timing patterns | Flag for review, potential disqualification |
| Bid cycling | Alternating bids between related suppliers | Real-time alert, investigation |
| Bid withdrawal abuse | Multiple withdrawals to probe pricing | Warning, then block |
| Last-second flooding | Multiple bids in final seconds | Rate limit (1 bid per 10 seconds) |

```typescript
// Anti-sniping implementation
interface AntiSnipingConfig {
  extensionTriggerMinutes: number;
  extensionDurationMinutes: number;
  maxExtensions: number;
  coolDownSeconds: number;
  rateLimitBidsPerMinute: number;
}

const DEFAULT_ANTI_SNIPING: AntiSnipingConfig = {
  extensionTriggerMinutes: 5,
  extensionDurationMinutes: 3,
  maxExtensions: 10,
  coolDownSeconds: 0,
  rateLimitBidsPerMinute: 6
};

class AntiSnipingService {
  async checkAndExtend(rfqId: string, bidTimestamp: Date): Promise<ExtensionResult> {
    const rfq = await rfqRepository.findById(rfqId);
    const config = rfq.auctionConfig.antiSniping || DEFAULT_ANTI_SNIPING;

    const deadline = new Date(rfq.biddingDeadline);
    const minutesRemaining = (deadline.getTime() - bidTimestamp.getTime()) / 60000;

    if (minutesRemaining > config.extensionTriggerMinutes) {
      return { extended: false };
    }

    // Check extension count
    const currentExtensions = await this.getExtensionCount(rfqId);
    if (currentExtensions >= config.maxExtensions) {
      return { extended: false, reason: 'max_extensions_reached' };
    }

    // Apply extension
    const newDeadline = new Date(deadline.getTime() + config.extensionDurationMinutes * 60000);
    await rfqRepository.update(rfqId, { biddingDeadline: newDeadline });

    // Log extension
    await auctionLogRepository.create({
      rfqId,
      eventType: 'deadline_extended',
      previousDeadline: deadline,
      newDeadline,
      extensionNumber: currentExtensions + 1,
      triggerBidTimestamp: bidTimestamp
    });

    // Notify all participants
    await websocketGateway.broadcast(`rfq:${rfqId}`, {
      type: 'deadline_extended',
      newDeadline: newDeadline.toISOString(),
      extensionNumber: currentExtensions + 1,
      maxExtensions: config.maxExtensions
    });

    return {
      extended: true,
      newDeadline,
      extensionNumber: currentExtensions + 1
    };
  }

  async detectGaming(rfqId: string): Promise<GamingDetectionResult> {
    const bids = await bidRepository.findByRfq(rfqId);
    const alerts: GamingAlert[] = [];

    // Pattern 1: Same IP addresses
    const ipGroups = this.groupByIp(bids);
    for (const [ip, supplierIds] of Object.entries(ipGroups)) {
      if (supplierIds.length > 1) {
        alerts.push({
          type: 'same_ip_multiple_suppliers',
          severity: 'high',
          details: { ip, supplierIds }
        });
      }
    }

    // Pattern 2: Bid cycling (alternating bids)
    const cyclingPatterns = this.detectCycling(bids);
    if (cyclingPatterns.length > 0) {
      alerts.push({
        type: 'bid_cycling',
        severity: 'medium',
        details: { patterns: cyclingPatterns }
      });
    }

    // Pattern 3: Suspicious timing
    const timingPatterns = this.detectTimingPatterns(bids);
    alerts.push(...timingPatterns);

    return { alerts, requiresReview: alerts.some(a => a.severity === 'high') };
  }
}
```

### Reserve Price and Tie-Breaking

#### Reserve Price Handling

| Scenario | Visibility | Outcome |
|----------|------------|---------|
| Reserve not met, bids received | Hidden from suppliers | Buyer notified, can lower reserve or cancel |
| Reserve met | Hidden from suppliers | Auction proceeds normally |
| Reserve disclosed | Shown as "starting price" | All bids must be below |
| No reserve | N/A | Lowest bid wins |

```typescript
// Reserve price configuration
interface ReservePriceConfig {
  enabled: boolean;
  amount?: number;
  visibility: 'hidden' | 'disclosed' | 'disclosed_as_starting';
  autoAcceptIfMet: boolean;
  notifyBuyerIfNotMet: boolean;
}

// Reserve price evaluation
async function evaluateReservePrice(rfqId: string): Promise<ReserveEvaluation> {
  const rfq = await rfqRepository.findById(rfqId);
  const config = rfq.reservePriceConfig;

  if (!config?.enabled) {
    return { applicable: false };
  }

  const bestBid = await auctionService.getBestBid(rfqId);

  if (!bestBid) {
    return {
      applicable: true,
      met: false,
      reason: 'no_bids_received'
    };
  }

  const reserveMet = bestBid.amount <= config.amount;

  return {
    applicable: true,
    met: reserveMet,
    bestBid: bestBid.amount,
    reserve: config.visibility === 'hidden' ? undefined : config.amount,
    gap: reserveMet ? 0 : bestBid.amount - config.amount
  };
}
```

#### Tie-Breaking Rules

| Priority | Criterion | Rationale |
|----------|-----------|-----------|
| 1 | Earlier submission timestamp | Rewards speed |
| 2 | Higher supplier tier | Rewards quality/reliability |
| 3 | Better historical performance score | Data-driven selection |
| 4 | Proximity to delivery port | Logistical efficiency |
| 5 | Random selection | Final fallback |

```typescript
// Tie-breaking implementation
interface TieBreakingConfig {
  criteria: TieBreakCriterion[];
  finalFallback: 'random' | 'manual_selection' | 'split_award';
}

type TieBreakCriterion =
  | 'earliest_submission'
  | 'higher_tier'
  | 'better_performance'
  | 'closer_to_port'
  | 'more_items_quoted';

const DEFAULT_TIE_BREAKING: TieBreakingConfig = {
  criteria: [
    'earliest_submission',
    'higher_tier',
    'better_performance',
    'closer_to_port'
  ],
  finalFallback: 'random'
};

async function resolveTie(quotes: Quote[], config: TieBreakingConfig): Promise<Quote> {
  let remaining = [...quotes];

  for (const criterion of config.criteria) {
    if (remaining.length === 1) break;

    remaining = await applyTieBreaker(remaining, criterion);
  }

  if (remaining.length > 1) {
    switch (config.finalFallback) {
      case 'random':
        return remaining[Math.floor(Math.random() * remaining.length)];
      case 'manual_selection':
        throw new TieBreakRequiresManualSelectionError(remaining);
      case 'split_award':
        throw new TieBreakSuggestsSplitAwardError(remaining);
    }
  }

  return remaining[0];
}
```

### Auction Outcome Auditing

#### Audit Trail Requirements

| Event | Data Captured | Retention | Immutability |
|-------|---------------|-----------|--------------|
| Auction created | Config, rules, participants | 7 years | Append-only |
| Bid submitted | Timestamp, amount, supplier, IP | 7 years | Immutable |
| Bid modified | Before/after, reason | 7 years | Immutable |
| Deadline extended | Trigger, old/new deadline | 7 years | Immutable |
| Auction closed | Final rankings, winner | 7 years | Immutable |
| Gaming alert | Pattern, evidence | 7 years | Immutable |

#### Fairness Audit Report

```typescript
// Audit report generation
interface AuctionFairnessAudit {
  rfqId: string;
  auctionType: AuctionType;
  generatedAt: Date;
  summary: {
    participantCount: number;
    bidCount: number;
    extensionCount: number;
    withdrawalCount: number;
    gamingAlertsCount: number;
  };
  timeline: AuditTimelineEntry[];
  bidAnalysis: {
    priceDistribution: { min: number; max: number; median: number; stdDev: number };
    biddingPatterns: BiddingPattern[];
    suspiciousActivity: SuspiciousActivity[];
  };
  outcome: {
    winner: { supplierId: string; amount: number; rank: number };
    reservePriceMet: boolean;
    tieBreakApplied: boolean;
    manualOverride: boolean;
  };
  compliance: {
    rulesApplied: string[];
    violationsDetected: RuleViolation[];
    actionseTaken: string[];
  };
  certification: {
    auditorId: string;
    certifiedAt: Date;
    findings: string[];
    recommendation: 'approve' | 'review' | 'reject';
  };
}

// Generate audit report
async function generateFairnessAudit(rfqId: string): Promise<AuctionFairnessAudit> {
  const rfq = await rfqRepository.findById(rfqId);
  const bids = await bidRepository.findByRfq(rfqId);
  const logs = await auctionLogRepository.findByRfq(rfqId);

  return {
    rfqId,
    auctionType: rfq.auctionType,
    generatedAt: new Date(),
    summary: calculateSummary(bids, logs),
    timeline: buildTimeline(logs),
    bidAnalysis: analyzeBids(bids),
    outcome: extractOutcome(rfq),
    compliance: extractCompliance(logs),
    certification: { /* Pending manual certification */ }
  };
}
```

### Open Questions - Resolved

- **Q:** How will auction outcomes be audited for fairness?
  - **A:** Auction fairness is ensured through multiple mechanisms:

    **Real-Time Controls:**
    - Rule engine validates every bid against eligibility, format, validity, timing, and fairness rules
    - Anti-sniping extensions prevent last-second manipulation
    - Gaming detection flags suspicious patterns (same IP, bid cycling, timing anomalies)
    - Rate limiting prevents bid flooding

    **Audit Trail:**
    - Every bid, modification, and withdrawal is logged with immutable timestamps
    - IP addresses, device fingerprints, and session IDs captured
    - Extension events and triggers documented
    - All rule violations recorded with severity

    **Post-Auction Audit:**
    - Automated fairness audit report generated for every completed auction
    - Statistical analysis of bid distribution (outliers flagged)
    - Timeline reconstruction for manual review
    - Gaming alerts summarized with evidence

    **Certification Process:**
    - High-value auctions (>$100K) require manual audit certification
    - Auctions with gaming alerts require review before award confirmation
    - Quarterly sample audits of random auctions by compliance team
    - Annual third-party audit of auction system integrity

---

## References
- [Reverse Auction Best Practices](https://www.procurement-academy.com/reverse-auctions/)
- [Multi-Criteria Decision Analysis](https://en.wikipedia.org/wiki/Multiple-criteria_decision_analysis)
- [Socket.io Documentation](https://socket.io/docs/v4/)
