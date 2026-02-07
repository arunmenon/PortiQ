"use client";

import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { AICard } from "@/stores/conversation-store";

interface ActionCardProps {
  card: AICard;
  className?: string;
}

function SuggestionCard({ data }: { data: Record<string, unknown> }) {
  const items = (data.items as string[]) || [];
  return (
    <ul className="space-y-1">
      {items.map((item, i) => (
        <li key={i} className="flex items-center gap-2 text-sm">
          <span className="h-1.5 w-1.5 rounded-full bg-primary" />
          {item}
        </li>
      ))}
    </ul>
  );
}

function RfqSummaryCard({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="space-y-2 text-sm">
      {data.vessel != null && (
        <div>
          <span className="text-muted-foreground">Vessel:</span> {String(data.vessel)}
        </div>
      )}
      {data.port != null && (
        <div>
          <span className="text-muted-foreground">Port:</span> {String(data.port)}
        </div>
      )}
      {data.itemCount != null && (
        <div>
          <span className="text-muted-foreground">Items:</span> {String(data.itemCount)}
        </div>
      )}
      {data.estimatedTotal != null && (
        <div>
          <span className="text-muted-foreground">Est. Total:</span> ${String(data.estimatedTotal)}
        </div>
      )}
    </div>
  );
}

function QuoteComparisonCard({ data }: { data: Record<string, unknown> }) {
  const quotes =
    (data.quotes as Array<{ supplier: string; total: number; delivery: string }>) || [];
  return (
    <div className="space-y-2">
      {quotes.map((quote, i) => (
        <div
          key={i}
          className="flex items-center justify-between text-sm border-b last:border-0 pb-2 last:pb-0"
        >
          <span className="font-medium">{quote.supplier}</span>
          <div className="flex items-center gap-2">
            <span>${quote.total.toLocaleString()}</span>
            <Badge variant="outline">{quote.delivery}</Badge>
          </div>
        </div>
      ))}
    </div>
  );
}

function ProductListCard({ data }: { data: Record<string, unknown> }) {
  const products =
    (data.products as Array<{ name: string; impa: string; category?: string }>) || [];
  return (
    <div className="space-y-2">
      {products.map((product, i) => (
        <div key={i} className="flex items-center gap-2 text-sm">
          <Badge variant="secondary" className="font-mono text-xs">
            {product.impa}
          </Badge>
          <span>{product.name}</span>
          {product.category && (
            <span className="text-muted-foreground">&middot; {product.category}</span>
          )}
        </div>
      ))}
    </div>
  );
}

function VesselInfoCard({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="space-y-2 text-sm">
      {data.name != null && (
        <div>
          <span className="text-muted-foreground">Name:</span> {String(data.name)}
        </div>
      )}
      {data.imo != null && (
        <div>
          <span className="text-muted-foreground">IMO:</span> {String(data.imo)}
        </div>
      )}
      {data.type != null && (
        <div>
          <span className="text-muted-foreground">Type:</span> {String(data.type)}
        </div>
      )}
      {data.flag != null && (
        <div>
          <span className="text-muted-foreground">Flag:</span> {String(data.flag)}
        </div>
      )}
    </div>
  );
}

const cardComponents: Record<string, React.FC<{ data: Record<string, unknown> }>> = {
  suggestion: SuggestionCard,
  rfq_summary: RfqSummaryCard,
  quote_comparison: QuoteComparisonCard,
  vessel_info: VesselInfoCard,
  product_list: ProductListCard,
};

export function ActionCard({ card, className }: ActionCardProps) {
  const CardBody = cardComponents[card.type];

  return (
    <Card className={cn("my-2", className)}>
      <CardHeader className="pb-2 pt-3 px-4">
        <CardTitle className="text-sm font-medium">{card.title}</CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-3">
        {CardBody ? (
          <CardBody data={card.data} />
        ) : (
          <pre className="text-xs">{JSON.stringify(card.data, null, 2)}</pre>
        )}
      </CardContent>
    </Card>
  );
}
