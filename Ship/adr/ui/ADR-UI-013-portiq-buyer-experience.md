# ADR-UI-013: PortiQ Buyer Experience Architecture

**Status:** Accepted
**Date:** 2026-02-06
**Technical Area:** Frontend
**Supersedes:** ADR-UI-004

---

## Context

The PortiQ UX Design Specification introduces an **AI-native, conversation-first paradigm** that fundamentally changes how buyers interact with the maritime ship chandlery platform. Rather than navigating traditional dashboard hierarchies and form-based workflows, buyers engage with an intelligent assistant that understands natural language, anticipates needs, and accelerates procurement.

### Business Context

The traditional dashboard approach (ADR-UI-004) required buyers to:
- Navigate multiple screens to create an RFQ
- Manually search and filter catalogs
- Manually compare quotes across suppliers
- Switch contexts frequently

The PortiQ approach enables:
- **Time to first RFQ: < 2 minutes** (vs. ~10 minutes traditional)
- **AI suggestion acceptance rate: > 70%**
- **Zero-click completions: > 40%** through proactive assistance
- **Voice input adoption: > 30%** for mobile/field users

### Technical Context

- Next.js 14 App Router (ADR-UI-001)
- shadcn/ui with AI-specific components (ADR-UI-002, UI-009)
- React Query for AI conversation state (ADR-UI-003)
- Real-time WebSocket for AI streaming (ADR-UI-012)
- Voice input via Web Speech API

### Assumptions

- Buyers prefer conversational interaction over form navigation
- Natural language can express complex procurement requirements
- AI can accurately parse vessel/port context from conversation
- Mobile buyers need voice-first input options

---

## Decision Drivers

- Reduce time-to-RFQ below 2 minutes
- Minimize clicks and context switches
- Support natural language procurement requests
- Enable voice input for field operations
- Maintain full functionality for power users

---

## Decision

We will build the buyer experience as a **conversation-first interface** with PortiQ AI as the primary interaction layer. The interface features a unified Command Bar for input, a two-panel conversation view for AI dialogue, and context-aware panels that display relevant information based on the conversation state.

---

## Implementation Notes

### Buyer Home Wireframe

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🚢 PortiQ                                    [Search] [🔔 3] [Avatar ▼]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Good morning, Captain Chen                                                │
│                                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │ 🎤  Ask PortiQ anything...                              ⌘K       │    │
│   │                                                                   │    │
│   │   Try: "Prepare provisions for MV Pacific Star arriving Mumbai"  │    │
│   │        "Show me my pending RFQs"                                  │    │
│   │        "Compare quotes for RFQ-2024-0156"                        │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│   ┌─────────────────────────────────┐  ┌─────────────────────────────────┐ │
│   │ 📋 Active RFQs                  │  │ 🚢 Fleet Status                 │ │
│   │                                 │  │                                 │ │
│   │ RFQ-2024-0158  ● 3 quotes      │  │ MV Pacific Star                 │ │
│   │ Deadline: 2h remaining         │  │ ETA Mumbai: Feb 8, 14:00       │ │
│   │                                 │  │ Status: Provisions needed       │ │
│   │ RFQ-2024-0157  ● 5 quotes      │  │                                 │ │
│   │ Ready for review               │  │ MV Ocean Voyager                │ │
│   │                                 │  │ ETA Chennai: Feb 10, 08:00     │ │
│   │ [View All →]                   │  │ Status: On schedule             │ │
│   └─────────────────────────────────┘  └─────────────────────────────────┘ │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │ 💡 PortiQ Suggests                                                  │  │
│   │                                                                     │  │
│   │ ┌─────────────────────────────────────────────────────────────────┐│  │
│   │ │ 🔄 MV Pacific Star needs restocking before Mumbai arrival       ││  │
│   │ │    Based on consumption patterns, you'll need deck supplies     ││  │
│   │ │    [Start RFQ] [Remind Me Later]                               ││  │
│   │ └─────────────────────────────────────────────────────────────────┘│  │
│   │                                                                     │  │
│   │ ┌─────────────────────────────────────────────────────────────────┐│  │
│   │ │ ⚡ Quick win: Accept recommended quote for RFQ-0157             ││  │
│   │ │    Saves $2,340 vs. second-best option                          ││  │
│   │ │    [Review & Accept] [See Comparison]                          ││  │
│   │ └─────────────────────────────────────────────────────────────────┘│  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Command Bar Component Specification

