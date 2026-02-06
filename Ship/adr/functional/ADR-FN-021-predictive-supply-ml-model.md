# ADR-FN-021: Predictive Supply ML Model

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

Predictive supply models can anticipate vessel provisioning needs before requisitions are submitted, enabling proactive supply chain operations.

### Business Context
By combining vessel data (type, size, crew, voyage patterns) with historical purchase behavior, the platform can:
- Generate preliminary requisition lists before ships request supplies
- Pre-position inventory at likely delivery ports
- Provide suppliers with demand forecasts
- Reduce last-minute ordering and pricing

This transforms reactive chandlery operations into proactive supply preparation, creating competitive advantage and operational efficiency.

### Technical Context
- Vessel tracking data from AIS/PCS1x (ADR-FN-019, ADR-FN-020)
- Historical order data in PostgreSQL
- Product catalog with IMPA codes (ADR-FN-001, ADR-FN-002)
- pgvector for embeddings (ADR-NF-002)
- Python ML ecosystem (scikit-learn, XGBoost) or similar

### Assumptions
- Historical order data will accumulate over time
- Vessel characteristics correlate with supply needs
- Voyage patterns indicate resupply triggers
- Cold start addressable with industry heuristics

---

## Decision Drivers

- Prediction accuracy for supply needs
- Cold start handling for new vessels/customers
- Computational efficiency for real-time use
- Explainability for procurement teams
- Continuous learning from feedback
- Integration with existing architecture

---

## Considered Options

### Option 1: Rule-Based Heuristics
**Description:** Expert-defined rules based on vessel type, crew size, and voyage duration.

**Pros:**
- Immediate implementation
- Fully explainable
- No training data required
- Easy to maintain

**Cons:**
- Limited accuracy
- Doesn't learn from data
- Can't capture complex patterns

### Option 2: Traditional ML (Gradient Boosting)
**Description:** XGBoost/LightGBM models trained on historical orders.

**Pros:**
- High accuracy with structured data
- Feature importance for explainability
- Fast inference
- Well-understood techniques

**Cons:**
- Requires training data
- Manual feature engineering
- Periodic retraining needed

### Option 3: Deep Learning (LSTM/Transformer)
**Description:** Neural networks for sequence modeling of order patterns.

**Pros:**
- Captures temporal patterns
- Can learn complex relationships
- State-of-the-art for sequences

**Cons:**
- Requires large training data
- Black box predictions
- Higher compute requirements
- Overkill for initial dataset

### Option 4: Hybrid Approach
**Description:** Rule-based foundation with ML enhancement as data grows.

**Pros:**
- Immediate value with rules
- ML improves over time
- Graceful capability growth
- Explainable baseline

**Cons:**
- Two systems to maintain
- Transition complexity

---

## Decision

**Chosen Option:** Hybrid Approach (Rules + Gradient Boosting)

We will implement rule-based heuristics for immediate value, enhanced by XGBoost models as historical data accumulates, with a unified prediction interface.

### Rationale
The hybrid approach provides immediate value through industry knowledge codified in rules, while building toward data-driven predictions as order history grows. XGBoost offers excellent performance on tabular data with interpretable feature importance. The unified interface allows seamless transition between approaches.

---

## Consequences

### Positive
- Immediate predictive capabilities
- Continuous improvement with data
- Explainable predictions
- Efficient inference
- Cold start handling

### Negative
- Rule maintenance until ML takes over
- **Mitigation:** Rules remain as fallback, gradually reduce reliance
- Two prediction approaches to integrate
- **Mitigation:** Unified interface, gradual weighting shift

### Risks
- Poor predictions erode trust: Confidence scores, human review
- ML model drift: Monitoring, periodic retraining
- Cold start inaccuracy: Conservative estimates, rule-based defaults

---

## Implementation Notes

