# ADR-UI-014: PortiQ Supplier Experience Architecture

**Status:** Accepted
**Date:** 2026-02-06
**Technical Area:** Frontend
**Supersedes:** ADR-UI-005

---

## Context

The PortiQ UX Design Specification introduces an **AI-assisted quoting paradigm** for suppliers that dramatically reduces the time and effort required to respond to RFQs. Rather than manually entering prices and availability for each line item, suppliers receive AI-prefilled quotes based on their inventory and pricing history.

### Business Context

The traditional supplier dashboard (ADR-UI-005) required suppliers to:
- Manually check each RFQ for relevance
- Enter prices for every line item
- Calculate competitive pricing without guidance
- Track opportunities across multiple screens

The PortiQ approach enables:
- **Time to quote: < 3 minutes** (vs. ~15 minutes traditional)
- **Win probability visibility** before submission
- **AI-optimized pricing** with multiple strategy options
- **Inventory-aware matching** highlighting fulfillable RFQs

### Technical Context

- Next.js 14 App Router (ADR-UI-001)
- shadcn/ui with AI-specific components (ADR-UI-002, UI-009)
- React Query for AI-assisted quoting state (ADR-UI-003)
- Real-time notifications for new RFQs (ADR-UI-012, UI-016)
- WebSocket for live inventory matching

### Assumptions

- Suppliers prefer AI assistance over manual pricing
- Inventory data is reliably synchronized
- Win probability calculations provide value
- Mobile access needed for field sales teams

---

## Decision Drivers

- Reduce quote submission time below 3 minutes
- Increase quote submission rate (more RFQs responded to)
- Improve win rate through AI-guided pricing
- Surface high-match opportunities proactively
- Support mobile quote submission

---

## Decision

We will build the supplier experience as an **AI-assisted quoting platform** with PortiQ providing inventory matching, price recommendations, and win probability insights. The interface prioritizes high-value opportunities and pre-fills quotes to minimize manual entry.

---

## Implementation Notes

### Supplier Home Wireframe

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🚢 PortiQ Supplier                              [🔔 5] [Ocean Supply ▼]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Good morning, Ocean Supply Team                                           │
│                                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │ 🎤  Ask PortiQ anything...                              ⌘K       │    │
│   │                                                                   │    │
│   │   Try: "Show me high-match opportunities"                        │    │
│   │        "Quote RFQ-2024-0158 with aggressive pricing"             │    │
│   │        "What's my win rate this month?"                          │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │ 🎯 High-Match Opportunities                           [View All →] │  │
│   │                                                                     │  │
│   │ ┌─────────────────────────────────────────────────────────────────┐│  │
│   │ │ 🔥 RFQ-2024-0158: MV Pacific Star - Mumbai Provisions          ││  │
│   │ │                                                                 ││  │
│   │ │ Inventory Match: [████████████████░░░░] 95%                    ││  │
│   │ │ Deadline: 2 hours remaining                                    ││  │
│   │ │ Est. Value: $12,400 - $15,200                                  ││  │
│   │ │                                                                 ││  │
│   │ │ 💡 PortiQ: "You have 62/65 items in stock. High win potential" ││  │
│   │ │                                                                 ││  │
│   │ │ [Quick Quote] [View Details]                                   ││  │
│   │ └─────────────────────────────────────────────────────────────────┘│  │
│   │                                                                     │  │
│   │ ┌─────────────────────────────────────────────────────────────────┐│  │
│   │ │ RFQ-2024-0159: MV Ocean Voyager - Chennai Deck Supplies        ││  │
│   │ │                                                                 ││  │
│   │ │ Inventory Match: [████████████░░░░░░░░] 78%                    ││  │
│   │ │ Deadline: 18 hours remaining                                   ││  │
│   │ │ Est. Value: $8,200 - $9,500                                    ││  │
│   │ │                                                                 ││  │
│   │ │ [Quick Quote] [View Details]                                   ││  │
│   │ └─────────────────────────────────────────────────────────────────┘│  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│   ┌─────────────────────────────┐  ┌─────────────────────────────────────┐ │
│   │ 📊 This Month               │  │ 📦 Active Orders                    │ │
│   │                             │  │                                     │ │
│   │ Quotes Submitted: 24        │  │ ORD-2024-0892  Shipping today      │ │
│   │ Won: 8 (33% win rate)       │  │ ORD-2024-0888  Preparing           │ │
│   │ Revenue: $145,230           │  │ ORD-2024-0885  Delivered ✓         │ │
│   │                             │  │                                     │ │
│   │ [View Analytics]            │  │ [View All Orders →]                │ │
│   └─────────────────────────────┘  └─────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Opportunities List with Inventory Match