```typescript
// components/portiq/command-bar.tsx
interface CommandBarProps {
  onSubmit: (input: string) => void;
  onVoiceInput: () => void;
  suggestions?: CommandSuggestion[];
  isProcessing?: boolean;
  placeholder?: string;
}

interface CommandSuggestion {
  type: 'action' | 'search' | 'ai_command';
  icon: ReactNode;
  label: string;
  description?: string;
  action: () => void;
}

// States:
// - default: Ready for input with placeholder suggestions
// - focused: Expanded with suggestion dropdown
// - voice-active: Microphone listening with waveform
// - processing: AI thinking indicator

export function CommandBar({
  onSubmit,
  onVoiceInput,
  suggestions = [],
  isProcessing = false,
  placeholder = "Ask PortiQ anything...",
}: CommandBarProps) {
  const [query, setQuery] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Keyboard shortcut: ⌘K to focus
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className={cn(
      "relative w-full max-w-2xl mx-auto",
      isFocused && "ring-2 ring-primary"
    )}>
      <div className="flex items-center gap-3 bg-muted rounded-xl px-4 py-3">
        <VoiceInputButton
          isActive={isVoiceActive}
          onToggle={() => {
            setIsVoiceActive(!isVoiceActive);
            if (!isVoiceActive) onVoiceInput();
          }}
        />

        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setTimeout(() => setIsFocused(false), 200)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && query.trim()) {
              onSubmit(query);
              setQuery('');
            }
          }}
          placeholder={placeholder}
          className="flex-1 bg-transparent outline-none text-sm"
        />

        {isProcessing ? (
          <AIThinkingIndicator variant="dots" />
        ) : (
          <kbd className="hidden md:flex text-xs text-muted-foreground">⌘K</kbd>
        )}
      </div>

      {/* Suggestion Dropdown */}
      {isFocused && suggestions.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-popover rounded-lg shadow-lg border p-2 z-50">
          {suggestions.map((suggestion, i) => (
            <button
              key={i}
              onClick={suggestion.action}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-md hover:bg-accent text-left"
            >
              {suggestion.icon}
              <div>
                <p className="text-sm font-medium">{suggestion.label}</p>
                {suggestion.description && (
                  <p className="text-xs text-muted-foreground">{suggestion.description}</p>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

### Two-Panel Conversation View

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🚢 PortiQ                      [← Back to Home]      [🔔 3] [Avatar ▼]    │
├───────────────────────────────────────────┬─────────────────────────────────┤
│                                           │                                 │
│  Conversation                             │  Context: MV Pacific Star       │
│                                           │                                 │
│  ┌─────────────────────────────────────┐  │  ┌─────────────────────────────┐│
│  │ 👤 You                              │  │  │ 🚢 Vessel Details           ││
│  │ Prepare provisions for MV Pacific   │  │  │                             ││
│  │ Star arriving Mumbai next week      │  │  │ IMO: 9234567               ││
│  └─────────────────────────────────────┘  │  │ Flag: Panama               ││
│                                           │  │ Crew: 22                    ││
│  ┌─────────────────────────────────────┐  │  │ Last Supply: 45 days ago   ││
│  │ 🤖 PortiQ                           │  │  └─────────────────────────────┘│
│  │                                     │  │                                 │
│  │ I found MV Pacific Star arriving    │  │  ┌─────────────────────────────┐│
│  │ Mumbai on Feb 8. Based on the 22    │  │  │ 📍 Port Call                ││
│  │ crew and 45 days since last supply, │  │  │                             ││
│  │ I recommend:                        │  │  │ Port: Mumbai               ││
│  │                                     │  │  │ ETA: Feb 8, 14:00          ││
│  │ ┌─────────────────────────────────┐ │  │  │ Berth: Requested           ││
│  │ │ 📦 Suggested Provisions         │ │  │  └─────────────────────────────┘│
│  │ │                                 │ │  │                                 │
│  │ │ • Fresh provisions (45 items)  │ │  │  ┌─────────────────────────────┐│
│  │ │ • Deck supplies (12 items)     │ │  │  │ 📋 Draft RFQ               ││
│  │ │ • Safety equipment (8 items)   │ │  │  │                             ││
│  │ │                                 │ │  │  │ 65 line items             ││
│  │ │ Est. value: $12,400 - $15,200  │ │  │  │ Est: $12,400 - $15,200     ││
│  │ │                                 │ │  │  │                             ││
│  │ │ [Create RFQ] [Adjust Items]    │ │  │  │ [View Details]             ││
│  │ └─────────────────────────────────┘ │  │  └─────────────────────────────┘│
│  │                                     │  │                                 │
│  │ Should I create this RFQ and send   │  │                                 │
│  │ to your preferred Mumbai suppliers? │  │                                 │
│  └─────────────────────────────────────┘  │                                 │
│                                           │                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 🎤  Type your response or ask a follow-up question...          ⌘K   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Context Panel States

The context panel dynamically updates based on conversation state:

```typescript
// components/portiq/context-panel.tsx
type ContextPanelType =
  | 'vessel'      // Show vessel details, crew, consumption history
  | 'rfq'         // Show RFQ summary, line items, suppliers
  | 'comparison'  // Show quote comparison, TCO analysis
  | 'order'       // Show order status, delivery tracking