### Prediction Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Predictive Supply Pipeline                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Feature Engineering                       │    │
│  │                                                              │    │
│  │   Vessel Features  │  Voyage Features  │  Historical Data   │    │
│  │   - Type, Size     │  - Route, Duration │  - Past Orders    │    │
│  │   - Crew Size      │  - Days at Sea     │  - Frequency      │    │
│  │   - Age            │  - Last Resupply   │  - Quantities     │    │
│  │                                                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                            │                                         │
│              ┌─────────────┴─────────────┐                          │
│              │                           │                          │
│  ┌───────────▼───────────┐   ┌──────────▼────────────┐             │
│  │   Rule-Based Engine   │   │    XGBoost Models     │             │
│  │                       │   │                       │             │
│  │  - Industry heuristics│   │  - Category models   │             │
│  │  - Cold start rules   │   │  - Quantity models   │             │
│  │  - Safety minimums    │   │  - Timing models     │             │
│  │                       │   │                       │             │
│  └───────────┬───────────┘   └──────────┬────────────┘             │
│              │                           │                          │
│              └─────────────┬─────────────┘                          │
│                            │                                         │
│                 ┌──────────▼──────────┐                             │
│                 │   Ensemble/Blend    │                             │
│                 │   (weighted by      │                             │
│                 │    data maturity)   │                             │
│                 └──────────┬──────────┘                             │
│                            │                                         │
│                 ┌──────────▼──────────┐                             │
│                 │   Prediction Output │                             │
│                 │   - Product list    │                             │
│                 │   - Quantities      │                             │
│                 │   - Confidence      │                             │
│                 └─────────────────────┘                             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Feature Definitions

```typescript
// prediction/models/features.model.ts
export interface VesselFeatures {
  // Static features
  vesselType: VesselType;
  grossTonnage: number;
  deadweight: number;
  yearBuilt: number;
  flagState: string;
  crewSize: number;

  // Derived features
  vesselAge: number;
  sizeCategory: 'SMALL' | 'MEDIUM' | 'LARGE' | 'VLCC';
}

export interface VoyageFeatures {
  routeType: 'COASTAL' | 'SHORT_SEA' | 'DEEP_SEA';
  currentVoyageDays: number;
  estimatedRemainingDays: number;
  daysSinceLastResupply: number;
  lastResupplyPort: string;
  destinationPort: string;
  seasonalFactor: number;  // Weather/seasonal adjustments
}

export interface HistoricalFeatures {
  orderCount: number;
  avgOrderValue: number;
  avgOrderFrequencyDays: number;
  topCategories: string[];
  lastOrderDate: Date;
  daysSinceLastOrder: number;
  preferredSuppliers: string[];

  // Per-category historical
  categoryHistory: Map<string, CategoryHistory>;
}

export interface CategoryHistory {
  categoryCode: string;
  totalQuantity: number;
  avgQuantityPerOrder: number;
  orderFrequency: number;
  lastOrderQuantity: number;
  lastOrderDate: Date;
}

export enum VesselType {
  BULK_CARRIER = 'BULK_CARRIER',
  CONTAINER = 'CONTAINER',
  TANKER = 'TANKER',
  CHEMICAL_TANKER = 'CHEMICAL_TANKER',
  LNG_CARRIER = 'LNG_CARRIER',
  GENERAL_CARGO = 'GENERAL_CARGO',
  PASSENGER = 'PASSENGER',
  RO_RO = 'RO_RO',
  OFFSHORE = 'OFFSHORE',
  TUG = 'TUG'
}
```

### Rule-Based Engine

