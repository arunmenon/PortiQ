# ADR-FN-008: LLM Provider for Normalization

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Backend

---

## Context

The document AI pipeline requires an LLM to normalize extracted table data into structured product information, interpreting abbreviations, standardizing units, and preparing data for SKU matching.

### Business Context
Maritime requisitions contain abbreviated product names ("SS Bolt M10x50" → "Stainless Steel Bolt, Metric 10mm x 50mm"), inconsistent units ("doz", "dozen", "12pcs"), and domain-specific terminology. Human operators intuitively normalize this data; an LLM must replicate this interpretation accurately to enable automated catalog matching.

### Technical Context
- Input: Markdown tables from Azure Document Intelligence
- Output: Structured JSON with normalized product details
- Processing volume: ~5,000 pages/month initially
- Integration with async pipeline (ADR-FN-006)
- Need for consistent, schema-compliant output
- Both GPT-4o and Claude 3.5 achieve 97-98% accuracy on extraction benchmarks

### Assumptions
- LLM API availability is sufficient for processing needs
- Cost per extraction is acceptable ($0.01-0.02 per page)
- Structured output modes (JSON) are reliable
- Domain-specific fine-tuning is not required initially

---

## Decision Drivers

- Extraction accuracy for maritime terminology
- Structured output reliability (JSON schema adherence)
- Cost efficiency at scale
- API reliability and latency
- Context window size for large tables
- Ease of prompt engineering and iteration

---

## Considered Options

### Option 1: OpenAI GPT-4o
**Description:** OpenAI's latest multimodal model with strong structured output capabilities.

**Pros:**
- Industry-leading accuracy on extraction tasks
- Native JSON mode with schema enforcement
- Large context window (128K tokens)
- Function calling for structured output
- Extensive documentation and community
- Competitive pricing ($5/1M input, $15/1M output)

**Cons:**
- Cloud dependency on OpenAI
- Occasional API instability
- Data processed outside own infrastructure

### Option 2: Anthropic Claude 3.5 Sonnet
**Description:** Anthropic's balanced model with strong reasoning and instruction following.

**Pros:**
- Excellent instruction following
- Strong at structured data extraction
- 200K context window
- Tool use capabilities
- Competitive pricing ($3/1M input, $15/1M output)
- Strong safety properties

**Cons:**
- Slightly newer, less ecosystem tooling
- JSON mode less mature than OpenAI
- Smaller community

### Option 3: Self-Hosted Open Source (Llama 3, Mistral)
**Description:** Deploy open-source LLMs on own infrastructure.

**Pros:**
- No per-token costs after setup
- Full data control
- No external dependencies
- Customization potential

**Cons:**
- Significant infrastructure investment
- Lower accuracy than frontier models
- Operational complexity
- GPU costs may exceed API costs at our volume

### Option 4: Multi-Provider with Fallback
**Description:** Primary provider with automatic fallback to secondary on failures.

**Pros:**
- High availability
- Provider redundancy
- Can optimize cost/quality tradeoff
- A/B testing capability

**Cons:**
- Implementation complexity
- Prompt compatibility across providers
- Inconsistent behavior

---

## Decision

**Chosen Option:** OpenAI GPT-4o with Claude 3.5 Sonnet Fallback

We will use GPT-4o as the primary LLM for normalization with Claude 3.5 Sonnet as fallback, implementing a provider abstraction layer for seamless switching.

### Rationale
GPT-4o's mature JSON mode and function calling provide the most reliable structured output for our extraction needs. The 128K context window handles large requisitions. Claude 3.5 Sonnet as fallback ensures availability during OpenAI outages. Both achieve comparable accuracy (97-98%) on extraction benchmarks, making the fallback seamless from a quality perspective.

---

## Consequences

### Positive
- High extraction accuracy with structured output
- Resilient architecture with fallback provider
- Flexibility to optimize provider selection over time
- Clear abstraction for future provider additions

### Negative
- Dual provider integration complexity
- **Mitigation:** Abstract behind common interface, standardize prompts
- Data processed externally
- **Mitigation:** No PII in requisition data; review data handling policies

### Risks
- Provider API changes: Abstract prompts, version lock SDKs
- Cost increases: Monitor usage, implement caching for repeated content
- Quality degradation: A/B testing, human review sampling