interface ContextPanelProps {
  type: ContextPanelType;
  data: VesselContext | RfqContext | ComparisonContext | OrderContext;
}

// Vessel Context
interface VesselContext {
  vessel: {
    name: string;
    imo: string;
    flag: string;
    crewSize: number;
    lastSupplyDate: Date;
    consumptionHistory: ConsumptionRecord[];
  };
  portCall?: {
    port: string;
    eta: Date;
    berth?: string;
  };
  draftRfq?: {
    lineItemCount: number;
    estimatedRange: [number, number];
  };
}

// RFQ Context
interface RfqContext {
  rfq: {
    id: string;
    title: string;
    status: RfqStatus;
    lineItems: LineItem[];
    deadline: Date;
    invitedSuppliers: Supplier[];
  };
  quotes: Quote[];
}

// Comparison Context
interface ComparisonContext {
  rfq: RfqSummary;
  quotes: QuoteComparison[];
  recommendation: {
    supplierId: string;
    confidence: number;
    reasoning: string[];
    savings: number;
  };
}
```

### Document Upload Drop Zone

```typescript
// components/portiq/document-drop-zone.tsx
interface DocumentDropZoneProps {
  onUpload: (files: File[]) => void;
  onProcessingComplete: (result: DocumentResult) => void;
  acceptedTypes?: string[];
}

// States:
// - default: "Drop requisition files here or click to upload"
// - dragover: Visual highlight, "Release to upload"
// - uploading: Progress bar with file names
// - processing: AI extraction animation with status steps