```typescript
// prediction/engines/rule-based.engine.ts
@Injectable()
export class RuleBasedEngine {
  // Industry standard consumption rates (per person per day)
  private readonly CONSUMPTION_RATES: Record<string, ConsumptionRate> = {
    '00': { // Provisions
      baseRate: 3.5,  // kg per person per day
      unit: 'KG',
      minDays: 7,
      bufferFactor: 1.2
    },
    '55': { // Cleaning chemicals
      baseRate: 0.1,
      unit: 'L',
      minDays: 30,
      bufferFactor: 1.1
    },
    '31': { // Protective gear
      baseRate: 0.02,
      unit: 'PIECE',
      minDays: 90,
      bufferFactor: 1.3
    }
    // ... additional categories
  };

  // Vessel type multipliers
  private readonly VESSEL_MULTIPLIERS: Record<VesselType, CategoryMultipliers> = {
    [VesselType.TANKER]: {
      '31': 1.5,  // More safety equipment
      '33': 1.5,  // More safety equipment
      '45': 1.3   // More petroleum products
    },
    [VesselType.PASSENGER]: {
      '00': 2.5,  // More provisions
      '17': 2.0,  // More tableware
      '55': 1.5   // More cleaning
    },
    [VesselType.BULK_CARRIER]: {
      '25': 1.3,  // More paint (cargo holds)
      '61': 1.2   // More hand tools
    }
    // ... additional vessel types
  };

  predict(
    features: PredictionFeatures
  ): RuleBasedPrediction {
    const predictions: ProductPrediction[] = [];

    // Calculate days until likely resupply
    const daysUntilResupply = this.estimateDaysUntilResupply(features);

    // For each category, calculate expected need
    for (const [category, rate] of Object.entries(this.CONSUMPTION_RATES)) {
      const multiplier = this.getMultiplier(features.vessel.vesselType, category);

      const dailyConsumption = rate.baseRate *
        features.vessel.crewSize *
        multiplier;

      const daysToSupply = Math.max(
        daysUntilResupply + rate.minDays,
        rate.minDays * 2
      );

      const quantity = dailyConsumption * daysToSupply * rate.bufferFactor;

      // Get common products in this category
      const products = this.getTopProducts(category, features);

      for (const product of products) {
        predictions.push({
          impaCode: product.impaCode,
          productName: product.name,
          quantity: Math.ceil(quantity * product.typicalShare),
          unit: rate.unit,
          confidence: 0.6,  // Rule-based confidence
          source: 'RULE_BASED',
          rationale: `Based on ${features.vessel.crewSize} crew, ` +
            `${daysToSupply} days supply, ${features.vessel.vesselType} vessel`
        });
      }
    }

    return {
      predictions,
      nextResupplyEstimate: new Date(Date.now() + daysUntilResupply * 86400000),
      confidence: 0.6
    };
  }

  private estimateDaysUntilResupply(features: PredictionFeatures): number {
    // Typical resupply intervals by voyage type
    const baseIntervals = {
      'COASTAL': 7,
      'SHORT_SEA': 14,
      'DEEP_SEA': 30
    };

    let days = baseIntervals[features.voyage.routeType];

    // Adjust for days since last resupply
    if (features.voyage.daysSinceLastResupply > 0) {
      const remaining = days - features.voyage.daysSinceLastResupply;
      days = Math.max(remaining, 3);  // Minimum 3 days
    }

    return days;
  }
}
```

### XGBoost Model Service

```typescript
// prediction/engines/ml-model.engine.ts
@Injectable()
export class MlModelEngine {
  private models: Map<string, any>;  // Category-specific models
  private featureProcessor: FeatureProcessor;

  constructor(
    private readonly modelRepository: ModelRepository,
    private readonly configService: ConfigService
  ) {}

  async initialize(): Promise<void> {
    // Load trained models
    const modelIds = await this.modelRepository.getActiveModels();

    for (const modelId of modelIds) {
      const model = await this.loadModel(modelId);
      this.models.set(model.category, model);
    }
  }

  async predict(features: PredictionFeatures): Promise<MlPrediction> {
    const predictions: ProductPrediction[] = [];

    // Process features into model input format
    const featureVector = this.featureProcessor.process(features);

    for (const [category, model] of this.models) {
      // Predict probability of needing this category
      const needProbability = await this.predictCategoryNeed(
        model.needModel,
        featureVector
      );

      if (needProbability > 0.3) {  // Threshold for including category
        // Predict quantity for category
        const quantity = await this.predictQuantity(
          model.quantityModel,
          featureVector
        );

        // Get top products in category
        const products = await this.predictProducts(
          model.productModel,
          featureVector,
          category
        );

        for (const product of products) {
          predictions.push({
            impaCode: product.impaCode,
            productName: product.name,
            quantity: Math.ceil(quantity * product.share),
            unit: product.unit,
            confidence: needProbability * product.confidence,
            source: 'ML_MODEL',
            rationale: this.generateRationale(model, featureVector)
          });
        }
      }
    }

    return {
      predictions,
      confidence: this.calculateOverallConfidence(predictions),
      modelVersion: this.getModelVersion()
    };
  }

  private generateRationale(model: any, features: number[]): string {
    // Get feature importance
    const importance = model.getFeatureImportance();
    const topFeatures = importance
      .map((imp, idx) => ({ name: FEATURE_NAMES[idx], importance: imp }))
      .sort((a, b) => b.importance - a.importance)
      .slice(0, 3);

    return `Key factors: ${topFeatures.map(f => f.name).join(', ')}`;
  }
}
```