---

## Implementation Notes

### Provider Abstraction

```typescript
// llm/provider.interface.ts
interface LLMProvider {
  name: string;
  extractLineItems(markdown: string, schema: JSONSchema): Promise<ExtractedLineItem[]>;
  normalizeProduct(rawText: string): Promise<NormalizedProduct>;
}

interface ExtractedLineItem {
  originalText: string;
  productName: string;
  quantity: number;
  unit: string;
  specifications: Record<string, string>;
  notes: string;
  confidence: number;
}

interface NormalizedProduct {
  name: string;
  normalizedName: string;
  category: string;
  material?: string;
  dimensions?: string;
  specifications: Record<string, any>;
}
```

### GPT-4o Implementation

```typescript
// llm/providers/openai.provider.ts
import OpenAI from 'openai';

class OpenAIProvider implements LLMProvider {
  name = 'openai-gpt4o';
  private client: OpenAI;

  constructor() {
    this.client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  }

  async extractLineItems(markdown: string, schema: JSONSchema): Promise<ExtractedLineItem[]> {
    const response = await this.client.chat.completions.create({
      model: 'gpt-4o',
      messages: [
        {
          role: 'system',
          content: EXTRACTION_SYSTEM_PROMPT
        },
        {
          role: 'user',
          content: `Extract line items from this maritime requisition table:\n\n${markdown}`
        }
      ],
      response_format: {
        type: 'json_schema',
        json_schema: {
          name: 'line_items',
          schema: schema
        }
      },
      temperature: 0.1
    });

    return JSON.parse(response.choices[0].message.content);
  }
}

const EXTRACTION_SYSTEM_PROMPT = `You are a maritime procurement specialist extracting line items from ship requisition documents.

For each line item, extract:
1. Product name (expand abbreviations: SS=Stainless Steel, GI=Galvanized Iron, etc.)
2. Quantity (numeric value)
3. Unit of measure (standardize: doz→dozen, pcs→pieces, etc.)
4. Specifications (dimensions, material, grade, etc.)
5. Any notes or special requirements

Maritime abbreviations reference:
- SS: Stainless Steel
- GI: Galvanized Iron
- MS: Mild Steel
- CI: Cast Iron
- BSP: British Standard Pipe
- NPT: National Pipe Thread
- SOLAS: Safety of Life at Sea certified

Output confidence score (0-1) based on clarity of the source text.`;
```

### Claude Fallback Implementation

```typescript
// llm/providers/anthropic.provider.ts
import Anthropic from '@anthropic-ai/sdk';

class AnthropicProvider implements LLMProvider {
  name = 'anthropic-claude35';
  private client: Anthropic;

  constructor() {
    this.client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  }

  async extractLineItems(markdown: string, schema: JSONSchema): Promise<ExtractedLineItem[]> {
    const response = await this.client.messages.create({
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 4096,
      messages: [
        {
          role: 'user',
          content: `${EXTRACTION_SYSTEM_PROMPT}\n\nExtract line items from this maritime requisition table and respond with valid JSON matching the schema:\n\n${markdown}\n\nSchema: ${JSON.stringify(schema)}`
        }
      ]
    });

    const content = response.content[0];
    if (content.type === 'text') {
      return JSON.parse(content.text);
    }
    throw new Error('Unexpected response format');
  }
}
```

### Provider Router

```typescript
// llm/provider-router.ts
class LLMProviderRouter {
  private providers: Map<string, LLMProvider>;
  private primary: string;
  private fallback: string;

  constructor() {
    this.providers = new Map([
      ['openai', new OpenAIProvider()],
      ['anthropic', new AnthropicProvider()]
    ]);
    this.primary = 'openai';
    this.fallback = 'anthropic';
  }

  async extractLineItems(markdown: string, schema: JSONSchema): Promise<ExtractedLineItem[]> {
    try {
      return await this.providers.get(this.primary)!.extractLineItems(markdown, schema);
    } catch (error) {
      console.error(`Primary provider failed: ${error.message}`);
      metrics.providerFailover.inc({ from: this.primary, to: this.fallback });

      return await this.providers.get(this.fallback)!.extractLineItems(markdown, schema);
    }
  }
}
```