export function DocumentDropZone({
  onUpload,
  onProcessingComplete,
  acceptedTypes = ['.pdf', '.xlsx', '.xls', '.csv', '.jpg', '.png'],
}: DocumentDropZoneProps) {
  const [state, setState] = useState<'default' | 'dragover' | 'uploading' | 'processing'>('default');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processingStep, setProcessingStep] = useState<string>('');

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setState('dragover');
      }}
      onDragLeave={() => setState('default')}
      onDrop={async (e) => {
        e.preventDefault();
        const files = Array.from(e.dataTransfer.files);
        setState('uploading');
        // ... upload logic
      }}
      className={cn(
        "border-2 border-dashed rounded-xl p-8 text-center transition-colors",
        state === 'default' && "border-muted-foreground/25 hover:border-primary/50",
        state === 'dragover' && "border-primary bg-primary/5",
        state === 'uploading' && "border-primary",
        state === 'processing' && "border-primary bg-primary/5"
      )}
    >
      {state === 'default' && (
        <>
          <Upload className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-sm font-medium">Drop requisition files here</p>
          <p className="text-xs text-muted-foreground mt-1">
            PDF, Excel, CSV, or images supported
          </p>
        </>
      )}

      {state === 'dragover' && (
        <>
          <FileUp className="h-12 w-12 mx-auto text-primary mb-4 animate-bounce" />
          <p className="text-sm font-medium text-primary">Release to upload</p>
        </>
      )}

      {state === 'uploading' && (
        <>
          <Loader2 className="h-12 w-12 mx-auto text-primary mb-4 animate-spin" />
          <Progress value={uploadProgress} className="w-full max-w-xs mx-auto" />
          <p className="text-sm mt-2">Uploading...</p>
        </>
      )}

      {state === 'processing' && (
        <>
          <AIThinkingIndicator variant="steps" />
          <p className="text-sm font-medium mt-4">{processingStep}</p>
          <div className="mt-2 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              <Check className="h-3 w-3 text-green-500" /> Document recognized
            </span>
            <span className="inline-flex items-center gap-1 ml-3">
              <Loader2 className="h-3 w-3 animate-spin" /> Extracting line items
            </span>
          </div>
        </>
      )}
    </div>
  );
}
```

### RFQ Review & Confirmation Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🚢 PortiQ                      [← Back to Conversation] [🔔 3] [Avatar ▼] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Review RFQ: MV Pacific Star - Mumbai Provisions                            │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 📋 Line Items (65)                                    [+ Add Item] │   │
│  │                                                                     │   │
│  │ ┌─────┬────────────────────────────────┬──────┬────────┬─────────┐ │   │
│  │ │     │ Product                        │ Qty  │ Unit   │ Action  │ │   │
│  │ ├─────┼────────────────────────────────┼──────┼────────┼─────────┤ │   │
│  │ │ ✓   │ 170101 Fresh Vegetables Assort │ 50   │ kg     │ [Edit]  │ │   │
│  │ │ ✓   │ 170102 Fresh Fruits Assorted   │ 30   │ kg     │ [Edit]  │ │   │
│  │ │ ⚠️  │ 170201 Frozen Beef             │ 25   │ kg     │ [Edit]  │ │   │
│  │ │     │ └─ PortiQ: "Suggest 35kg based │      │        │         │ │   │
│  │ │     │     on 22 crew, 45 day gap"    │      │        │         │ │   │
│  │ │     │     [Accept 35kg] [Keep 25kg]  │      │        │         │ │   │
│  │ │ ✓   │ 311501 Mooring Rope 24mm       │ 200  │ m      │ [Edit]  │ │   │
│  │ │ ...                                                            │ │   │
│  │ └─────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                     │   │
│  │ Showing 1-10 of 65 items                        [< Prev] [Next >]  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 👥 Suppliers (5 selected)                          [+ Add Supplier] │   │
│  │                                                                     │   │
│  │ ┌────────────────────┬──────────┬───────────┬────────────────────┐ │   │
│  │ │ Supplier           │ Rating   │ Avg Lead  │ Match              │ │   │
│  │ ├────────────────────┼──────────┼───────────┼────────────────────┤ │   │
│  │ │ ✓ Mumbai Marine    │ ★★★★☆   │ 2 days    │ 95% items          │ │   │
│  │ │ ✓ Ocean Supplies   │ ★★★★★   │ 3 days    │ 89% items          │ │   │
│  │ │ ✓ Port Provisions  │ ★★★☆☆   │ 1 day     │ 78% items          │ │   │
│  │ │ ✓ Coastal Trading  │ ★★★★☆   │ 2 days    │ 92% items          │ │   │
│  │ │ ✓ Harbor Supplies  │ ★★★★☆   │ 2 days    │ 85% items          │ │   │
│  │ └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                     │   │
│  │ 💡 PortiQ selected these suppliers based on your history and       │   │
│  │    their Mumbai port coverage.                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ⏰ Deadline                                                         │   │
│  │                                                                     │   │
│  │ Bidding deadline: [Feb 6, 2024 ▼] [18:00 ▼]  (48 hours before ETA)│   │
│  │                                                                     │   │
│  │ 💡 PortiQ: "48 hours gives suppliers time to respond while          │   │
│  │     ensuring delivery before departure"                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                              [Save Draft] [Publish] │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Quote Comparison with AI Recommendation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🚢 PortiQ                          [← Back to RFQ]    [🔔 3] [Avatar ▼]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Quote Comparison: RFQ-2024-0158 (MV Pacific Star)                         │
│  5 quotes received • Deadline: 2 hours remaining                           │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 🏆 PortiQ Recommendation                                            │   │
│  │                                                                     │   │
│  │ ┌─────────────────────────────────────────────────────────────────┐│   │
│  │ │ 🥇 Mumbai Marine Supply Co.                                     ││   │
│  │ │                                                                 ││   │
│  │ │ Total: $13,450              TCO Score: 94/100                   ││   │
│  │ │                                                                 ││   │
│  │ │ Why this quote?                                                 ││   │
│  │ │ • Best price-to-quality ratio (saves $2,340 vs. next best)     ││   │
│  │ │ • 95% item availability (highest match)                        ││   │
│  │ │ • 2-day delivery meets your Feb 8 deadline                     ││   │
│  │ │ • ★★★★☆ rating from 47 orders with your fleet                  ││   │
│  │ │                                                                 ││   │
│  │ │ [Accept Recommendation]  [See Full Comparison]                  ││   │
│  │ └─────────────────────────────────────────────────────────────────┘│   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 📊 All Quotes                                                       │   │
│  │                                                                     │   │
│  │ ┌──────────────────┬─────────┬─────────┬─────────┬────────┬──────┐ │   │
│  │ │ Supplier         │ Total   │ Items   │ Lead    │ Rating │ TCO  │ │   │
│  │ ├──────────────────┼─────────┼─────────┼─────────┼────────┼──────┤ │   │
│  │ │ 🥇 Mumbai Marine │ $13,450 │ 62/65   │ 2 days  │ ★★★★☆ │ 94   │ │   │
│  │ │ 🥈 Ocean Supply  │ $15,790 │ 58/65   │ 3 days  │ ★★★★★ │ 88   │ │   │
│  │ │ 🥉 Coastal Trade │ $14,200 │ 60/65   │ 2 days  │ ★★★★☆ │ 86   │ │   │
│  │ │    Harbor Supply │ $13,900 │ 55/65   │ 2 days  │ ★★★★☆ │ 82   │ │   │
│  │ │    Port Provisn  │ $12,100 │ 51/65   │ 1 day   │ ★★★☆☆ │ 75   │ │   │
│  │ └──────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                     │   │
│  │ [View Line-by-Line Comparison]                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 💬 Ask PortiQ about these quotes...                          ⌘K    │   │
│  │                                                                     │   │
│  │ Try: "Why isn't the cheapest quote recommended?"                    │   │
│  │      "What items are missing from each quote?"                     │   │
│  │      "Show me delivery risk analysis"                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### AI Message Rendering Components

```typescript
// components/portiq/ai-message.tsx
interface AIMessageProps {
  message: AIMessage;
  onAction: (action: AIAction) => void;
}

