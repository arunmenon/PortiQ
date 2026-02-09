"use client";

import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RfqStatusBadge } from "@/components/rfqs/rfq-status-badge";
import { MapPin, Clock, Package, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { RfqResponse } from "@/lib/api/types";

interface OpportunityCardProps {
  rfq: RfqResponse;
}

function formatShortDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function getDeadlineUrgency(deadline: string): "green" | "yellow" | "red" {
  const daysUntil = Math.ceil(
    (new Date(deadline).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
  );
  if (daysUntil <= 2) return "red";
  if (daysUntil <= 7) return "yellow";
  return "green";
}

const urgencyStyles = {
  green: "border-transparent bg-green-100 text-green-700",
  yellow: "border-transparent bg-amber-100 text-amber-700",
  red: "border-transparent bg-red-100 text-red-700",
};

export function OpportunityCard({ rfq }: OpportunityCardProps) {
  const router = useRouter();

  return (
    <Card
      className="cursor-pointer transition-shadow hover:shadow-md"
      onClick={() => router.push(`/supplier/rfqs/${rfq.id}`)}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base leading-tight">
            {rfq.title}
          </CardTitle>
          <RfqStatusBadge status={rfq.status} />
        </div>
        <Badge variant="secondary" className="w-fit font-mono text-xs">
          {rfq.reference_number}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Package className="h-3.5 w-3.5 flex-shrink-0" />
          <span>
            {rfq.line_items.length} line{" "}
            {rfq.line_items.length === 1 ? "item" : "items"}
          </span>
        </div>

        {rfq.delivery_port && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <MapPin className="h-3.5 w-3.5 flex-shrink-0" />
            <span className="truncate">{rfq.delivery_port}</span>
          </div>
        )}

        {rfq.bidding_deadline && (
          <div className="flex items-center gap-2 text-sm">
            <Clock className="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" />
            <Badge
              variant="outline"
              className={cn(
                "text-xs",
                urgencyStyles[getDeadlineUrgency(rfq.bidding_deadline)]
              )}
            >
              Deadline: {formatShortDate(rfq.bidding_deadline)}
            </Badge>
          </div>
        )}

        <div className="flex items-center justify-end pt-1">
          <span className="flex items-center gap-1 text-xs font-medium text-primary">
            View Details
            <ArrowRight className="h-3 w-3" />
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