### Cost Tracking

```typescript
// llm/cost-tracker.ts
const LLM_PRICING = {
  'gpt-4o': { input: 5.0, output: 15.0 }, // per 1M tokens
  'claude-3-5-sonnet': { input: 3.0, output: 15.0 }
};

class CostTracker {
  async trackUsage(provider: string, inputTokens: number, outputTokens: number): Promise<void> {
    const pricing = LLM_PRICING[provider];
    const cost = (inputTokens * pricing.input + outputTokens * pricing.output) / 1_000_000;

    await this.recordCost({
      provider,
      inputTokens,
      outputTokens,
      cost,
      timestamp: new Date()
    });

    metrics.llmCost.inc({ provider }, cost);
    metrics.llmTokens.inc({ provider, type: 'input' }, inputTokens);
    metrics.llmTokens.inc({ provider, type: 'output' }, outputTokens);
  }
}
```

### Dependencies
- ADR-FN-006: Document AI Pipeline Architecture
- ADR-FN-007: Document Parsing Service
- ADR-FN-009: Confidence-Gated Human-in-Loop
- ADR-NF-008: Async Processing (BullMQ)

### Migration Strategy
1. Implement provider abstraction interface
2. Build GPT-4o provider with structured output
3. Add Claude 3.5 Sonnet as fallback
4. Create provider router with circuit breaker
5. Implement cost tracking and monitoring
6. A/B test both providers for quality validation

---

## Operational Considerations

### Cost and Latency Budgets

#### Monthly Cost Budget

| Cost Category | MVP Budget | Scale Budget | Alert Threshold |
|---------------|------------|--------------|-----------------|
| OpenAI GPT-4o | $200/month | $1,000/month | 80% of budget |
| Anthropic Claude (fallback) | $50/month | $200/month | 80% of budget |
| Total LLM Spend | $250/month | $1,200/month | 90% of total |
| Cost per document (target) | $0.05 | $0.04 | $0.08 |
| Cost per line item (target) | $0.003 | $0.002 | $0.005 |

```typescript
// Cost budget enforcement
interface CostBudget {
  monthly: {
    total: number;
    byProvider: Record<string, number>;
  };
  perDocument: {
    target: number;
    max: number;
  };
  alerts: {
    warningPercent: 80;
    criticalPercent: 95;
  };
}

const COST_BUDGET: CostBudget = {
  monthly: {
    total: 250,  // MVP
    byProvider: {
      'openai': 200,
      'anthropic': 50
    }
  },
  perDocument: {
    target: 0.05,
    max: 0.15   // Hard cap - route to manual if exceeded
  },
  alerts: {
    warningPercent: 80,
    criticalPercent: 95
  }
};

@Injectable()
export class CostEnforcementService {
  @Cron('0 * * * *')  // Hourly
  async checkBudgetUtilization(): Promise<void> {
    const mtdSpend = await this.getMonthToDateSpend();
    const daysInMonth = new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).getDate();
    const dayOfMonth = new Date().getDate();
    const expectedSpend = (COST_BUDGET.monthly.total / daysInMonth) * dayOfMonth;
    const utilizationPercent = (mtdSpend / COST_BUDGET.monthly.total) * 100;

    if (utilizationPercent > COST_BUDGET.alerts.criticalPercent) {
      await this.alertService.sendCritical('llm_budget_critical', {
        spent: mtdSpend,
        budget: COST_BUDGET.monthly.total,
        percent: utilizationPercent
      });
      await this.enableCostSavingMode();
    }
  }

  async enableCostSavingMode(): Promise<void> {
    // Switch to smaller model for low-complexity items
    await this.configService.set('llm.costSavingMode', true);
    // Increase batching to reduce API calls
    await this.configService.set('llm.batchSize', 20);
    // Route more items to human review
    await this.configService.set('confidence.autoApproveThreshold', 0.98);
  }
}
```

#### Latency Budgets

