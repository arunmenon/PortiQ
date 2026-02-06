# ADR-FN-013: Quote Comparison & TCO Engine

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

Buyers need a sophisticated quote comparison tool that evaluates supplier quotes beyond unit price, incorporating total cost of ownership (TCO) factors specific to maritime procurement.

### Business Context
Maritime procurement decisions involve complex trade-offs:
- **Shipping costs**: Vary significantly by supplier location and delivery port
- **Lead time**: Urgent requirements may justify higher prices
- **Quality/reliability**: Supplier track record affects operational risk
- **Payment terms**: Extended terms have financing value
- **Partial fulfillment**: Splitting orders across suppliers has coordination costs

A TCO engine helps procurement teams make optimal decisions by quantifying these factors into comparable scores.

### Technical Context
- Multiple quotes per RFQ with line-item granularity
- Integration with auction types (ADR-FN-012)
- Supplier performance data from order history
- Real-time calculation for interactive comparison UI
- Support for buyer-configurable weighting

### Assumptions
- Buyers can configure evaluation criteria weights
- Historical supplier data is available for quality scoring
- Shipping cost estimation is feasible
- Payment term value can be calculated from financing rates

---

## Decision Drivers

- Comprehensive comparison beyond unit price
- Configurable to buyer priorities
- Transparent scoring methodology
- Line-item level analysis capability
- Support for partial awards
- Integration with award recommendation

---

## Considered Options

### Option 1: Simple Price Comparison
**Description:** Compare quotes purely on total price with basic filtering.

**Pros:**
- Simple implementation
- Easy to understand
- Fast calculation

**Cons:**
- Ignores critical factors
- Suboptimal decisions
- No differentiation from competitors

### Option 2: Weighted Multi-Criteria Model
**Description:** Calculate TCO score using configurable weights for price, shipping, lead time, quality, and terms.

**Pros:**
- Comprehensive evaluation
- Buyer-configurable
- Transparent methodology
- Supports optimization

**Cons:**
- More complex implementation
- Requires data for all factors
- Weight calibration needed

### Option 3: AI-Based Recommendation
**Description:** Machine learning model recommends optimal supplier based on historical outcomes.

**Pros:**
- Learns from past decisions
- Handles complex patterns
- Improves over time

**Cons:**
- Requires substantial training data
- Black-box decisions
- Cold start problem
- Harder to explain to users

---

## Decision

**Chosen Option:** Weighted Multi-Criteria Model

We will implement a TCO engine using weighted multi-criteria scoring with configurable weights, transparent calculations, and support for line-item and order-level analysis.

### Rationale
A weighted multi-criteria model provides the optimal balance of comprehensiveness and transparency. Buyers can understand and configure the scoring methodology, building trust in recommendations. The model can be enhanced with ML-based weight suggestions over time without sacrificing explainability.

---

## Consequences

### Positive
- Comprehensive evaluation of total value
- Transparent, auditable scoring
- Buyer-configurable priorities
- Supports optimal award decisions
- Differentiating platform capability

### Negative
- Requires data for all scoring factors
- **Mitigation:** Graceful degradation when data missing, default values
- Weight calibration is subjective
- **Mitigation:** Provide industry templates, allow customization

### Risks
- Missing data skews scores: Clear indication of data completeness
- Gaming by suppliers: Audit trail, outcome tracking
- Over-reliance on scores: Present as decision support, not replacement

---

## Implementation Notes

### TCO Scoring Model

```typescript
// tco/models/tco-config.model.ts
export interface TcoConfig {
  weights: TcoWeights;
  thresholds: TcoThresholds;
  penaltyRates: PenaltyRates;
}

export interface TcoWeights {
  unitPrice: number;        // 0-100
  shippingCost: number;     // 0-100
  leadTime: number;         // 0-100
  qualityScore: number;     // 0-100
  paymentTerms: number;     // 0-100
  supplierRating: number;   // 0-100
}

export interface TcoThresholds {
  maxAcceptableLeadDays: number;
  minAcceptableQualityScore: number;
  preferredPaymentTermsDays: number;
}

export interface PenaltyRates {
  leadTimePenaltyPerDay: number;      // % penalty per day over preferred
  paymentTermValuePerDay: number;     // % value per day of extended terms
  partialFulfillmentPenalty: number;  // Fixed penalty for splitting orders
}

// Default configuration
export const DEFAULT_TCO_CONFIG: TcoConfig = {
  weights: {
    unitPrice: 40,
    shippingCost: 15,
    leadTime: 15,
    qualityScore: 15,
    paymentTerms: 10,
    supplierRating: 5
  },
  thresholds: {
    maxAcceptableLeadDays: 14,
    minAcceptableQualityScore: 70,
    preferredPaymentTermsDays: 30
  },
  penaltyRates: {
    leadTimePenaltyPerDay: 1.5,
    paymentTermValuePerDay: 0.05,
    partialFulfillmentPenalty: 5
  }
};
```

### TCO Calculation Service