```typescript
// components/supplier/opportunity-card.tsx
interface OpportunityCardProps {
  rfq: RfqOpportunity;
  onQuickQuote: () => void;
  onViewDetails: () => void;
}

interface RfqOpportunity {
  id: string;
  title: string;
  buyerName: string;
  vesselName: string;
  port: string;
  deadline: Date;
  lineItemCount: number;
  estimatedValue: [number, number];
  inventoryMatch: {
    matchedItems: number;
    totalItems: number;
    percentage: number;
  };
  winProbability?: number;
  portiqInsight?: string;
}

export function OpportunityCard({
  rfq,
  onQuickQuote,
  onViewDetails,
}: OpportunityCardProps) {
  const isUrgent = differenceInHours(rfq.deadline, new Date()) < 4;
  const isHighMatch = rfq.inventoryMatch.percentage >= 85;

  return (
    <Card className={cn(
      "relative overflow-hidden",
      isUrgent && "border-destructive",
      isHighMatch && "border-primary"
    )}>
      {isHighMatch && (
        <div className="absolute top-0 right-0 bg-primary text-primary-foreground px-2 py-1 text-xs">
          High Match
        </div>
      )}

      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-lg">{rfq.title}</CardTitle>
            <CardDescription>
              {rfq.buyerName} • {rfq.vesselName} • {rfq.port}
            </CardDescription>
          </div>
          {rfq.winProbability && (
            <WinProbabilityBadge probability={rfq.winProbability} />
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Inventory Match Bar */}
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span>Inventory Match</span>
            <span className={cn(
              "font-medium",
              rfq.inventoryMatch.percentage >= 85 && "text-green-600",
              rfq.inventoryMatch.percentage >= 60 && rfq.inventoryMatch.percentage < 85 && "text-yellow-600",
              rfq.inventoryMatch.percentage < 60 && "text-red-600"
            )}>
              {rfq.inventoryMatch.matchedItems}/{rfq.inventoryMatch.totalItems} items ({rfq.inventoryMatch.percentage}%)
            </span>
          </div>
          <Progress
            value={rfq.inventoryMatch.percentage}
            className={cn(
              rfq.inventoryMatch.percentage >= 85 && "[&>div]:bg-green-500",
              rfq.inventoryMatch.percentage >= 60 && rfq.inventoryMatch.percentage < 85 && "[&>div]:bg-yellow-500",
              rfq.inventoryMatch.percentage < 60 && "[&>div]:bg-red-500"
            )}
          />
        </div>

        {/* Deadline & Value */}
        <div className="flex justify-between text-sm">
          <div className="flex items-center gap-1">
            <Clock className="h-4 w-4" />
            <span className={cn(isUrgent && "text-destructive font-medium")}>
              {formatDistanceToNow(rfq.deadline)} remaining
            </span>
          </div>
          <div>
            Est: {formatCurrency(rfq.estimatedValue[0])} - {formatCurrency(rfq.estimatedValue[1])}
          </div>
        </div>

        {/* PortiQ Insight */}
        {rfq.portiqInsight && (
          <div className="flex items-start gap-2 bg-primary/5 rounded-lg p-3">
            <Sparkles className="h-4 w-4 text-primary mt-0.5" />
            <p className="text-sm text-muted-foreground">{rfq.portiqInsight}</p>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <Button onClick={onQuickQuote} className="flex-1">
            <Zap className="h-4 w-4 mr-2" />
            Quick Quote
          </Button>
          <Button variant="outline" onClick={onViewDetails}>
            View Details
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
```