interface AIMessage {
  id: string;
  type: 'text' | 'card' | 'comparison' | 'confirmation';
  content: string;
  cards?: AICard[];
  actions?: AIAction[];
  confidence?: number;
  timestamp: Date;
}

interface AICard {
  type: 'suggestion' | 'rfq_summary' | 'quote_comparison' | 'vessel_info';
  title: string;
  data: Record<string, any>;
  actions?: AIAction[];
}

interface AIAction {
  id: string;
  label: string;
  variant: 'primary' | 'secondary' | 'destructive';
  action: string; // Action identifier for handler
  params?: Record<string, any>;
}

export function AIMessage({ message, onAction }: AIMessageProps) {
  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0">
        <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
          <Bot className="h-4 w-4 text-primary" />
        </div>
      </div>

      <div className="flex-1 space-y-3">
        <div className="prose prose-sm max-w-none">
          {message.content}
        </div>

        {message.cards?.map((card, i) => (
          <ActionCard key={i} card={card} onAction={onAction} />
        ))}

        {message.actions && (
          <div className="flex flex-wrap gap-2">
            {message.actions.map((action) => (
              <Button
                key={action.id}
                variant={action.variant === 'primary' ? 'default' : 'outline'}
                size="sm"
                onClick={() => onAction(action)}
              >
                {action.label}
              </Button>
            ))}
          </div>
        )}

        {message.confidence && message.confidence < 0.9 && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <ConfidenceIndicator level={message.confidence} />
            <span>
              {message.confidence < 0.7
                ? "I'm not fully confident about this. Please verify."
                : "This looks correct, but you may want to double-check."}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
```

### State Management

```typescript
// stores/conversation-store.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  cards?: AICard[];
  actions?: AIAction[];
  timestamp: Date;
}

interface ConversationState {
  messages: Message[];
  context: {
    type: ContextPanelType | null;
    data: any;
  };
  pendingActions: AIAction[];
  isProcessing: boolean;

  // Actions
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  updateContext: (type: ContextPanelType, data: any) => void;
  clearContext: () => void;
  setProcessing: (processing: boolean) => void;
  addPendingAction: (action: AIAction) => void;
  removePendingAction: (actionId: string) => void;
  clearConversation: () => void;
}

export const useConversationStore = create<ConversationState>()(
  persist(
    (set) => ({
      messages: [],
      context: { type: null, data: null },
      pendingActions: [],
      isProcessing: false,

      addMessage: (message) =>
        set((state) => ({
          messages: [
            ...state.messages,
            {
              ...message,
              id: crypto.randomUUID(),
              timestamp: new Date(),
            },
          ],
        })),

      updateContext: (type, data) =>
        set({ context: { type, data } }),

      clearContext: () =>
        set({ context: { type: null, data: null } }),

      setProcessing: (processing) =>
        set({ isProcessing: processing }),

      addPendingAction: (action) =>
        set((state) => ({
          pendingActions: [...state.pendingActions, action],
        })),

      removePendingAction: (actionId) =>
        set((state) => ({
          pendingActions: state.pendingActions.filter((a) => a.id !== actionId),
        })),

      clearConversation: () =>
        set({ messages: [], context: { type: null, data: null }, pendingActions: [] }),
    }),
    {
      name: 'portiq-conversation',
      partialize: (state) => ({
        messages: state.messages.slice(-50), // Keep last 50 messages
      }),
    }
  )
);
```

### API Integration Points

```typescript
// lib/api/portiq.ts
import { apiClient } from './client';

// Send message to PortiQ AI
export async function sendPortiQMessage(
  message: string,
  context?: { vesselId?: string; rfqId?: string }
): Promise<PortiQResponse> {
  return apiClient.post('/api/v1/portiq/chat', {
    message,
    context,
    sessionId: getSessionId(),
  });
}

// Stream response for real-time typing effect
export function streamPortiQResponse(
  message: string,
  context?: any,
  onChunk: (chunk: string) => void,
  onCard: (card: AICard) => void,
  onComplete: (response: PortiQResponse) => void
): void {
  const eventSource = new EventSource(
    `/api/v1/portiq/chat/stream?message=${encodeURIComponent(message)}&context=${encodeURIComponent(JSON.stringify(context))}`
  );

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'chunk') {
      onChunk(data.content);
    } else if (data.type === 'card') {
      onCard(data.card);
    } else if (data.type === 'complete') {
      onComplete(data.response);
      eventSource.close();
    }
  };

  eventSource.onerror = () => {
    eventSource.close();
  };
}