```typescript
// tco/services/tco-engine.service.ts
@Injectable()
export class TcoEngineService {
  constructor(
    private readonly supplierService: SupplierService,
    private readonly shippingService: ShippingService
  ) {}

  async calculateTco(
    quote: Quote,
    rfq: Rfq,
    config: TcoConfig = DEFAULT_TCO_CONFIG
  ): Promise<TcoResult> {
    const components: TcoComponent[] = [];

    // 1. Unit Price Score (normalized)
    const priceScore = await this.calculatePriceScore(quote, rfq);
    components.push({
      factor: 'unitPrice',
      rawValue: quote.totalAmount,
      normalizedScore: priceScore,
      weight: config.weights.unitPrice,
      weightedScore: priceScore * config.weights.unitPrice / 100
    });

    // 2. Shipping Cost Score
    const shippingScore = await this.calculateShippingScore(quote, rfq);
    components.push({
      factor: 'shippingCost',
      rawValue: shippingScore.estimatedCost,
      normalizedScore: shippingScore.score,
      weight: config.weights.shippingCost,
      weightedScore: shippingScore.score * config.weights.shippingCost / 100
    });

    // 3. Lead Time Score
    const leadTimeScore = this.calculateLeadTimeScore(quote, config);
    components.push({
      factor: 'leadTime',
      rawValue: quote.leadTimeDays,
      normalizedScore: leadTimeScore,
      weight: config.weights.leadTime,
      weightedScore: leadTimeScore * config.weights.leadTime / 100
    });

    // 4. Quality Score
    const qualityScore = await this.calculateQualityScore(quote);
    components.push({
      factor: 'qualityScore',
      rawValue: qualityScore.historicalScore,
      normalizedScore: qualityScore.score,
      weight: config.weights.qualityScore,
      weightedScore: qualityScore.score * config.weights.qualityScore / 100
    });

    // 5. Payment Terms Score
    const paymentScore = this.calculatePaymentTermsScore(quote, config);
    components.push({
      factor: 'paymentTerms',
      rawValue: quote.paymentTermsDays,
      normalizedScore: paymentScore,
      weight: config.weights.paymentTerms,
      weightedScore: paymentScore * config.weights.paymentTerms / 100
    });

    // 6. Supplier Rating Score
    const supplierScore = await this.calculateSupplierScore(quote.supplierId);
    components.push({
      factor: 'supplierRating',
      rawValue: supplierScore.rating,
      normalizedScore: supplierScore.score,
      weight: config.weights.supplierRating,
      weightedScore: supplierScore.score * config.weights.supplierRating / 100
    });

    // Calculate total TCO score
    const totalWeight = Object.values(config.weights).reduce((a, b) => a + b, 0);
    const totalScore = components.reduce((sum, c) => sum + c.weightedScore, 0);
    const normalizedTotal = (totalScore / totalWeight) * 100;

    // Calculate effective TCO amount
    const effectiveTco = this.calculateEffectiveTcoAmount(quote, components, config);

    return {
      quoteId: quote.id,
      supplierId: quote.supplierId,
      totalScore: normalizedTotal,
      effectiveTcoAmount: effectiveTco,
      components,
      dataCompleteness: this.calculateDataCompleteness(components),
      generatedAt: new Date()
    };
  }

  private async calculatePriceScore(quote: Quote, rfq: Rfq): Promise<number> {
    // Get all quotes for this RFQ to normalize
    const allQuotes = await this.quoteRepository.findByRfq(rfq.id);
    const prices = allQuotes.map(q => q.totalAmount);

    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);

    if (minPrice === maxPrice) return 100;

    // Lower price = higher score (inverted normalization)
    return 100 - ((quote.totalAmount - minPrice) / (maxPrice - minPrice)) * 100;
  }

  private calculateLeadTimeScore(quote: Quote, config: TcoConfig): number {
    const preferredDays = config.thresholds.maxAcceptableLeadDays;

    if (quote.leadTimeDays <= preferredDays) {
      // Bonus for faster delivery
      return 100 + ((preferredDays - quote.leadTimeDays) * 2);
    }

    // Penalty for slower delivery
    const daysOver = quote.leadTimeDays - preferredDays;
    const penalty = daysOver * config.penaltyRates.leadTimePenaltyPerDay;

    return Math.max(0, 100 - penalty);
  }

  private async calculateQualityScore(quote: Quote): Promise<QualityScoreResult> {
    const supplier = await this.supplierService.findById(quote.supplierId);
    const orderHistory = await this.supplierService.getOrderHistory(quote.supplierId);

    // Calculate from historical performance
    const metrics = {
      orderAccuracy: orderHistory.accurateOrders / orderHistory.totalOrders,
      onTimeDelivery: orderHistory.onTimeDeliveries / orderHistory.totalOrders,
      qualityComplaints: 1 - (orderHistory.complaints / orderHistory.totalOrders),
      returnRate: 1 - (orderHistory.returns / orderHistory.totalOrders)
    };

    const historicalScore =
      metrics.orderAccuracy * 30 +
      metrics.onTimeDelivery * 30 +
      metrics.qualityComplaints * 25 +
      metrics.returnRate * 15;

    return {
      historicalScore,
      score: historicalScore,
      metrics,
      orderCount: orderHistory.totalOrders
    };
  }

  private calculatePaymentTermsScore(quote: Quote, config: TcoConfig): number {
    const preferredDays = config.thresholds.preferredPaymentTermsDays;
    const valuePerDay = config.penaltyRates.paymentTermValuePerDay;

    // Longer payment terms are better for buyer
    const extraDays = quote.paymentTermsDays - preferredDays;
    const bonus = extraDays * valuePerDay;

    return Math.min(100 + bonus, 120); // Cap at 120%
  }

  private calculateEffectiveTcoAmount(
    quote: Quote,
    components: TcoComponent[],
    config: TcoConfig
  ): number {
    let effectiveAmount = quote.totalAmount;

    // Add shipping cost
    const shippingComponent = components.find(c => c.factor === 'shippingCost');
    effectiveAmount += shippingComponent?.rawValue ?? 0;

    // Add lead time penalty (monetized)
    const leadTimeComponent = components.find(c => c.factor === 'leadTime');
    if (leadTimeComponent && leadTimeComponent.normalizedScore < 100) {
      const penaltyPercent = (100 - leadTimeComponent.normalizedScore) / 100;
      effectiveAmount += quote.totalAmount * penaltyPercent * 0.1;
    }

    // Subtract payment terms value
    const paymentComponent = components.find(c => c.factor === 'paymentTerms');
    if (paymentComponent && paymentComponent.normalizedScore > 100) {
      const bonusPercent = (paymentComponent.normalizedScore - 100) / 100;
      effectiveAmount -= quote.totalAmount * bonusPercent;
    }

    return effectiveAmount;
  }
}
```

### Quote Comparison Service