### AI-Prefilled Quote Form

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🚢 PortiQ Supplier              [← Back to Opportunities] [🔔] [Avatar ▼] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Quote for: RFQ-2024-0158 (MV Pacific Star - Mumbai Provisions)             │
│  Buyer: Pacific Fleet Management • Deadline: 2 hours                        │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 🎯 Quote Strategy                                                   │   │
│  │                                                                     │   │
│  │ PortiQ has pre-filled your quote based on inventory and pricing    │   │
│  │ history. Choose a strategy:                                        │   │
│  │                                                                     │   │
│  │ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐        │   │
│  │ │ 🏃 Aggressive   │ │ ⚖️ Balanced     │ │ 💎 Premium      │        │   │
│  │ │                 │ │                 │ │                 │        │   │
│  │ │ Total: $12,850  │ │ Total: $13,450  │ │ Total: $14,200  │        │   │
│  │ │ Margin: 12%     │ │ Margin: 18%     │ │ Margin: 24%     │        │   │
│  │ │ Win Prob: 75%   │ │ Win Prob: 65%   │ │ Win Prob: 45%   │        │   │
│  │ │                 │ │                 │ │                 │        │   │
│  │ │ [Select]        │ │ [● Selected]    │ │ [Select]        │        │   │
│  │ └─────────────────┘ └─────────────────┘ └─────────────────┘        │   │
│  │                                                                     │   │
│  │ 💡 PortiQ: "Balanced pricing is optimal - this buyer accepted      │   │
│  │     your last 3 quotes at similar margins"                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 📋 Line Items (62 available / 65 requested)           [Expand All] │   │
│  │                                                                     │   │
│  │ ┌───────────────────────────────────────────────────────────────┐  │   │
│  │ │ ✓ Fresh Provisions (45 items)                        $6,240  │  │   │
│  │ │   All items in stock • Prices auto-filled from inventory      │  │   │
│  │ └───────────────────────────────────────────────────────────────┘  │   │
│  │                                                                     │   │
│  │ ┌───────────────────────────────────────────────────────────────┐  │   │
│  │ │ ✓ Deck Supplies (10 items)                           $4,120  │  │   │
│  │ │   All items in stock • 2 prices adjusted for margin           │  │   │
│  │ └───────────────────────────────────────────────────────────────┘  │   │
│  │                                                                     │   │
│  │ ┌───────────────────────────────────────────────────────────────┐  │   │
│  │ │ ⚠️ Safety Equipment (7/10 items)                     $3,090  │  │   │
│  │ │   3 items out of stock • Substitutes suggested                │  │   │
│  │ │   [View Substitutes]                                           │  │   │
│  │ └───────────────────────────────────────────────────────────────┘  │   │
│  │                                                                     │   │
│  │ ┌───────────────────────────────────────────────────────────────┐  │   │
│  │ │ ❌ Unavailable (3 items)                               —      │  │   │
│  │ │   No stock or substitutes available                           │  │   │
│  │ │   [Mark as Partial Quote]                                      │  │   │
│  │ └───────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 📊 Quote Summary                                                    │   │
│  │                                                                     │   │
│  │ Subtotal:           $13,450       Delivery: [2 days ▼]             │   │
│  │ Valid Until:        [Feb 10 ▼]    Items Quoted: 62/65 (95%)        │   │
│  │                                                                     │   │
│  │ Win Probability: [████████████░░░░░░░░] 65%                        │   │
│  │                                                                     │   │
│  │                             [Save Draft]  [Submit Quote]            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Win Probability Calculation Display