### Ensemble Predictor

```typescript
// prediction/services/prediction.service.ts
@Injectable()
export class PredictionService {
  constructor(
    private readonly ruleEngine: RuleBasedEngine,
    private readonly mlEngine: MlModelEngine,
    private readonly featureService: FeatureService,
    private readonly historyRepository: OrderHistoryRepository
  ) {}

  async predictSupplyNeeds(
    vesselId: string,
    options: PredictionOptions = {}
  ): Promise<SupplyPrediction> {
    // Gather features
    const features = await this.featureService.getFeatures(vesselId);

    // Get data maturity metrics
    const dataMaturity = await this.assessDataMaturity(vesselId);

    // Get predictions from both engines
    const rulePrediction = this.ruleEngine.predict(features);
    const mlPrediction = dataMaturity.sufficient
      ? await this.mlEngine.predict(features)
      : null;

    // Blend predictions based on data maturity
    const blended = this.blendPredictions(
      rulePrediction,
      mlPrediction,
      dataMaturity
    );

    // Apply business rules and constraints
    const constrained = this.applyConstraints(blended, options);

    // Store prediction for feedback loop
    await this.storePrediction(vesselId, constrained);

    return constrained;
  }

  private async assessDataMaturity(vesselId: string): Promise<DataMaturity> {
    const history = await this.historyRepository.getVesselHistory(vesselId);

    return {
      sufficient: history.orderCount >= 5,
      orderCount: history.orderCount,
      historyMonths: history.monthsOfData,
      confidenceBoost: Math.min(history.orderCount / 20, 0.4)
    };
  }

  private blendPredictions(
    rulePrediction: RuleBasedPrediction,
    mlPrediction: MlPrediction | null,
    dataMaturity: DataMaturity
  ): BlendedPrediction {
    if (!mlPrediction) {
      return {
        predictions: rulePrediction.predictions,
        confidence: rulePrediction.confidence,
        sources: ['RULE_BASED']
      };
    }

    // Weight ML more heavily as data matures
    const mlWeight = 0.3 + dataMaturity.confidenceBoost;
    const ruleWeight = 1 - mlWeight;

    const blendedProducts = new Map<string, ProductPrediction>();

    // Add rule predictions
    for (const pred of rulePrediction.predictions) {
      blendedProducts.set(pred.impaCode, {
        ...pred,
        quantity: pred.quantity * ruleWeight,
        confidence: pred.confidence * ruleWeight
      });
    }

    // Blend ML predictions
    for (const pred of mlPrediction.predictions) {
      const existing = blendedProducts.get(pred.impaCode);

      if (existing) {
        existing.quantity += pred.quantity * mlWeight;
        existing.confidence = Math.max(
          existing.confidence,
          pred.confidence * mlWeight + dataMaturity.confidenceBoost
        );
        existing.source = 'BLENDED';
      } else {
        blendedProducts.set(pred.impaCode, {
          ...pred,
          quantity: pred.quantity * mlWeight,
          confidence: pred.confidence * mlWeight
        });
      }
    }

    return {
      predictions: Array.from(blendedProducts.values())
        .map(p => ({ ...p, quantity: Math.ceil(p.quantity) }))
        .filter(p => p.quantity > 0),
      confidence: mlPrediction.confidence * mlWeight + rulePrediction.confidence * ruleWeight,
      sources: ['RULE_BASED', 'ML_MODEL']
    };
  }

  async recordOutcome(
    predictionId: string,
    actualOrder: Order
  ): Promise<void> {
    // Record for model feedback/retraining
    const prediction = await this.predictionRepository.findById(predictionId);

    const accuracy = this.calculateAccuracy(prediction, actualOrder);

    await this.feedbackRepository.create({
      predictionId,
      orderId: actualOrder.id,
      predictedItems: prediction.predictions.length,
      actualItems: actualOrder.lineItems.length,
      overlapRate: accuracy.itemOverlap,
      quantityAccuracy: accuracy.quantityAccuracy,
      recordedAt: new Date()
    });

    // Trigger retraining if enough feedback
    await this.checkRetrainingTrigger();
  }
}
```