```typescript
// tco/services/quote-comparison.service.ts
@Injectable()
export class QuoteComparisonService {
  constructor(private readonly tcoEngine: TcoEngineService) {}

  async compareQuotes(
    rfqId: string,
    config?: TcoConfig
  ): Promise<QuoteComparisonResult> {
    const quotes = await this.quoteRepository.findByRfq(rfqId);
    const rfq = await this.rfqRepository.findById(rfqId);

    // Calculate TCO for all quotes
    const tcoResults = await Promise.all(
      quotes.map(quote => this.tcoEngine.calculateTco(quote, rfq, config))
    );

    // Rank by TCO score
    tcoResults.sort((a, b) => b.totalScore - a.totalScore);

    // Generate line-item comparison
    const lineItemComparison = this.generateLineItemComparison(quotes, rfq);

    // Identify optimal split (if applicable)
    const optimalSplit = await this.calculateOptimalSplit(quotes, rfq, config);

    return {
      rfqId,
      rankings: tcoResults.map((tco, index) => ({
        rank: index + 1,
        ...tco
      })),
      lineItemComparison,
      optimalSplit,
      recommendation: this.generateRecommendation(tcoResults, optimalSplit)
    };
  }

  private generateLineItemComparison(
    quotes: Quote[],
    rfq: Rfq
  ): LineItemComparison[] {
    return rfq.lineItems.map(lineItem => {
      const supplierPrices = quotes.map(quote => {
        const quoteLine = quote.lineItems.find(
          ql => ql.rfqLineItemId === lineItem.id
        );

        return {
          supplierId: quote.supplierId,
          supplierName: quote.supplier.name,
          unitPrice: quoteLine?.unitPrice,
          quantity: quoteLine?.quantity,
          totalPrice: quoteLine ? quoteLine.unitPrice * quoteLine.quantity : null,
          available: !!quoteLine
        };
      });

      // Find best price
      const availablePrices = supplierPrices.filter(sp => sp.available);
      const bestPrice = Math.min(...availablePrices.map(sp => sp.unitPrice!));

      return {
        lineItemId: lineItem.id,
        productName: lineItem.productName,
        impaCode: lineItem.impaCode,
        requestedQuantity: lineItem.quantity,
        supplierPrices: supplierPrices.map(sp => ({
          ...sp,
          isBestPrice: sp.unitPrice === bestPrice
        }))
      };
    });
  }

  private async calculateOptimalSplit(
    quotes: Quote[],
    rfq: Rfq,
    config?: TcoConfig
  ): Promise<OptimalSplitResult | null> {
    // Check if split makes sense
    if (quotes.length < 2) return null;

    // Find best supplier for each line item
    const optimalAssignments: Map<string, string> = new Map();

    for (const lineItem of rfq.lineItems) {
      let bestSupplier: string | null = null;
      let bestValue = Infinity;

      for (const quote of quotes) {
        const quoteLine = quote.lineItems.find(
          ql => ql.rfqLineItemId === lineItem.id
        );

        if (quoteLine && quoteLine.unitPrice < bestValue) {
          bestValue = quoteLine.unitPrice;
          bestSupplier = quote.supplierId;
        }
      }

      if (bestSupplier) {
        optimalAssignments.set(lineItem.id, bestSupplier);
      }
    }

    // Check if split is actually better
    const uniqueSuppliers = new Set(optimalAssignments.values());

    if (uniqueSuppliers.size <= 1) return null;

    // Calculate split savings vs single supplier
    const splitTotal = this.calculateSplitTotal(optimalAssignments, quotes, rfq);
    const singleBest = Math.min(...quotes.map(q => q.totalAmount));
    const savings = singleBest - splitTotal;

    // Apply coordination penalty
    const penalty = (uniqueSuppliers.size - 1) * (config?.penaltyRates.partialFulfillmentPenalty ?? 5) / 100 * splitTotal;
    const netSavings = savings - penalty;

    if (netSavings <= 0) return null;

    return {
      assignments: Array.from(optimalAssignments.entries()).map(([lineItemId, supplierId]) => ({
        lineItemId,
        supplierId
      })),
      supplierCount: uniqueSuppliers.size,
      splitTotal,
      singleBestTotal: singleBest,
      grossSavings: savings,
      coordinationPenalty: penalty,
      netSavings
    };
  }
}
```

### Comparison Response Model

```typescript
// tco/models/comparison-result.model.ts
export interface QuoteComparisonResult {
  rfqId: string;
  rankings: RankedTcoResult[];
  lineItemComparison: LineItemComparison[];
  optimalSplit: OptimalSplitResult | null;
  recommendation: Recommendation;
}

export interface Recommendation {
  type: 'SINGLE_SUPPLIER' | 'SPLIT_ORDER' | 'REVIEW_REQUIRED';
  primarySupplierId?: string;
  rationale: string;
  confidence: number;
  considerations: string[];
}

export interface LineItemComparison {
  lineItemId: string;
  productName: string;
  impaCode: string;
  requestedQuantity: number;
  supplierPrices: {
    supplierId: string;
    supplierName: string;
    unitPrice: number | null;
    quantity: number | null;
    totalPrice: number | null;
    available: boolean;
    isBestPrice: boolean;
  }[];
}
```

### Dependencies
- ADR-FN-011: RFQ Workflow State Machine
- ADR-FN-012: Auction Types
- ADR-FN-014: Supplier Onboarding & KYC
- ADR-NF-001: PostgreSQL as Unified Data Store

### Migration Strategy
1. Implement TCO calculation engine
2. Create configurable weights interface
3. Build quote comparison service
4. Add line-item comparison view
5. Implement split order optimization
6. Create comparison UI components
7. Add industry-standard weight templates

---

## Operational Considerations

### TCO Cost Components and Transparency

#### Cost Component Breakdown

| Component | Description | Calculation Method | Data Source |
|-----------|-------------|-------------------|-------------|
| Unit Price | Base product price | Sum(quantity x unit_price) | Quote |
| Shipping Cost | Delivery to vessel/port | Distance-based + weight/volume | Shipping API |
| Lead Time Cost | Opportunity cost of delay | days_over_target x daily_penalty_rate | Quote + config |
| Quality Risk | Expected rework/returns | (1 - quality_score) x order_value x risk_factor | Supplier history |
| Payment Terms Value | Financing benefit/cost | (terms_days - baseline) x daily_rate x order_value | Quote + config |
| Coordination Cost | Multi-supplier overhead | flat_fee x (supplier_count - 1) | System calc |
| Compliance Cost | Certification/documentation | Fixed per category | Product metadata |

#### Transparent Scoring Formula

```typescript
// TCO calculation with full transparency
interface TcoBreakdown {
  quoteId: string;
  basePrice: {
    amount: number;
    weight: number;
    contribution: number;
  };
  shippingCost: {
    estimatedAmount: number;
    calculationMethod: 'distance_based' | 'weight_based' | 'supplier_provided';
    weight: number;
    contribution: number;
  };
  leadTimeScore: {
    daysQuoted: number;
    targetDays: number;
    penaltyApplied: number;
    weight: number;
    contribution: number;
  };
  qualityScore: {
    historicalScore: number;
    orderCount: number;
    confidenceLevel: 'high' | 'medium' | 'low';
    weight: number;
    contribution: number;
  };
  paymentTermsValue: {
    termsOffered: number;
    baselineTerms: number;
    dailyRate: number;
    valueAmount: number;
    weight: number;
    contribution: number;
  };
  supplierRating: {
    overallRating: number;
    ratingCount: number;
    weight: number;
    contribution: number;
  };
  totalScore: number;
  effectiveTcoAmount: number;
  calculationTimestamp: Date;
  configVersion: string;
}

// Formula documentation shown to buyers
const TCO_FORMULA_EXPLANATION = `
TCO Score = Σ(Component Score × Component Weight) / Total Weight