// Execute AI-suggested action
export async function executePortiQAction(
  action: AIAction
): Promise<ActionResult> {
  return apiClient.post('/api/v1/portiq/action', {
    actionId: action.id,
    action: action.action,
    params: action.params,
  });
}

// Get vessel context for conversation
export async function getVesselContext(
  vesselId: string
): Promise<VesselContext> {
  return apiClient.get(`/api/v1/portiq/context/vessel/${vesselId}`);
}

// Get RFQ context for conversation
export async function getRfqContext(
  rfqId: string
): Promise<RfqContext> {
  return apiClient.get(`/api/v1/portiq/context/rfq/${rfqId}`);
}
```

### React Query Hooks

```typescript
// hooks/queries/use-portiq.ts
import { useMutation, useQuery } from '@tanstack/react-query';
import { useConversationStore } from '@/stores/conversation-store';
import * as portiqApi from '@/lib/api/portiq';

export function usePortiQChat() {
  const { addMessage, setProcessing, updateContext } = useConversationStore();

  return useMutation({
    mutationFn: async ({ message, context }: { message: string; context?: any }) => {
      return portiqApi.sendPortiQMessage(message, context);
    },
    onMutate: ({ message }) => {
      addMessage({ role: 'user', content: message });
      setProcessing(true);
    },
    onSuccess: (response) => {
      addMessage({
        role: 'assistant',
        content: response.message,
        cards: response.cards,
        actions: response.actions,
      });

      if (response.context) {
        updateContext(response.context.type, response.context.data);
      }
    },
    onSettled: () => {
      setProcessing(false);
    },
  });
}