```typescript
// components/supplier/win-probability-badge.tsx
interface WinProbabilityBadgeProps {
  probability: number;
  showDetails?: boolean;
  factors?: WinFactor[];
}

interface WinFactor {
  name: string;
  impact: 'positive' | 'neutral' | 'negative';
  description: string;
}

export function WinProbabilityBadge({
  probability,
  showDetails = false,
  factors = [],
}: WinProbabilityBadgeProps) {
  const level =
    probability >= 70 ? 'high' :
    probability >= 40 ? 'medium' : 'low';

  const colors = {
    high: 'bg-green-100 text-green-800 border-green-200',
    medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    low: 'bg-red-100 text-red-800 border-red-200',
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="outline"
            className={cn("font-medium", colors[level])}
          >
            <Target className="h-3 w-3 mr-1" />
            {probability}% Win
          </Badge>
        </TooltipTrigger>
        {showDetails && factors.length > 0 && (
          <TooltipContent className="w-64">
            <div className="space-y-2">
              <p className="font-medium">Win Probability Factors</p>
              {factors.map((factor, i) => (
                <div key={i} className="flex items-start gap-2 text-sm">
                  {factor.impact === 'positive' && <TrendingUp className="h-4 w-4 text-green-500" />}
                  {factor.impact === 'neutral' && <Minus className="h-4 w-4 text-gray-400" />}
                  {factor.impact === 'negative' && <TrendingDown className="h-4 w-4 text-red-500" />}
                  <span>{factor.description}</span>
                </div>
              ))}
            </div>
          </TooltipContent>
        )}
      </Tooltip>
    </TooltipProvider>
  );
}
```

### Quote Optimization Options

```typescript
// components/supplier/quote-strategy-selector.tsx
interface QuoteStrategy {
  id: 'aggressive' | 'balanced' | 'premium';
  name: string;
  icon: ReactNode;
  description: string;
  totalPrice: number;
  margin: number;
  winProbability: number;
  adjustments: PriceAdjustment[];
}

interface QuoteStrategySelectorProps {
  strategies: QuoteStrategy[];
  selected: string;
  onSelect: (strategyId: string) => void;
  insight?: string;
}

export function QuoteStrategySelector({
  strategies,
  selected,
  onSelect,
  insight,
}: QuoteStrategySelectorProps) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-4">
        {strategies.map((strategy) => (
          <Card
            key={strategy.id}
            className={cn(
              "cursor-pointer transition-all",
              selected === strategy.id
                ? "ring-2 ring-primary border-primary"
                : "hover:border-primary/50"
            )}
            onClick={() => onSelect(strategy.id)}
          >
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                {strategy.icon}
                {strategy.name}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div>
                <p className="text-2xl font-bold">{formatCurrency(strategy.totalPrice)}</p>
                <p className="text-sm text-muted-foreground">{strategy.margin}% margin</p>
              </div>
              <div className="flex items-center gap-2">
                <WinProbabilityBadge probability={strategy.winProbability} />
              </div>
              {selected === strategy.id && (
                <Badge className="w-full justify-center">Selected</Badge>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {insight && (
        <div className="flex items-start gap-2 bg-primary/5 rounded-lg p-3">
          <Sparkles className="h-4 w-4 text-primary mt-0.5" />
          <p className="text-sm">{insight}</p>
        </div>
      )}
    </div>
  );
}
```