Where each component score is normalized to 0-100:
- Unit Price Score = 100 × (1 - (your_price - min_price) / (max_price - min_price))
- Shipping Score = 100 × (1 - (your_shipping - min_shipping) / (max_shipping - min_shipping))
- Lead Time Score = 100 - (days_over_target × penalty_per_day)
- Quality Score = Historical performance percentage
- Payment Terms Score = 100 + (extra_days × value_per_day)
- Supplier Rating = Rating × 20 (converts 1-5 to 0-100)

Effective TCO Amount = Base Price + Shipping + Lead Time Penalty - Payment Terms Benefit
`;
```

#### Buyer-Visible Information

| Information | Always Shown | On Request | Never Shown |
|-------------|--------------|------------|-------------|
| Own quote details | Yes | N/A | N/A |
| TCO score | Yes | N/A | N/A |
| Score breakdown | Yes | N/A | N/A |
| Competitor scores | After deadline | N/A | Before deadline |
| Competitor prices | After deadline | N/A | Before deadline |
| Weight configuration | Yes | N/A | N/A |
| Historical basis | Summary | Full details | Raw data |

### Weighting Governance

#### Weight Configuration Authority

| Role | Can View | Can Modify | Requires Approval |
|------|----------|------------|-------------------|
| Procurement Officer | Own RFQs | No | N/A |
| Procurement Manager | Team RFQs | Yes, within limits | No |
| Buyer Admin | All org RFQs | Yes, any valid config | No |
| Platform Admin | All | Yes, including system defaults | Yes (for defaults) |

#### Weight Validation Rules

```typescript
// Weight constraints
interface WeightConstraints {
  unitPrice: { min: 20, max: 80 };
  shippingCost: { min: 5, max: 30 };
  leadTime: { min: 5, max: 30 };
  qualityScore: { min: 5, max: 40 };
  paymentTerms: { min: 0, max: 20 };
  supplierRating: { min: 0, max: 20 };
}

// Total weight must equal 100
const WEIGHT_TOTAL_REQUIRED = 100;

// Validation function
function validateWeights(weights: TcoWeights): ValidationResult {
  const errors: string[] = [];

  // Check individual constraints
  for (const [component, value] of Object.entries(weights)) {
    const constraints = WEIGHT_CONSTRAINTS[component];
    if (value < constraints.min || value > constraints.max) {
      errors.push(`${component} weight must be between ${constraints.min} and ${constraints.max}`);
    }
  }

  // Check total
  const total = Object.values(weights).reduce((sum, w) => sum + w, 0);
  if (total !== WEIGHT_TOTAL_REQUIRED) {
    errors.push(`Weights must sum to ${WEIGHT_TOTAL_REQUIRED}, got ${total}`);
  }

  // Business rule: price must be highest weight
  if (weights.unitPrice < Math.max(weights.qualityScore, weights.leadTime)) {
    errors.push('Unit price must be the highest weighted factor');
  }

  return { valid: errors.length === 0, errors };
}
```

#### Industry Templates

| Template | Price | Shipping | Lead Time | Quality | Payment | Supplier |
|----------|-------|----------|-----------|---------|---------|----------|
| Commodity Purchase | 50% | 15% | 10% | 10% | 10% | 5% |
| Technical Equipment | 35% | 10% | 15% | 25% | 10% | 5% |
| Urgent Requirement | 30% | 10% | 35% | 10% | 10% | 5% |
| Strategic Sourcing | 25% | 10% | 10% | 30% | 15% | 10% |
| Quality Critical | 25% | 10% | 10% | 40% | 10% | 5% |

### TCO Audit Trail

#### Audit Events

| Event | Data Captured | Retention |
|-------|---------------|-----------|
| Weight config created | Weights, created_by, template_used | 7 years |
| Weight config modified | Before/after, modified_by, reason | 7 years |
| TCO calculated | Full breakdown, config version | 7 years |
| Comparison viewed | User, timestamp, quotes compared | 2 years |
| Award decision | Selected quote, TCO rank, override_reason | 7 years |

```typescript
// TCO audit record
interface TcoAuditRecord {
  id: string;
  rfqId: string;
  eventType: 'config_created' | 'config_modified' | 'calculated' | 'viewed' | 'award_decision';
  timestamp: Date;
  userId: string;
  organizationId: string;
  payload: {
    // For config events
    weights?: TcoWeights;
    previousWeights?: TcoWeights;
    modificationReason?: string;

    // For calculation events
    calculations?: TcoBreakdown[];
    configVersion?: string;

    // For award events
    selectedQuoteId?: string;
    tcoRank?: number;
    overrideReason?: string;
    awardJustification?: string;
  };
}

// Audit query for compliance
async function getAwardAuditTrail(rfqId: string): Promise<AwardAuditTrail> {
  const events = await tcoAuditRepository.findByRfq(rfqId);

  return {
    rfqId,
    weightConfiguration: {
      initial: events.find(e => e.eventType === 'config_created'),
      modifications: events.filter(e => e.eventType === 'config_modified'),
      final: getCurrentConfig(events)
    },
    calculations: events.filter(e => e.eventType === 'calculated'),
    awardDecision: events.find(e => e.eventType === 'award_decision'),
    viewHistory: events.filter(e => e.eventType === 'viewed')
  };
}
```

### Currency, Tax, and Unit Normalization

#### Currency Handling

| Scenario | Normalization | Rate Source | Display |
|----------|---------------|-------------|---------|
| All quotes same currency | No conversion | N/A | Original currency |
| Mixed currencies | Convert to RFQ currency | Daily ECB/RBI rates | Converted + original |
| Cross-border with markup | Add conversion fee | Rate + 1.5% | Effective rate shown |

```typescript
// Currency normalization
interface CurrencyNormalization {
  originalCurrency: string;
  originalAmount: number;
  normalizedCurrency: string;
  normalizedAmount: number;
  exchangeRate: number;
  rateSource: 'ECB' | 'RBI' | 'supplier_provided';
  rateTimestamp: Date;
  conversionFee?: number;
}

async function normalizeQuoteCurrency(
  quote: Quote,
  targetCurrency: string
): Promise<NormalizedQuote> {
  if (quote.currency === targetCurrency) {
    return { ...quote, currencyNormalization: null };
  }

  const rate = await exchangeRateService.getRate(
    quote.currency,
    targetCurrency,
    new Date()
  );

  const conversionFee = quote.currency !== 'INR' && targetCurrency !== 'INR'
    ? 0.015 // 1.5% for cross-currency
    : 0;

  const effectiveRate = rate.rate * (1 + conversionFee);

  return {
    ...quote,
    normalizedAmount: quote.totalAmount * effectiveRate,
    currencyNormalization: {
      originalCurrency: quote.currency,
      originalAmount: quote.totalAmount,
      normalizedCurrency: targetCurrency,
      normalizedAmount: quote.totalAmount * effectiveRate,
      exchangeRate: rate.rate,
      rateSource: rate.source,
      rateTimestamp: rate.timestamp,
      conversionFee: conversionFee > 0 ? quote.totalAmount * conversionFee * rate.rate : undefined
    }
  };
}
```