export function usePortiQAction() {
  const { addMessage, removePendingAction } = useConversationStore();

  return useMutation({
    mutationFn: portiqApi.executePortiQAction,
    onSuccess: (result, action) => {
      removePendingAction(action.id);

      if (result.message) {
        addMessage({
          role: 'assistant',
          content: result.message,
          cards: result.cards,
        });
      }
    },
  });
}

export function useVesselContext(vesselId: string | undefined) {
  return useQuery({
    queryKey: ['portiq', 'context', 'vessel', vesselId],
    queryFn: () => portiqApi.getVesselContext(vesselId!),
    enabled: !!vesselId,
  });
}
```

---

## Dependencies

- ADR-UI-001: Next.js 14+ App Router
- ADR-UI-002: Component Library (shadcn/ui)
- ADR-UI-003: State Management Strategy (extended for AI state)
- ADR-UI-009: Design System & Theming (AI component library)
- ADR-UI-015: Command Bar & Voice Input Architecture
- ADR-UI-016: Proactive Intelligence & Notifications
- ADR-FN-006: Document AI Pipeline (document upload integration)
- ADR-FN-009: Confidence-Gated Human-in-Loop (review UX)
- ADR-FN-013: Quote Comparison & TCO Engine (recommendation display)

---

## Migration Strategy

### From ADR-UI-004 (Traditional Dashboard)

1. **Phase 1: Parallel Deployment**
   - Deploy PortiQ conversation interface alongside existing dashboard
   - Add "Try PortiQ" banner on dashboard pages
   - Allow users to switch between interfaces

2. **Phase 2: Default to PortiQ**
   - Make PortiQ the default experience for new users
   - Existing users retain dashboard access
   - Track adoption metrics and satisfaction

3. **Phase 3: Dashboard Deprecation**
   - Move dashboard to "Classic Mode" in settings
   - Migrate remaining power users with training
   - Maintain dashboard for 6 months post-deprecation

### Feature Mapping

| Dashboard Feature | PortiQ Equivalent |
|-------------------|-------------------|
| Dashboard metrics | Proactive suggestions + Home cards |
| Catalog search | Command bar natural language search |
| RFQ creation wizard | Conversation-driven RFQ creation |
| Quote comparison table | AI recommendation with comparison |
| Order list | "Show my orders" command |
| Supplier directory | "Find suppliers for X" command |

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Command bar response | < 100ms | Input to first character |
| AI response start | < 500ms | Submit to first token |
| Full AI response | < 3s | For simple queries |
| Context panel update | < 200ms | On conversation change |
| Document upload start | < 1s | Drop to upload begin |
| Document processing | < 30s | Upload to extraction complete |

---

## Success Metrics

| Metric | Target | Tracking |
|--------|--------|----------|
| Time to first RFQ | < 2 minutes | Analytics |
| AI suggestion acceptance | > 70% | Action tracking |
| Voice input adoption | > 30% | Input method tracking |
| User satisfaction (CSAT) | > 4.5/5 | Post-task surveys |
| Return to dashboard rate | < 10% | Navigation tracking |

---

## References

- PortiQ UX Design Specification (internal)
- [Conversational UI Patterns](https://www.nngroup.com/articles/chatbots/)
- [Voice Input Best Practices](https://developers.google.com/assistant/design)
- [AI Transparency Guidelines](https://pair.withgoogle.com/guidebook/)