### Order Management View

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🚢 PortiQ Supplier                 [Orders]           [🔔 2] [Avatar ▼]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Active Orders                                          [+ Export] [Filter] │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 🟢 ORD-2024-0892                                    Shipping Today  │   │
│  │                                                                     │   │
│  │ MV Pacific Star • Pacific Fleet Management                          │   │
│  │ Mumbai Port • Delivery: Feb 8, 14:00                                │   │
│  │                                                                     │   │
│  │ ┌─────────────────────────────────────────────────────────────────┐│   │
│  │ │ Order Progress                                                  ││   │
│  │ │ [✓ Confirmed] → [✓ Preparing] → [● Shipping] → [ Delivered]    ││   │
│  │ └─────────────────────────────────────────────────────────────────┘│   │
│  │                                                                     │   │
│  │ Items: 62 | Value: $13,450 | Margin: $2,421 (18%)                  │   │
│  │                                                                     │   │
│  │ [Update Status] [View Details] [Print Packing List]                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 🟡 ORD-2024-0888                                        Preparing   │   │
│  │                                                                     │   │
│  │ MV Ocean Voyager • Global Shipping Ltd                              │   │
│  │ Chennai Port • Delivery: Feb 10, 08:00                              │   │
│  │                                                                     │   │
│  │ ┌─────────────────────────────────────────────────────────────────┐│   │
│  │ │ Order Progress                                                  ││   │
│  │ │ [✓ Confirmed] → [● Preparing] → [ Shipping] → [ Delivered]     ││   │
│  │ └─────────────────────────────────────────────────────────────────┘│   │
│  │                                                                     │   │
│  │ ⚠️ 2 items low stock - consider sourcing alternatives              │   │
│  │                                                                     │   │
│  │ Items: 45 | Value: $8,920 | Margin: $1,427 (16%)                   │   │
│  │                                                                     │   │
│  │ [Update Status] [View Details] [Manage Stock Issue]                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ✓ ORD-2024-0885                                         Delivered  │   │
│  │                                                                     │   │
│  │ MV Star Navigator • ABC Shipping                                    │   │
│  │ Mumbai Port • Delivered: Feb 3, 16:30                               │   │
│  │                                                                     │   │
│  │ Items: 38 | Value: $6,240 | Margin: $1,123 (18%)                   │   │
│  │ ★★★★★ Rated by buyer                                               │   │
│  │                                                                     │   │
│  │ [View Details] [View Invoice]                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Supplier Command Bar Actions

```typescript
// lib/portiq/supplier-commands.ts
export const supplierCommands: CommandDefinition[] = [
  {
    trigger: ['show opportunities', 'opportunities', 'rfqs'],
    action: 'navigate',
    params: { path: '/opportunities' },
    description: 'View available RFQ opportunities',
  },
  {
    trigger: ['high match', 'best opportunities', 'good fit'],
    action: 'filter_opportunities',
    params: { filter: 'high_match' },
    description: 'Show RFQs with 80%+ inventory match',
  },
  {
    trigger: ['quote', 'quick quote'],
    pattern: /quote (?:for )?(?:rfq[- ]?)?(\d+|RFQ-\d+-\d+)/i,
    action: 'open_quote',
    extractParams: (match) => ({ rfqId: match[1] }),
    description: 'Open quote form for specific RFQ',
  },
  {
    trigger: ['aggressive pricing', 'low price', 'competitive'],
    action: 'apply_strategy',
    params: { strategy: 'aggressive' },
    description: 'Apply aggressive pricing strategy',
  },
  {
    trigger: ['balanced', 'standard pricing'],
    action: 'apply_strategy',
    params: { strategy: 'balanced' },
    description: 'Apply balanced pricing strategy',
  },
  {
    trigger: ['premium', 'high margin'],
    action: 'apply_strategy',
    params: { strategy: 'premium' },
    description: 'Apply premium pricing strategy',
  },
  {
    trigger: ['my orders', 'active orders', 'orders'],
    action: 'navigate',
    params: { path: '/orders' },
    description: 'View active orders',
  },
  {
    trigger: ['shipping today', 'due today'],
    action: 'filter_orders',
    params: { filter: 'shipping_today' },
    description: 'Show orders shipping today',
  },
  {
    trigger: ['win rate', 'performance', 'analytics'],
    action: 'navigate',
    params: { path: '/analytics' },
    description: 'View performance analytics',
  },
  {
    trigger: ['update inventory', 'stock'],
    action: 'navigate',
    params: { path: '/inventory' },
    description: 'Manage inventory levels',
  },
];
```

### State Management

