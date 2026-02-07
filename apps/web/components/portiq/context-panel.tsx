"use client";

import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sparkles, Ship, FileText, BarChart3, ShoppingCart, X } from "lucide-react";
import { useConversationStore, type ContextPanelType } from "@/stores/conversation-store";

interface ContextPanelProps {
  className?: string;
  onClose?: () => void;
}

const panelConfig: Record<ContextPanelType, { icon: React.ElementType; label: string }> = {
  vessel: { icon: Ship, label: "Vessel" },
  rfq: { icon: FileText, label: "RFQ" },
  comparison: { icon: BarChart3, label: "Quote Comparison" },
  order: { icon: ShoppingCart, label: "Order" },
};

function VesselContext({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="space-y-3 text-sm">
      <div className="flex justify-between">
        <span className="text-muted-foreground">Name</span>
        <span className="font-medium">{String(data.name || "\u2014")}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-muted-foreground">IMO</span>
        <span className="font-mono">{String(data.imo || "\u2014")}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-muted-foreground">Type</span>
        <span>{String(data.type || "\u2014")}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-muted-foreground">Flag</span>
        <span>{String(data.flag || "\u2014")}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-muted-foreground">Port</span>
        <span>{String(data.port || "\u2014")}</span>
      </div>
    </div>
  );
}

function RfqContext({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="space-y-3 text-sm">
      <div className="flex justify-between">
        <span className="text-muted-foreground">RFQ #</span>
        <span className="font-mono">{String(data.id || "\u2014")}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-muted-foreground">Status</span>
        <Badge variant="outline">{String(data.status || "Draft")}</Badge>
      </div>
      <div className="flex justify-between">
        <span className="text-muted-foreground">Items</span>
        <span>{String(data.itemCount || 0)}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-muted-foreground">Due</span>
        <span>{String(data.dueDate || "\u2014")}</span>
      </div>
    </div>
  );
}

function ComparisonContext({ data }: { data: Record<string, unknown> }) {
  const suppliers = (data.suppliers as string[]) || [];
  return (
    <div className="space-y-3 text-sm">
      <div className="flex justify-between">
        <span className="text-muted-foreground">Quotes</span>
        <span>{suppliers.length}</span>
      </div>
      {suppliers.map((supplier, i) => (
        <div key={i} className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-primary" />
          <span>{supplier}</span>
        </div>
      ))}
    </div>
  );
}

function OrderContext({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="space-y-3 text-sm">
      <div className="flex justify-between">
        <span className="text-muted-foreground">Order #</span>
        <span className="font-mono">{String(data.id || "\u2014")}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-muted-foreground">Status</span>
        <Badge variant="outline">{String(data.status || "\u2014")}</Badge>
      </div>
      <div className="flex justify-between">
        <span className="text-muted-foreground">Total</span>
        <span>${String(data.total || "0")}</span>
      </div>
    </div>
  );
}

const contextComponents: Record<ContextPanelType, React.FC<{ data: Record<string, unknown> }>> = {
  vessel: VesselContext,
  rfq: RfqContext,
  comparison: ComparisonContext,
  order: OrderContext,
};

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 mb-4">
        <Sparkles className="h-6 w-6 text-primary" />
      </div>
      <h3 className="font-semibold text-sm mb-1">Context Panel</h3>
      <p className="text-xs text-muted-foreground">
        Start a conversation and relevant context — vessels, RFQs, quotes — will appear here.
      </p>
    </div>
  );
}

export function ContextPanel({ className, onClose }: ContextPanelProps) {
  const { context, clearContext } = useConversationStore();

  if (!context.type || !context.data) {
    return (
      <div className={cn("border-l bg-card", className)}>
        <EmptyState />
      </div>
    );
  }

  const config = panelConfig[context.type];
  const ContextBody = contextComponents[context.type];
  const Icon = config.icon;

  return (
    <div className={cn("border-l bg-card overflow-y-auto", className)}>
      <div className="p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Icon className="h-4 w-4 text-primary" />
            <span className="font-semibold text-sm">{config.label}</span>
          </div>
          <div className="flex gap-1">
            {onClose && (
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClose}>
                <X className="h-4 w-4" />
              </Button>
            )}
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={clearContext}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <Card>
          <CardHeader className="pb-2 pt-3 px-4">
            <CardTitle className="text-xs text-muted-foreground uppercase tracking-wider">
              {config.label} Details
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-3">
            <ContextBody data={context.data} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