#### Tax Normalization

| Scenario | Handling | Display |
|----------|----------|---------|
| All quotes include GST | Compare as-is | "Prices include GST" |
| Mixed (some include, some exclude) | Normalize to exclude | "Prices shown excluding GST" |
| Different GST rates (category-based) | Apply correct rate per item | Line-item tax breakdown |
| Export (0% GST) | Mark as export-eligible | "GST: Export - 0%" |

```typescript
// Tax normalization rules
interface TaxNormalization {
  normalizationMethod: 'include_all' | 'exclude_all';
  lineItemTax: {
    lineItemId: string;
    productCategory: string;
    gstRate: number;
    originalAmount: number;
    taxAmount: number;
    normalizedAmount: number;
  }[];
  totalTax: number;
  totalNormalized: number;
}

function normalizeQuoteTax(quote: Quote, method: 'include_all' | 'exclude_all'): NormalizedQuote {
  const lineItemTax = quote.lineItems.map(item => {
    const gstRate = getGstRateForCategory(item.hsnCode);
    const taxIncluded = quote.pricesIncludeTax;

    let originalAmount = item.quantity * item.unitPrice;
    let taxAmount: number;
    let normalizedAmount: number;

    if (taxIncluded) {
      taxAmount = originalAmount - (originalAmount / (1 + gstRate));
      normalizedAmount = method === 'exclude_all'
        ? originalAmount - taxAmount
        : originalAmount;
    } else {
      taxAmount = originalAmount * gstRate;
      normalizedAmount = method === 'include_all'
        ? originalAmount + taxAmount
        : originalAmount;
    }

    return {
      lineItemId: item.id,
      productCategory: item.hsnCode,
      gstRate,
      originalAmount,
      taxAmount,
      normalizedAmount
    };
  });

  return {
    ...quote,
    taxNormalization: {
      normalizationMethod: method,
      lineItemTax,
      totalTax: lineItemTax.reduce((sum, lt) => sum + lt.taxAmount, 0),
      totalNormalized: lineItemTax.reduce((sum, lt) => sum + lt.normalizedAmount, 0)
    }
  };
}
```

#### Unit Normalization

| Scenario | Handling | Conversion |
|----------|----------|------------|
| Same UOM across quotes | Direct comparison | None |
| Different UOM (kg vs lb) | Convert to RFQ UOM | Standard conversion factors |
| Pack sizes differ | Normalize to per-unit | price / pack_size |
| Minimum order qty | Include in comparison | Flag if MOQ > requested |

```typescript
// Unit of measure normalization
interface UomNormalization {
  originalUom: string;
  originalQuantity: number;
  originalUnitPrice: number;
  normalizedUom: string;
  normalizedQuantity: number;
  normalizedUnitPrice: number;
  conversionFactor: number;
}

const UOM_CONVERSIONS: Record<string, Record<string, number>> = {
  'kg': { 'lb': 2.20462, 'g': 1000, 'oz': 35.274 },
  'l': { 'gal': 0.264172, 'ml': 1000, 'qt': 1.05669 },
  'm': { 'ft': 3.28084, 'cm': 100, 'in': 39.3701 },
  'each': { 'dozen': 0.0833, 'pair': 0.5, 'set': 1 }
};

function normalizeLineItemUom(
  quoteItem: QuoteLineItem,
  rfqItem: RfqLineItem
): NormalizedLineItem {
  if (quoteItem.uom === rfqItem.uom) {
    return { ...quoteItem, uomNormalization: null };
  }

  const conversionFactor = getConversionFactor(quoteItem.uom, rfqItem.uom);

  if (!conversionFactor) {
    throw new UomConversionError(
      `Cannot convert ${quoteItem.uom} to ${rfqItem.uom}`
    );
  }

  return {
    ...quoteItem,
    uomNormalization: {
      originalUom: quoteItem.uom,
      originalQuantity: quoteItem.quantity,
      originalUnitPrice: quoteItem.unitPrice,
      normalizedUom: rfqItem.uom,
      normalizedQuantity: quoteItem.quantity * conversionFactor,
      normalizedUnitPrice: quoteItem.unitPrice / conversionFactor,
      conversionFactor
    }
  };
}
```

### Handling Missing and Supplier-Specific Fields

#### Missing Data Strategy

| Field | If Missing | Default Value | Impact on Score |
|-------|------------|---------------|-----------------|
| Shipping cost | Estimate from location | Distance-based estimate | Flag as estimated |
| Lead time | Use category average | 14 days | Apply uncertainty penalty |
| Quality score | Use tier-based default | 70 (BASIC), 80 (VERIFIED), 85 (PREFERRED) | Flag as default |
| Payment terms | Assume standard | Net 30 | No penalty/bonus |
| Supplier rating | Use tier proxy | 3.5 (BASIC), 4.0 (VERIFIED), 4.5 (PREFERRED) | Flag as proxy |

```typescript
// Missing data handling
interface DataCompletenessReport {
  quoteId: string;
  overallCompleteness: number; // 0-100%
  fields: {
    fieldName: string;
    status: 'provided' | 'estimated' | 'defaulted' | 'missing';
    value: any;
    source: 'supplier' | 'system' | 'default';
    confidenceLevel: 'high' | 'medium' | 'low';
  }[];
  warnings: string[];
}

function handleMissingData(quote: Quote, rfq: Rfq): EnrichedQuote {
  const report: DataCompletenessReport = {
    quoteId: quote.id,
    overallCompleteness: 0,
    fields: [],
    warnings: []
  };

  // Shipping cost
  if (!quote.shippingCost) {
    const estimated = estimateShippingCost(quote.supplierId, rfq.deliveryPort);
    quote.shippingCost = estimated.cost;
    report.fields.push({
      fieldName: 'shippingCost',
      status: 'estimated',
      value: estimated.cost,
      source: 'system',
      confidenceLevel: estimated.confidence
    });
    report.warnings.push('Shipping cost estimated - actual may vary');
  }

  // Quality score
  if (!quote.qualityScore) {
    const supplier = await supplierService.findById(quote.supplierId);
    const defaultScore = TIER_DEFAULT_QUALITY[supplier.tier];
    quote.qualityScore = defaultScore;
    report.fields.push({
      fieldName: 'qualityScore',
      status: 'defaulted',
      value: defaultScore,
      source: 'default',
      confidenceLevel: 'low'
    });
    report.warnings.push('Quality score based on tier default - no transaction history');
  }

  // Calculate completeness
  const providedCount = report.fields.filter(f => f.status === 'provided').length;
  report.overallCompleteness = (providedCount / report.fields.length) * 100;

  return { ...quote, dataCompleteness: report };
}
```