| Operation | Target P50 | Target P95 | Max P99 | SLA Breach Action |
|-----------|------------|------------|---------|-------------------|
| Single line item extraction | 800ms | 1.5s | 3s | Log + alert if sustained |
| Batch extraction (10 items) | 2s | 4s | 8s | Reduce batch size |
| Full document (150 items) | 30s | 60s | 120s | Split into smaller batches |
| Provider health check | 200ms | 500ms | 1s | Mark provider unhealthy |

```typescript
// Latency monitoring and circuit breaker
const LATENCY_CONFIG = {
  timeoutMs: {
    single: 5000,
    batch: 15000,
    document: 120000
  },
  circuitBreaker: {
    failureThreshold: 5,        // Failures before opening
    resetTimeoutMs: 30000,      // Time before half-open
    halfOpenRequests: 3         // Requests in half-open state
  }
};

class LatencyAwareProviderRouter {
  private providerHealth: Map<string, ProviderHealth> = new Map();

  async route(request: ExtractionRequest): Promise<string> {
    const providers = ['openai', 'anthropic'];

    for (const provider of providers) {
      const health = this.providerHealth.get(provider);

      if (health?.circuitOpen && Date.now() < health.resetAt) {
        continue;  // Skip unhealthy provider
      }

      const recentLatency = await this.getRecentP95Latency(provider);
      if (recentLatency < LATENCY_CONFIG.timeoutMs.single * 0.8) {
        return provider;
      }
    }

    // All providers slow - use primary with extended timeout
    return 'openai';
  }
}
```

### Vendor Lock-in Mitigation

#### Multi-Provider Strategy

| Provider | Role | Prompt Compatibility | Switch Effort |
|----------|------|---------------------|---------------|
| OpenAI GPT-4o | Primary | Native JSON mode | Baseline |
| Anthropic Claude | Secondary/Fallback | Tool use + XML | 2-day prompt adaptation |
| Google Gemini | Tertiary (future) | Function calling | 3-day integration |
| Local Llama 3 | Emergency | Basic completion | 1-week fine-tuning |

```typescript
// Provider-agnostic prompt template
interface PromptTemplate {
  version: string;
  basePrompt: string;
  providerAdaptations: Record<string, ProviderAdaptation>;
}

interface ProviderAdaptation {
  systemPromptWrapper?: (base: string) => string;
  outputFormatInstruction: string;
  structuredOutputConfig: any;
}

const EXTRACTION_PROMPT_TEMPLATE: PromptTemplate = {
  version: '1.2.0',
  basePrompt: `You are a maritime procurement specialist extracting line items from ship requisition documents.

For each line item, extract:
1. Product name (expand abbreviations: SS=Stainless Steel, GI=Galvanized Iron, etc.)
2. Quantity (numeric value)
3. Unit of measure (standardize: doz→dozen, pcs→pieces, etc.)
4. Specifications (dimensions, material, grade, etc.)
5. Any notes or special requirements

Output confidence score (0-1) based on clarity of the source text.`,

  providerAdaptations: {
    'openai': {
      outputFormatInstruction: 'Respond with JSON matching the provided schema.',
      structuredOutputConfig: {
        response_format: { type: 'json_schema', json_schema: LINE_ITEM_SCHEMA }
      }
    },
    'anthropic': {
      systemPromptWrapper: (base) => base,
      outputFormatInstruction: `Respond with valid JSON array. Each item must have: originalText, productName, quantity, unit, specifications, notes, confidence.`,
      structuredOutputConfig: {}  // Claude uses prompt-based JSON
    },
    'local-llama': {
      outputFormatInstruction: `Output ONLY a JSON array, no explanation. Format: [{"originalText": "...", "productName": "...", ...}]`,
      structuredOutputConfig: {}
    }
  }
};

// Prompt compilation per provider
function compilePrompt(template: PromptTemplate, provider: string, content: string): CompiledPrompt {
  const adaptation = template.providerAdaptations[provider];
  const systemPrompt = adaptation.systemPromptWrapper
    ? adaptation.systemPromptWrapper(template.basePrompt)
    : template.basePrompt;

  return {
    system: systemPrompt,
    user: `${adaptation.outputFormatInstruction}\n\nContent to extract:\n${content}`,
    config: adaptation.structuredOutputConfig
  };
}
```

### Evaluation and Guardrails for Output Consistency

#### Output Validation Rules

