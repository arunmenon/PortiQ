"use client";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  TrendingUp,
  Users,
  AlertTriangle,
  Clock,
  Sparkles,
} from "lucide-react";
import { useIntelligence } from "@/hooks/use-intelligence";
import { IntelligenceCard } from "./intelligence-card";
import type {
  PriceBenchmark,
  SupplierMatch,
  RiskFlag,
  TimingAdvice,
  BudgetEstimate,
} from "@/lib/api/intelligence";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface IntelligenceSidebarProps {
  deliveryPort: string;
  impaCodes?: string[];
  vesselId?: string;
  deliveryDate?: string;
  biddingDeadline?: string;
  className?: string;
}

// ---------------------------------------------------------------------------
// Severity helpers
// ---------------------------------------------------------------------------

const severityColor: Record<string, string> = {
  HIGH: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  MEDIUM: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  LOW: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
};

const assessmentColor: Record<string, string> = {
  sufficient: "text-green-600 dark:text-green-400",
  tight: "text-yellow-600 dark:text-yellow-400",
  risky: "text-red-600 dark:text-red-400",
};

// ---------------------------------------------------------------------------
// Sub-sections
// ---------------------------------------------------------------------------

function PriceSection({
  benchmarks,
  budget,
}: {
  benchmarks: PriceBenchmark[];
  budget: BudgetEstimate | null;
}) {
  const itemsWithData = benchmarks.filter((b) => b.has_data);

  if (itemsWithData.length === 0 && !budget) {
    return (
      <p className="text-xs text-muted-foreground">
        Add IMPA codes to line items to see price intelligence.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {budget && (
        <div className="rounded-md border bg-muted/30 p-3 space-y-1">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Budget Estimate
          </p>
          <div className="flex items-baseline gap-1">
            <span className="text-lg font-semibold">
              {budget.currency} {Number(budget.likely).toLocaleString()}
            </span>
            <span className="text-xs text-muted-foreground">median</span>
          </div>
          <div className="flex gap-3 text-xs text-muted-foreground">
            <span>Low: {budget.currency} {Number(budget.low).toLocaleString()}</span>
            <span>High: {budget.currency} {Number(budget.high).toLocaleString()}</span>
          </div>
          <p className="text-xs text-muted-foreground">
            Based on {budget.items_with_data} item{budget.items_with_data !== 1 ? "s" : ""} with data
            {budget.items_without_data > 0 &&
              `, ${budget.items_without_data} without`}
          </p>
        </div>
      )}

      {itemsWithData.length > 0 && (
        <>
          <Separator />
          <div className="space-y-2">
            {itemsWithData.slice(0, 5).map((benchmark) => (
              <div
                key={benchmark.impa_code}
                className="flex items-center justify-between text-sm"
              >
                <span className="font-mono text-xs text-muted-foreground">
                  {benchmark.impa_code}
                </span>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-muted-foreground">
                    {benchmark.p25 != null ? Number(benchmark.p25).toFixed(0) : "--"}
                  </span>
                  <span className="font-medium">
                    {benchmark.p50 != null ? Number(benchmark.p50).toFixed(0) : "--"}
                  </span>
                  <span className="text-muted-foreground">
                    {benchmark.p75 != null ? Number(benchmark.p75).toFixed(0) : "--"}
                  </span>
                  <span className="text-muted-foreground">
                    ({benchmark.quote_count})
                  </span>
                </div>
              </div>
            ))}
            {itemsWithData.length > 5 && (
              <p className="text-xs text-muted-foreground">
                +{itemsWithData.length - 5} more items
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function SupplierSection({
  recommended,
  totalCount,
  singleSourceRisk,
}: {
  recommended: SupplierMatch[];
  totalCount: number;
  singleSourceRisk: boolean;
}) {
  if (recommended.length === 0) {
    return (
      <p className="text-xs text-muted-foreground">
        No matching suppliers found for this port.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {singleSourceRisk && (
        <div className="flex items-center gap-1.5 text-xs text-yellow-600 dark:text-yellow-400">
          <AlertTriangle className="h-3 w-3" />
          Single source risk
        </div>
      )}
      {recommended.slice(0, 5).map((supplier) => (
        <div
          key={supplier.supplier_id}
          className="flex items-center justify-between text-sm"
        >
          <div className="flex items-center gap-2 min-w-0">
            <span className="truncate">{supplier.organization_name}</span>
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            <Badge variant="outline" className="text-xs px-1.5 py-0">
              {supplier.tier}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {(supplier.score * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      ))}
      {totalCount > recommended.length && (
        <p className="text-xs text-muted-foreground">
          +{totalCount - recommended.length} more suppliers available
        </p>
      )}
    </div>
  );
}

function RiskSection({ risks }: { risks: RiskFlag[] }) {
  if (risks.length === 0) {
    return (
      <p className="text-xs text-muted-foreground">
        No risks identified for current parameters.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {risks.map((risk, index) => (
        <div key={index} className="flex items-start gap-2 text-sm">
          <Badge
            variant="secondary"
            className={cn(
              "text-xs px-1.5 py-0 shrink-0 mt-0.5",
              severityColor[risk.severity],
            )}
          >
            {risk.severity}
          </Badge>
          <span className="text-xs leading-relaxed">{risk.message}</span>
        </div>
      ))}
    </div>
  );
}

function TimingSection({ timing }: { timing: TimingAdvice }) {
  return (
    <div className="space-y-2 text-sm">
      <p className="text-xs">{timing.recommendation}</p>
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Timeline:</span>
        <span
          className={cn(
            "text-xs font-medium capitalize",
            assessmentColor[timing.timeline_assessment],
          )}
        >
          {timing.timeline_assessment}
        </span>
      </div>
      {timing.avg_response_days != null && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Avg response:</span>
          <span className="text-xs">
            {timing.avg_response_days.toFixed(1)} days
          </span>
        </div>
      )}
      {timing.optimal_window_days > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Optimal window:</span>
          <span className="text-xs">{timing.optimal_window_days} days</span>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function SidebarSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="space-y-2 rounded-lg border p-4">
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-4" />
            <Skeleton className="h-4 w-24" />
          </div>
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center px-4">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 mb-3">
        <Sparkles className="h-5 w-5 text-primary" />
      </div>
      <p className="text-sm font-medium mb-1">Intelligence Panel</p>
      <p className="text-xs text-muted-foreground">
        Enter a delivery port to see supplier matches, price benchmarks, and risk
        analysis.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main sidebar
// ---------------------------------------------------------------------------

export function IntelligenceSidebar({
  deliveryPort,
  impaCodes,
  vesselId,
  deliveryDate,
  biddingDeadline,
  className,
}: IntelligenceSidebarProps) {
  const hasPort = deliveryPort.trim().length > 0;

  const { data, isLoading, isError } = useIntelligence({
    deliveryPort: hasPort ? deliveryPort : undefined,
    impaCodes,
    vesselId,
    deliveryDate,
    biddingDeadline,
  });

  if (!hasPort) {
    return (
      <div className={cn("sticky top-6", className)}>
        <EmptyState />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={cn("sticky top-6", className)}>
        <SidebarSkeleton />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className={cn("sticky top-6", className)}>
        <div className="rounded-md border border-yellow-200 bg-yellow-50 dark:border-yellow-900/50 dark:bg-yellow-900/10 p-3">
          <p className="text-xs text-yellow-700 dark:text-yellow-400">
            Unable to load intelligence data. The sidebar will retry when parameters change.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("sticky top-6 space-y-3", className)}>
      {/* Price Intelligence */}
      <IntelligenceCard title="Price Intelligence" icon={TrendingUp}>
        <PriceSection
          benchmarks={data.price_benchmarks}
          budget={data.budget_estimate}
        />
      </IntelligenceCard>

      {/* Supplier Matches */}
      {data.suppliers && (
        <IntelligenceCard title="Supplier Matches" icon={Users}>
          <SupplierSection
            recommended={data.suppliers.recommended}
            totalCount={data.suppliers.total_count}
            singleSourceRisk={data.suppliers.single_source_risk}
          />
        </IntelligenceCard>
      )}

      {/* Risk Flags */}
      {data.risk_flags.length > 0 && (
        <IntelligenceCard title="Risk Flags" icon={AlertTriangle}>
          <RiskSection risks={data.risk_flags} />
        </IntelligenceCard>
      )}

      {/* Timing */}
      {data.timing && (
        <IntelligenceCard
          title="Timing Advice"
          icon={Clock}
          defaultOpen={false}
        >
          <TimingSection timing={data.timing} />
        </IntelligenceCard>
      )}
    </div>
  );
}