#### Supplier-Specific Fields

| Field Type | Handling | Display |
|------------|----------|---------|
| Custom certifications | Include as qualitative note | Shown in supplier details |
| Warranty terms | Monetize if quantifiable | Add to TCO if configured |
| Bundle discounts | Apply to line items | Show original + discounted |
| Exclusivity offers | Flag for buyer consideration | Highlight in comparison |
| Value-added services | List separately | Optional add-on section |

```typescript
// Supplier-specific field handling
interface SupplierSpecificFields {
  certifications: {
    name: string;
    relevance: 'required' | 'preferred' | 'bonus';
    verified: boolean;
  }[];
  warrantyTerms: {
    durationMonths: number;
    coverage: string;
    monetizedValue?: number;
  };
  bundleDiscounts: {
    threshold: number;
    discountPercent: number;
    applied: boolean;
  }[];
  valueAddedServices: {
    service: string;
    included: boolean;
    additionalCost?: number;
  }[];
  notes: string[];
}

// Display in comparison
function renderSupplierSpecificFields(fields: SupplierSpecificFields): ComparisonSection {
  return {
    sectionTitle: 'Additional Offerings',
    items: [
      {
        label: 'Certifications',
        value: fields.certifications.map(c => c.name).join(', '),
        highlight: fields.certifications.some(c => c.relevance === 'required')
      },
      {
        label: 'Warranty',
        value: `${fields.warrantyTerms.durationMonths} months`,
        subtext: fields.warrantyTerms.coverage
      },
      {
        label: 'Value-Added Services',
        value: fields.valueAddedServices.filter(v => v.included).map(v => v.service).join(', ')
      }
    ],
    notes: fields.notes
  };
}
```

### Open Questions - Resolved

- **Q:** How are missing or supplier-specific fields handled in comparisons?
  - **A:** Missing and supplier-specific fields are handled through a comprehensive data completeness framework:

    **Missing Data:**
    - Each quote receives a Data Completeness Report showing which fields are provided, estimated, defaulted, or missing
    - System estimates missing shipping costs using distance-based calculations with confidence levels
    - Missing quality scores default to tier-based values (70% for BASIC, 80% for VERIFIED, etc.)
    - Lead times default to category averages (typically 14 days) with uncertainty penalties
    - Payment terms assume Net 30 if not specified
    - All estimated/defaulted values are clearly flagged in the comparison UI with warnings
    - Overall completeness percentage is shown to help buyers assess quote reliability

    **Supplier-Specific Fields:**
    - Custom certifications are displayed as qualitative notes and flagged if they match RFQ requirements
    - Extended warranty terms can be monetized and added to TCO if the buyer enables this option
    - Bundle discounts are applied to affected line items with clear before/after pricing
    - Value-added services (installation, training, etc.) are listed separately with optional cost
    - All supplier-specific offerings appear in a dedicated "Additional Offerings" section in the comparison view
    - Buyers can filter or sort by specific attributes (e.g., "show only quotes with ISO certification")

---

## PortiQ AI Recommendation Display

The PortiQ conversation-first interface presents quote comparisons and AI recommendations through an interactive, conversational experience. This section defines the UX patterns for displaying AI-generated procurement recommendations.

### Recommendation Card in Conversation

When quotes are ready for comparison, PortiQ presents a recommendation card:

```
┌─────────────────────────────────────────────────────────────────┐
│                   AI Recommendation Display                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ╭─────────────────────────────────────────────────────────╮   │
│  │ PortiQ                                                    │   │
│  │                                                           │   │
│  │ I've analyzed all 4 quotes for MV Pacific Star. Here's   │   │
│  │ my recommendation:                                        │   │
│  │                                                           │   │
│  │ ┌─────────────────────────────────────────────────────┐  │   │
│  │ │ ★ RECOMMENDED                          97% confident │  │   │
│  │ │                                                      │  │   │
│  │ │ Ocean Supplies Pte Ltd                               │  │   │
│  │ │                                                      │  │   │
│  │ │ Total: $12,450        TCO Score: 94.2               │  │   │
│  │ │ Lead Time: 5 days     Quality: ★★★★★              │  │   │
│  │ │                                                      │  │   │
│  │ │ Why this supplier?                                   │  │   │
│  │ │ • Best price-to-quality ratio                       │  │   │
│  │ │ • 98% on-time delivery history                      │  │   │
│  │ │ • Full catalog match (all 47 items)                 │  │   │
│  │ │                                                      │  │   │
│  │ │ [Award to Ocean Supplies]  [See All Quotes]         │  │   │
│  │ └─────────────────────────────────────────────────────┘  │   │
│  │                                                           │   │
│  │ 💡 Pro tip: You could save 3% more by splitting the     │   │
│  │    order. Want me to show you the optimal split?        │   │
│  │                                                           │   │
│  │    [Yes, show split option]  [No, keep single supplier] │   │
│  ╰─────────────────────────────────────────────────────────╯   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Recommendation Card Component

```tsx
// components/recommendation/AIRecommendationCard.tsx
interface AIRecommendationCardProps {
  recommendation: QuoteRecommendation;
  onAward: () => void;
  onViewAll: () => void;
  onShowSplit?: () => void;
}