```typescript
// Output validation schema
const OUTPUT_VALIDATION_RULES = {
  lineItem: {
    required: ['productName', 'quantity', 'unit', 'confidence'],
    types: {
      productName: 'string',
      quantity: 'number',
      unit: 'string',
      confidence: 'number',
      specifications: 'object'
    },
    constraints: {
      productName: { minLength: 3, maxLength: 500 },
      quantity: { min: 0, max: 1000000 },
      confidence: { min: 0, max: 1 },
      unit: { enum: STANDARD_UNITS }
    }
  }
};

// Guardrail implementation
class OutputGuardrails {
  validate(output: any): ValidationResult {
    const errors: ValidationError[] = [];

    // Schema validation
    if (!Array.isArray(output)) {
      return { valid: false, errors: [{ type: 'schema', message: 'Output must be array' }] };
    }

    for (const [idx, item] of output.entries()) {
      // Required fields
      for (const field of OUTPUT_VALIDATION_RULES.lineItem.required) {
        if (item[field] === undefined || item[field] === null) {
          errors.push({ type: 'missing_field', index: idx, field });
        }
      }

      // Type validation
      for (const [field, expectedType] of Object.entries(OUTPUT_VALIDATION_RULES.lineItem.types)) {
        if (item[field] !== undefined && typeof item[field] !== expectedType) {
          errors.push({ type: 'type_mismatch', index: idx, field, expected: expectedType });
        }
      }

      // Constraint validation
      if (item.quantity < 0) {
        errors.push({ type: 'constraint', index: idx, field: 'quantity', message: 'Quantity cannot be negative' });
      }

      // Semantic validation
      if (item.productName && item.productName.length < 3) {
        errors.push({ type: 'semantic', index: idx, field: 'productName', message: 'Product name too short' });
      }
    }

    return { valid: errors.length === 0, errors };
  }

  // Consistency check across providers
  async checkConsistency(
    openaiOutput: any[],
    claudeOutput: any[]
  ): Promise<ConsistencyReport> {
    const discrepancies: Discrepancy[] = [];

    for (let i = 0; i < Math.min(openaiOutput.length, claudeOutput.length); i++) {
      const oai = openaiOutput[i];
      const claude = claudeOutput[i];

      if (oai.quantity !== claude.quantity) {
        discrepancies.push({
          index: i,
          field: 'quantity',
          openai: oai.quantity,
          anthropic: claude.quantity,
          severity: Math.abs(oai.quantity - claude.quantity) / oai.quantity > 0.1 ? 'high' : 'low'
        });
      }

      // Fuzzy match on product name
      const nameSimilarity = this.calculateSimilarity(oai.productName, claude.productName);
      if (nameSimilarity < 0.85) {
        discrepancies.push({
          index: i,
          field: 'productName',
          openai: oai.productName,
          anthropic: claude.productName,
          severity: 'medium'
        });
      }
    }

    return {
      totalItems: openaiOutput.length,
      discrepancies,
      consistencyScore: 1 - (discrepancies.length / openaiOutput.length)
    };
  }
}
```

#### Prompt Versioning

```typescript
// Prompt version management
interface PromptVersion {
  id: string;
  version: string;
  prompt: string;
  activeFrom: Date;
  activeTo?: Date;
  metrics: {
    accuracy: number;
    consistency: number;
    avgConfidence: number;
  };
}

// A/B testing for prompt improvements
@Injectable()
export class PromptExperimentService {
  async selectPromptVersion(documentId: string): Promise<PromptVersion> {
    const activeExperiment = await this.getActiveExperiment();

    if (!activeExperiment) {
      return this.getCurrentProduction();
    }

    // Deterministic assignment based on document ID
    const bucket = this.hashToBucket(documentId, 100);

    if (bucket < activeExperiment.treatmentPercent) {
      return activeExperiment.treatmentPrompt;
    }
    return activeExperiment.controlPrompt;
  }

  async recordOutcome(
    documentId: string,
    promptVersion: string,
    metrics: ExtractionMetrics
  ): Promise<void> {
    await this.experimentMetricsRepository.insert({
      documentId,
      promptVersion,
      accuracy: metrics.accuracy,
      confidence: metrics.avgConfidence,
      reviewRequired: metrics.reviewRequired,
      timestamp: new Date()
    });
  }
}
```

