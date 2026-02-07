"use client";

import { cn } from "@/lib/utils";

type ThinkingVariant = "dots" | "steps" | "scanning";

interface ThinkingStep {
  label: string;
  status: "active" | "complete" | "pending";
}

interface ThinkingIndicatorProps {
  variant?: ThinkingVariant;
  steps?: ThinkingStep[];
  className?: string;
}

function DotsIndicator() {
  return (
    <div className="flex items-center gap-1 px-4 py-3">
      <div className="flex items-center gap-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-2 w-2 rounded-full bg-primary animate-bounce"
            style={{ animationDelay: `${i * 150}ms` }}
          />
        ))}
      </div>
      <span className="ml-2 text-sm text-muted-foreground">Thinking...</span>
    </div>
  );
}

function StepsIndicator({ steps }: { steps: ThinkingStep[] }) {
  return (
    <div className="space-y-2 px-4 py-3">
      {steps.map((step, i) => (
        <div key={i} className="flex items-center gap-2 text-sm">
          {step.status === "complete" && (
            <span className="h-4 w-4 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-[10px]">
              &#10003;
            </span>
          )}
          {step.status === "active" && (
            <span className="h-4 w-4 rounded-full border-2 border-primary animate-pulse" />
          )}
          {step.status === "pending" && (
            <span className="h-4 w-4 rounded-full border-2 border-muted" />
          )}
          <span
            className={cn(
              step.status === "complete" && "text-muted-foreground line-through",
              step.status === "active" && "text-foreground font-medium",
              step.status === "pending" && "text-muted-foreground"
            )}
          >
            {step.label}
          </span>
        </div>
      ))}
    </div>
  );
}

function ScanningIndicator() {
  return (
    <div className="px-4 py-3 space-y-2">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span>Scanning catalog...</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div className="h-full w-1/3 rounded-full bg-primary animate-[scan_1.5s_ease-in-out_infinite]" />
      </div>
    </div>
  );
}

export function ThinkingIndicator({ variant = "dots", steps = [], className }: ThinkingIndicatorProps) {
  return (
    <div className={cn("flex items-start gap-3", className)}>
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
        <span className="text-sm font-medium text-primary">AI</span>
      </div>
      <div className="rounded-lg border bg-card">
        {variant === "dots" && <DotsIndicator />}
        {variant === "steps" && <StepsIndicator steps={steps} />}
        {variant === "scanning" && <ScanningIndicator />}
      </div>
    </div>
  );
}