### Dependencies
- ADR-FN-019: AIS Data Integration
- ADR-FN-020: India Port Integration (PCS1x)
- ADR-FN-002: Product Master Data Model
- ADR-NF-002: Vector Search with pgvector

### Migration Strategy
1. Implement feature engineering pipeline
2. Deploy rule-based engine
3. Collect prediction feedback data
4. Train initial XGBoost models (after 6 months data)
5. Implement blending logic
6. Create prediction API and UI
7. Set up model monitoring and retraining pipeline

---

## Training Data and Features

### Training Data Sources

| Data Source | Fields | Volume | Update Frequency |
|-------------|--------|--------|------------------|
| Historical orders | items, quantities, timing | 100K+ orders | Real-time |
| Vessel profiles | type, size, route patterns | 5K vessels | Weekly |
| Port call history | duration, services, patterns | 50K port calls | Daily |
| Catalog data | categories, consumption patterns | 50K products | On change |
| Seasonal factors | weather, holidays, trade cycles | External | Monthly |

### Feature Engineering

```python
# Feature categories and examples
FEATURE_GROUPS = {
    'vessel_features': [
        'vessel_type',           # Bulk, container, tanker
        'vessel_size_dwt',       # Deadweight tonnage
        'vessel_age_years',
        'crew_size_estimate',
        'flag_state',
        'last_drydock_months',
    ],
    'voyage_features': [
        'days_since_last_supply',
        'voyage_duration_days',
        'ports_visited_count',
        'sea_days_ratio',
        'current_cargo_type',
    ],
    'port_features': [
        'port_supply_index',     # Availability score
        'port_price_index',      # Relative pricing
        'is_regular_port',       # Historical pattern
        'port_category_coverage',
    ],
    'temporal_features': [
        'month_of_year',
        'quarter',
        'is_holiday_period',
        'days_to_festive_season',
    ],
    'historical_patterns': [
        'avg_monthly_spend',
        'category_preference_vector',  # Embedding
        'supplier_loyalty_score',
        'order_frequency',
    ]
}
```

### Target Variables

| Target | Type | Granularity | Use Case |
|--------|------|-------------|----------|
| `will_order` | Binary | Per vessel-port | Arrival prioritization |
| `order_value` | Regression | Per vessel-port | Revenue forecasting |
| `category_quantities` | Multi-output | Per category | Inventory planning |
| `timing_days` | Regression | Days before arrival | Supplier prep |

### Prediction Quality Metrics

| Metric | Target | Acceptable | Measurement |
|--------|--------|------------|-------------|
| **Order Prediction Accuracy** | >85% | >75% | Precision at threshold |
| **Value Prediction MAPE** | <20% | <30% | Mean Absolute % Error |
| **Category Recall** | >80% | >70% | Categories actually ordered |
| **Timing Error** | ±2 days | ±5 days | Avg prediction vs actual |

## Model Monitoring and Retraining

### Monitoring Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│               ML Model Health Dashboard                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Model Version: v2.3.1          Last Trained: 2025-01-15    │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  Prediction Accuracy (7-day rolling)                        │
│  ████████████████████░░░░  82%  (Target: 85%)              │
│                                                              │
│  Data Drift Score                                            │
│  ████░░░░░░░░░░░░░░░░░░░░  0.12 (Threshold: 0.25)          │
│                                                              │
│  Feature Importance Shift                                    │
│  ██████░░░░░░░░░░░░░░░░░░  Low (OK)                         │
│                                                              │
│  Predictions Today: 1,234    Feedback Collected: 892        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Drift Detection