### Open Questions

- **Q:** What is the non-LLM fallback during outages or quota exhaustion?
  - **A:** The non-LLM fallback strategy provides degraded but functional service:

  **Fallback Hierarchy:**
  | Level | Trigger | Fallback Action | Capability |
  |-------|---------|-----------------|------------|
  | 1 | Primary provider timeout | Switch to secondary LLM provider | Full capability |
  | 2 | All LLM providers down | Rule-based extraction | 60% accuracy, common patterns only |
  | 3 | Rule-based insufficient | Template matching | 40% accuracy, known formats only |
  | 4 | All automated fails | Queue for manual processing | 100% accuracy, high latency |

  **Rule-Based Extraction (Non-LLM):**
  ```typescript
  // Deterministic extraction for common patterns
  const EXTRACTION_RULES = {
    quantityPatterns: [
      /(\d+)\s*(pcs?|pieces?|units?|ea|each)/i,
      /(\d+)\s*(doz(?:en)?)/i,
      /(\d+)\s*(sets?|pairs?)/i,
      /qty[:\s]*(\d+)/i
    ],
    unitMappings: {
      'pc': 'pieces', 'pcs': 'pieces', 'ea': 'each',
      'doz': 'dozen', 'pr': 'pair', 'set': 'set'
    },
    abbreviationExpansions: {
      'SS': 'Stainless Steel', 'GI': 'Galvanized Iron',
      'MS': 'Mild Steel', 'CI': 'Cast Iron',
      'BSP': 'British Standard Pipe', 'NPT': 'National Pipe Thread'
    }
  };

  class RuleBasedExtractor {
    extract(row: TableRow, headers: string[]): PartialLineItem {
      const item: PartialLineItem = { confidence: 0.5, extractionMethod: 'rule-based' };

      // Extract quantity using patterns
      for (const cell of row.cells) {
        for (const pattern of EXTRACTION_RULES.quantityPatterns) {
          const match = cell.match(pattern);
          if (match) {
            item.quantity = parseInt(match[1]);
            item.unit = EXTRACTION_RULES.unitMappings[match[2].toLowerCase()] || match[2];
            break;
          }
        }
      }

      // Expand abbreviations in product name
      const productCell = row.cells[this.findProductColumn(headers)];
      item.productName = this.expandAbbreviations(productCell);

      // Lower confidence for rule-based
      item.confidence = item.quantity ? 0.6 : 0.4;
      item.requiresReview = true;

      return item;
    }

    private expandAbbreviations(text: string): string {
      let expanded = text;
      for (const [abbr, full] of Object.entries(EXTRACTION_RULES.abbreviationExpansions)) {
        expanded = expanded.replace(new RegExp(`\\b${abbr}\\b`, 'gi'), full);
      }
      return expanded;
    }
  }
  ```

  **Fallback Mode Monitoring:**
  ```typescript
  // Track time spent in fallback modes
  @Injectable()
  export class FallbackMonitor {
    @OnEvent('extraction.fallback_used')
    async recordFallback(event: FallbackEvent): Promise<void> {
      metrics.fallbackUsage.inc({ level: event.level, reason: event.reason });

      if (event.level >= 3) {
        // Rule-based or manual fallback - alert operations
        await this.alertService.sendWarning('extraction_fallback_active', {
          level: event.level,
          documentsAffected: await this.countAffectedDocuments(),
          estimatedRecovery: event.providerStatus.estimatedRecovery
        });
      }
    }

    @Cron('*/5 * * * *')
    async checkFallbackDuration(): Promise<void> {
      const fallbackStart = await this.getFallbackStartTime();
      if (fallbackStart) {
        const duration = Date.now() - fallbackStart.getTime();
        if (duration > 3600000) {  // 1 hour in fallback
          await this.alertService.sendCritical('extended_fallback_mode', {
            durationMinutes: Math.round(duration / 60000),
            queueDepth: await this.getManualQueueDepth()
          });
        }
      }
    }
  }
  ```

---

## References
- [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
- [Anthropic Claude API](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)
- [LLM Extraction Benchmarks](https://github.com/run-llama/llama_index)