```typescript
// stores/supplier-store.ts
import { create } from 'zustand';

interface QuoteState {
  rfqId: string | null;
  strategy: 'aggressive' | 'balanced' | 'premium';
  lineItems: QuoteLineItem[];
  totalPrice: number;
  margin: number;
  winProbability: number;
  unavailableItems: string[];
  substitutions: Substitution[];
  deliveryDays: number;
  validUntil: Date | null;
}

interface SupplierState {
  // Opportunities
  opportunities: RfqOpportunity[];
  opportunityFilters: OpportunityFilters;

  // Current quote
  currentQuote: QuoteState | null;

  // Orders
  activeOrders: Order[];
  orderFilters: OrderFilters;

  // Actions
  setOpportunities: (opportunities: RfqOpportunity[]) => void;
  filterOpportunities: (filters: OpportunityFilters) => void;

  initializeQuote: (rfqId: string, strategies: QuoteStrategy[]) => void;
  setQuoteStrategy: (strategy: 'aggressive' | 'balanced' | 'premium') => void;
  updateLineItem: (itemId: string, updates: Partial<QuoteLineItem>) => void;
  addSubstitution: (originalId: string, substituteId: string) => void;
  submitQuote: () => Promise<void>;
  clearQuote: () => void;

  setOrders: (orders: Order[]) => void;
  updateOrderStatus: (orderId: string, status: OrderStatus) => void;
}

export const useSupplierStore = create<SupplierState>((set, get) => ({
  opportunities: [],
  opportunityFilters: { minMatch: 0, sortBy: 'deadline' },
  currentQuote: null,
  activeOrders: [],
  orderFilters: { status: 'active' },

  setOpportunities: (opportunities) => set({ opportunities }),

  filterOpportunities: (filters) => set({ opportunityFilters: filters }),

  initializeQuote: (rfqId, strategies) => {
    const balanced = strategies.find(s => s.id === 'balanced')!;
    set({
      currentQuote: {
        rfqId,
        strategy: 'balanced',
        lineItems: balanced.adjustments.map(a => ({
          ...a,
          isAdjusted: false,
        })),
        totalPrice: balanced.totalPrice,
        margin: balanced.margin,
        winProbability: balanced.winProbability,
        unavailableItems: [],
        substitutions: [],
        deliveryDays: 2,
        validUntil: addDays(new Date(), 7),
      },
    });
  },

  setQuoteStrategy: (strategy) => {
    const { currentQuote } = get();
    if (!currentQuote) return;

    // Recalculate prices based on strategy
    // This would call an API to get new pricing
    set({
      currentQuote: {
        ...currentQuote,
        strategy,
      },
    });
  },

  updateLineItem: (itemId, updates) => {
    const { currentQuote } = get();
    if (!currentQuote) return;

    set({
      currentQuote: {
        ...currentQuote,
        lineItems: currentQuote.lineItems.map(item =>
          item.id === itemId ? { ...item, ...updates, isAdjusted: true } : item
        ),
      },
    });
  },

  addSubstitution: (originalId, substituteId) => {
    const { currentQuote } = get();
    if (!currentQuote) return;

    set({
      currentQuote: {
        ...currentQuote,
        substitutions: [
          ...currentQuote.substitutions,
          { originalId, substituteId },
        ],
      },
    });
  },

  submitQuote: async () => {
    const { currentQuote } = get();
    if (!currentQuote) return;

    await apiClient.post('/api/v1/quotes', {
      rfqId: currentQuote.rfqId,
      lineItems: currentQuote.lineItems,
      deliveryDays: currentQuote.deliveryDays,
      validUntil: currentQuote.validUntil,
      substitutions: currentQuote.substitutions,
    });

    set({ currentQuote: null });
  },

  clearQuote: () => set({ currentQuote: null }),

  setOrders: (orders) => set({ activeOrders: orders }),

  updateOrderStatus: (orderId, status) => {
    set((state) => ({
      activeOrders: state.activeOrders.map(order =>
        order.id === orderId ? { ...order, status } : order
      ),
    }));
  },
}));
```

### API Integration Points