export function AIRecommendationCard({
  recommendation,
  onAward,
  onViewAll,
  onShowSplit,
}: AIRecommendationCardProps) {
  return (
    <div className="rounded-lg border-2 border-primary bg-primary/5 p-4 space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <StarIcon className="h-5 w-5 text-primary" />
          <span className="text-sm font-semibold text-primary uppercase tracking-wide">
            Recommended
          </span>
        </div>
        <ConfidenceIndicator level={recommendation.confidence} />
      </div>

      {/* Supplier info */}
      <div>
        <h3 className="text-lg font-semibold">{recommendation.supplier.name}</h3>
        <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
          <span>{recommendation.supplier.tier}</span>
          <span>•</span>
          <span>{recommendation.supplier.location}</span>
        </div>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-2 gap-4">
        <MetricBox
          label="Total Price"
          value={formatCurrency(recommendation.totalAmount)}
          subtext={recommendation.priceRank === 1 ? 'Lowest' : `#${recommendation.priceRank}`}
        />
        <MetricBox
          label="TCO Score"
          value={recommendation.tcoScore.toFixed(1)}
          subtext="out of 100"
        />
        <MetricBox
          label="Lead Time"
          value={`${recommendation.leadTimeDays} days`}
          subtext={recommendation.meetsDeadline ? '✓ Meets deadline' : '⚠ Late'}
        />
        <MetricBox
          label="Quality Rating"
          value={<StarRating value={recommendation.qualityRating} />}
          subtext={`${recommendation.orderCount} orders`}
        />
      </div>

      {/* Reasoning */}
      <div className="space-y-2">
        <p className="text-sm font-medium">Why this supplier?</p>
        <ul className="space-y-1">
          {recommendation.reasoning.map((reason, index) => (
            <li key={index} className="flex items-start gap-2 text-sm text-muted-foreground">
              <CheckIcon className="h-4 w-4 text-success mt-0.5 flex-shrink-0" />
              <span>{reason}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Actions */}
      <div className="flex gap-3 pt-2">
        <Button onClick={onAward} className="flex-1">
          Award to {recommendation.supplier.name}
        </Button>
        <Button variant="outline" onClick={onViewAll}>
          See All Quotes
        </Button>
      </div>

      {/* Split order suggestion */}
      {recommendation.splitSavings && recommendation.splitSavings > 0 && onShowSplit && (
        <div className="pt-3 border-t">
          <div className="flex items-center gap-2 text-sm">
            <LightBulbIcon className="h-4 w-4 text-warning" />
            <span>
              Pro tip: Save {formatCurrency(recommendation.splitSavings)} ({recommendation.splitSavingsPercent}%) by splitting the order
            </span>
          </div>
          <div className="flex gap-2 mt-2">
            <Button variant="outline" size="sm" onClick={onShowSplit}>
              Show split option
            </Button>
            <Button variant="ghost" size="sm">
              Keep single supplier
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
```

### Visual Comparison Chart

```tsx
// components/recommendation/QuoteComparisonChart.tsx
interface QuoteComparisonChartProps {
  quotes: RankedQuote[];
  highlightedId?: string;
}

export function QuoteComparisonChart({ quotes, highlightedId }: QuoteComparisonChartProps) {
  return (
    <div className="space-y-4">
      {/* Price comparison bar chart */}
      <div className="space-y-2">
        <h4 className="text-sm font-medium">Price Comparison</h4>
        {quotes.map((quote, index) => {
          const maxPrice = Math.max(...quotes.map(q => q.totalAmount));
          const widthPercent = (quote.totalAmount / maxPrice) * 100;
          const isHighlighted = quote.id === highlightedId;
          const isLowest = index === 0;

          return (
            <div key={quote.id} className="flex items-center gap-3">
              <div className="w-24 text-sm truncate">
                {quote.supplier.name}
              </div>
              <div className="flex-1 h-8 bg-muted rounded-full overflow-hidden relative">
                <div
                  className={cn(
                    'h-full rounded-full transition-all',
                    isHighlighted && 'bg-primary',
                    isLowest && !isHighlighted && 'bg-success',
                    !isHighlighted && !isLowest && 'bg-muted-foreground/40'
                  )}
                  style={{ width: `${widthPercent}%` }}
                />
                <span className="absolute inset-0 flex items-center px-3 text-sm font-medium">
                  {formatCurrency(quote.totalAmount)}
                </span>
              </div>
              <div className="w-16 text-right">
                <span className={cn(
                  'text-sm',
                  isLowest && 'text-success font-medium'
                )}>
                  {isLowest ? 'Lowest' : `+${formatPercent((quote.totalAmount - quotes[0].totalAmount) / quotes[0].totalAmount)}`}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* TCO Score comparison */}
      <div className="space-y-2">
        <h4 className="text-sm font-medium">TCO Score Comparison</h4>
        <div className="flex items-end justify-between h-32 gap-2">
          {quotes.map((quote) => {
            const heightPercent = quote.tcoScore;
            const isHighlighted = quote.id === highlightedId;

            return (
              <div
                key={quote.id}
                className="flex-1 flex flex-col items-center gap-1"
              >
                <span className="text-sm font-medium">{quote.tcoScore.toFixed(0)}</span>
                <div
                  className={cn(
                    'w-full rounded-t transition-all',
                    isHighlighted ? 'bg-primary' : 'bg-muted-foreground/40'
                  )}
                  style={{ height: `${heightPercent}%` }}
                />
                <span className="text-xs text-muted-foreground truncate w-full text-center">
                  {quote.supplier.name.split(' ')[0]}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
```

### Reasoning Display Component

```tsx
// components/recommendation/ReasoningBreakdown.tsx
interface ReasoningBreakdownProps {
  recommendation: QuoteRecommendation;
  showDetails: boolean;
  onToggleDetails: () => void;
}

export function ReasoningBreakdown({
  recommendation,
  showDetails,
  onToggleDetails,
}: ReasoningBreakdownProps) {
  return (
    <div className="space-y-4">
      {/* Summary reasoning */}
      <div className="p-4 bg-muted/50 rounded-lg">
        <div className="flex items-start gap-3">
          <BrainIcon className="h-5 w-5 text-primary mt-0.5" />
          <div className="space-y-2">
            <p className="font-medium">AI Analysis Summary</p>
            <p className="text-sm text-muted-foreground">
              {recommendation.summaryReasoning}
            </p>
          </div>
        </div>
      </div>

      {/* Expandable detailed breakdown */}
      <Collapsible open={showDetails} onOpenChange={onToggleDetails}>
        <CollapsibleTrigger className="flex items-center gap-2 text-sm text-primary">
          <ChevronRightIcon
            className={cn('h-4 w-4 transition-transform', showDetails && 'rotate-90')}
          />
          {showDetails ? 'Hide' : 'Show'} detailed scoring
        </CollapsibleTrigger>

        <CollapsibleContent className="pt-4 space-y-4">
          {/* Factor breakdown */}
          {recommendation.tcoBreakdown.components.map((component) => (
            <div key={component.factor} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">{FACTOR_LABELS[component.factor]}</span>
                <span>
                  {component.normalizedScore.toFixed(0)} × {component.weight}% = {component.weightedScore.toFixed(1)}
                </span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full"
                  style={{ width: `${component.normalizedScore}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Raw value: {formatComponentValue(component)}
              </p>
            </div>
          ))}

          {/* Data completeness warning */}
          {recommendation.dataCompleteness < 100 && (
            <div className="flex items-center gap-2 p-3 bg-warning/10 rounded-lg text-sm">
              <AlertTriangleIcon className="h-4 w-4 text-warning" />
              <span>
                This quote has {recommendation.dataCompleteness}% data completeness.
                Some scores are estimated.
              </span>
            </div>
          )}
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}

const FACTOR_LABELS: Record<string, string> = {
  unitPrice: 'Price',
  shippingCost: 'Shipping',
  leadTime: 'Lead Time',
  qualityScore: 'Quality',
  paymentTerms: 'Payment Terms',
  supplierRating: 'Supplier Rating',
};
```

### Interactive Comparison View in Context Panel

```tsx
// components/recommendation/ComparisonContextPanel.tsx
interface ComparisonContextPanelProps {
  rfqId: string;
  quotes: RankedQuote[];
  recommendation: QuoteRecommendation;
}

export function ComparisonContextPanel({
  rfqId,
  quotes,
  recommendation,
}: ComparisonContextPanelProps) {
  const [selectedQuoteId, setSelectedQuoteId] = useState(recommendation.quoteId);
  const [viewMode, setViewMode] = useState<'summary' | 'detail' | 'line-item'>('summary');

  return (
    <ContextPanel type="comparison">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b">
        <h3 className="font-semibold">Quote Comparison</h3>
        <SegmentedControl
          value={viewMode}
          onChange={setViewMode}
          options={[
            { value: 'summary', label: 'Summary' },
            { value: 'detail', label: 'Detail' },
            { value: 'line-item', label: 'Line Items' },
          ]}
        />
      </div>

      {/* Quote list */}
      <div className="space-y-2 py-4">
        {quotes.map((quote, index) => (
          <QuoteListItem
            key={quote.id}
            quote={quote}
            rank={index + 1}
            isRecommended={quote.id === recommendation.quoteId}
            isSelected={quote.id === selectedQuoteId}
            onClick={() => setSelectedQuoteId(quote.id)}
          />
        ))}
      </div>

      {/* Selected quote details */}
      {viewMode === 'detail' && (
        <QuoteDetailView quoteId={selectedQuoteId} />
      )}

      {viewMode === 'line-item' && (
        <LineItemComparison rfqId={rfqId} quotes={quotes} />
      )}

      {/* Action buttons */}
      <div className="pt-4 border-t space-y-2">
        <Button className="w-full" onClick={() => awardQuote(selectedQuoteId)}>
          Award to {quotes.find(q => q.id === selectedQuoteId)?.supplier.name}
        </Button>
        <Button variant="outline" className="w-full">
          Request Revised Quotes
        </Button>
      </div>
    </ContextPanel>
  );
}

function QuoteListItem({ quote, rank, isRecommended, isSelected, onClick }: QuoteListItemProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-center gap-3 p-3 rounded-lg border text-left transition-colors',
        isSelected && 'border-primary bg-primary/5',
        !isSelected && 'hover:border-muted-foreground/50'
      )}
    >
      <span className={cn(
        'flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-sm font-medium',
        rank === 1 && 'bg-success text-success-foreground',
        rank === 2 && 'bg-primary/20 text-primary',
        rank >= 3 && 'bg-muted text-muted-foreground'
      )}>
        {rank}
      </span>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium truncate">{quote.supplier.name}</span>
          {isRecommended && (
            <StarIcon className="h-4 w-4 text-primary flex-shrink-0" />
          )}
        </div>
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <span>{formatCurrency(quote.totalAmount)}</span>
          <span>•</span>
          <span>TCO {quote.tcoScore.toFixed(0)}</span>
        </div>
      </div>

      <ChevronRightIcon className="h-4 w-4 text-muted-foreground" />
    </button>
  );
}
```

### Mobile Quote Comparison

```
┌─────────────────────────────────────────┐
│ ←  Quote Comparison                      │
│     MV Pacific Star - Engine Parts       │
├─────────────────────────────────────────┤
│                                          │
│  ★ AI Recommended                        │
│  ┌────────────────────────────────────┐ │
│  │ Ocean Supplies Pte Ltd              │ │
│  │                                      │ │
│  │ $12,450          TCO: 94.2          │ │
│  │ 5 days           ★★★★★            │ │
│  │                                      │ │
│  │ ✓ Best price-quality ratio          │ │
│  │ ✓ 98% on-time delivery              │ │
│  │                                      │ │
│  │ [Award]                    [Details] │ │
│  └────────────────────────────────────┘ │
│                                          │
│  Other Quotes                            │
│  ┌────────────────────────────────────┐ │
│  │ #2  Maritime Traders    $12,890    │ │
│  │     TCO: 88.5  •  7 days  •  ★★★★  │ │
│  └────────────────────────────────────┘ │
│  ┌────────────────────────────────────┐ │
│  │ #3  Port Supplies Co    $13,200    │ │
│  │     TCO: 82.1  •  4 days  •  ★★★   │ │
│  └────────────────────────────────────┘ │
│  ┌────────────────────────────────────┐ │
│  │ #4  Global Marine       $14,100    │ │
│  │     TCO: 76.8  •  10 days •  ★★★★  │ │
│  └────────────────────────────────────┘ │
│                                          │
├─────────────────────────────────────────┤
│                                          │
│  [Compare Side-by-Side]     🎤          │
│                                          │
│  "Award to Ocean Supplies"               │
│                                          │
└─────────────────────────────────────────┘
```

### Voice Commands for Quote Comparison

```typescript
const COMPARISON_VOICE_COMMANDS = {
  'award': (supplier?: string) => awardToSupplier(supplier),
  'award to': (supplier: string) => awardToSupplier(supplier),
  'show details': () => showQuoteDetails(),
  'compare': () => showSideBySide(),
  'show split': () => showSplitOption(),
  'next quote': () => selectNextQuote(),
  'previous quote': () => selectPreviousQuote(),
  'why this': () => showReasoning(),
};
```

---

## References
- [Total Cost of Ownership Models](https://www.cips.org/knowledge/procurement-topics-and-skills/strategy-policy/total-cost-of-ownership/)
- [Multi-Criteria Decision Analysis](https://en.wikipedia.org/wiki/Multiple-criteria_decision_analysis)
- [Procurement Best Practices](https://www.procurement-academy.com/)
- [ADR-UI-013: PortiQ Buyer Experience](../ui/ADR-UI-013-portiq-buyer-experience.md)
- [ADR-UI-009: Design System (ActionCard, ConfidenceIndicator)](../ui/ADR-UI-009-design-system-theming.md)