| Drift Type | Detection Method | Threshold | Action |
|------------|------------------|-----------|--------|
| Data drift | KL divergence on features | >0.25 | Alert + investigate |
| Concept drift | Accuracy degradation | >10% drop | Trigger retraining |
| Label drift | Target distribution shift | >0.20 | Investigate data quality |

```python
# Drift monitoring job (daily)
def check_model_drift():
    # 1. Feature distribution drift
    current_features = get_recent_features(days=7)
    training_features = get_training_distribution()
    drift_score = calculate_kl_divergence(current_features, training_features)

    if drift_score > DRIFT_THRESHOLD:
        alert_team("Data drift detected", drift_score)

    # 2. Prediction accuracy drift
    recent_accuracy = calculate_accuracy(days=7)
    baseline_accuracy = get_model_baseline()

    if recent_accuracy < baseline_accuracy * 0.9:
        trigger_retraining()

    # 3. Log metrics
    log_monitoring_metrics(drift_score, recent_accuracy)
```

### Retraining Cadence

| Trigger | Frequency | Scope |
|---------|-----------|-------|
| Scheduled | Monthly | Full retrain on all data |
| Performance drop | On detection | Full retrain |
| New feature | As needed | Incremental + evaluation |
| Major data change | On event | Full retrain + A/B test |

## Prediction Surfacing and Validation

### User-Facing Predictions

| Prediction Type | Surface Location | User Action | Feedback Loop |
|-----------------|------------------|-------------|---------------|
| Pre-arrival recommendation | Fleet dashboard | Review, accept/modify | Capture modifications |
| Suggested quantities | RFQ creation | Pre-fill, adjust | Compare to final order |
| Price expectation | Quote comparison | Reference only | Compare to actual quotes |
| Timing alert | Notifications | Acknowledge | Track if acted upon |

### Prediction UI Design

```
┌─────────────────────────────────────────────────────────────┐
│  🚢 MV Pacific Star - Arriving Mumbai in 5 days             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  📊 Predicted Supply Needs (85% confidence)                 │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  Category          Predicted    Last Order    Confidence    │
│  ────────────────  ─────────    ──────────    ──────────    │
│  Provisions        $12,500      $11,200       ████████░░    │
│  Deck Stores       $4,200       $3,800        ███████░░░    │
│  Engine Spares     $2,100       $5,500        █████░░░░░    │
│  Safety Equipment  $800         $750          ████████░░    │
│                                                              │
│  [Create RFQ from Prediction]    [Adjust & Create]          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Validation Feedback Collection

```typescript
// Capture prediction feedback
interface PredictionFeedback {
  predictionId: string;
  vesselId: string;
  portCallId: string;

  // What we predicted
  predictedCategories: CategoryPrediction[];
  predictedTotal: number;

  // What actually happened
  actualOrderId?: string;
  actualCategories?: CategoryActual[];
  actualTotal?: number;

  // User actions
  userAccepted: boolean;
  userModifications: Modification[];
  feedbackTimestamp: Date;
}

// Use feedback for model improvement
async function collectFeedback(portCallId: string) {
  const prediction = await getPrediction(portCallId);
  const actualOrder = await getActualOrder(portCallId);

  const feedback: PredictionFeedback = {
    predictionId: prediction.id,
    predictedTotal: prediction.total,
    actualTotal: actualOrder?.total || 0,
    // ... calculate accuracy metrics
  };

  await feedbackRepo.save(feedback);
  await updateModelMetrics(feedback);
}
```

---

## References
- [XGBoost Documentation](https://xgboost.readthedocs.io/)
- [Demand Forecasting Best Practices](https://otexts.com/fpp3/)
- [Feature Engineering for ML](https://www.oreilly.com/library/view/feature-engineering-for/9781491953235/)