```typescript
// lib/api/supplier.ts

// Get opportunities with inventory matching
export async function getOpportunities(
  filters?: OpportunityFilters
): Promise<PaginatedResponse<RfqOpportunity>> {
  return apiClient.get('/api/v1/supplier/opportunities', { params: filters });
}

// Get AI-generated quote strategies for an RFQ
export async function getQuoteStrategies(
  rfqId: string
): Promise<QuoteStrategy[]> {
  return apiClient.get(`/api/v1/supplier/rfqs/${rfqId}/strategies`);
}

// Submit a quote
export async function submitQuote(
  rfqId: string,
  quote: QuoteSubmission
): Promise<Quote> {
  return apiClient.post(`/api/v1/supplier/rfqs/${rfqId}/quote`, quote);
}

// Get suggested substitutions for unavailable items
export async function getSubstitutions(
  rfqId: string,
  itemIds: string[]
): Promise<Substitution[]> {
  return apiClient.post(`/api/v1/supplier/rfqs/${rfqId}/substitutions`, {
    itemIds,
  });
}

// Get win probability factors
export async function getWinProbabilityFactors(
  rfqId: string,
  strategy: string
): Promise<WinFactor[]> {
  return apiClient.get(`/api/v1/supplier/rfqs/${rfqId}/win-factors`, {
    params: { strategy },
  });
}

// Update order status
export async function updateOrderStatus(
  orderId: string,
  status: OrderStatus,
  notes?: string
): Promise<Order> {
  return apiClient.patch(`/api/v1/supplier/orders/${orderId}/status`, {
    status,
    notes,
  });
}

// Get supplier analytics
export async function getSupplierAnalytics(
  period: 'week' | 'month' | 'quarter' | 'year'
): Promise<SupplierAnalytics> {
  return apiClient.get('/api/v1/supplier/analytics', { params: { period } });
}
```

---

## Dependencies

- ADR-UI-001: Next.js 14+ App Router
- ADR-UI-002: Component Library (shadcn/ui)
- ADR-UI-003: State Management Strategy (extended for supplier state)
- ADR-UI-009: Design System & Theming (AI component library)
- ADR-UI-015: Command Bar & Voice Input Architecture
- ADR-UI-016: Proactive Intelligence & Notifications
- ADR-FN-013: Quote Comparison & TCO Engine (win probability calculation)

---

## Migration Strategy

### From ADR-UI-005 (Traditional Dashboard)

1. **Phase 1: AI Quote Assistant**
   - Add AI quote pre-fill to existing quote form
   - Show win probability on opportunity cards
   - Maintain existing workflow as fallback

2. **Phase 2: Unified Interface**
   - Deploy full PortiQ supplier interface
   - Add Command Bar for quick actions
   - Enable voice input for mobile

3. **Phase 3: Full Migration**
   - Default new suppliers to PortiQ interface
   - Migrate existing suppliers with training
   - Deprecate classic interface after 6 months

### Feature Mapping

| Dashboard Feature | PortiQ Equivalent |
|-------------------|-------------------|
| Opportunities list | Inventory-matched opportunity cards |
| Manual quote form | AI-prefilled quote with strategies |
| Order list | Order cards with progress tracking |
| Inventory management | "Update inventory" command |
| Analytics dashboard | "Show my win rate" command |

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Opportunity load | < 500ms | API response time |
| Inventory match calculation | < 1s | Real-time on load |
| Quote strategy generation | < 2s | AI processing time |
| Win probability calculation | < 500ms | Per quote |
| Quote submission | < 1s | Submit to confirmation |

---

## Success Metrics

| Metric | Target | Tracking |
|--------|--------|----------|
| Time to quote | < 3 minutes | Analytics |
| Quote submission rate | +50% | vs. baseline |
| Win rate improvement | +15% | vs. pre-AI |
| AI suggestion acceptance | > 70% | Action tracking |
| Mobile quote submissions | > 25% | Platform tracking |

---

## References

- PortiQ UX Design Specification (internal)
- [B2B Supplier Portal Best Practices](https://www.nngroup.com/articles/b2b-usability/)
- [AI-Assisted Pricing Interfaces](https://www.smashingmagazine.com/2022/06/designing-better-dashboards/)
