"use client";

import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RfqStatusBadge } from "./rfq-status-badge";
import { MapPin, Clock, Calendar, Package } from "lucide-react";
import type { RfqResponse } from "@/lib/api/types";

interface RfqCardProps {
  rfq: RfqResponse;
}

function formatShortDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function RfqCard({ rfq }: RfqCardProps) {
  const router = useRouter();

  return (
    <Card
      className="cursor-pointer transition-shadow hover:shadow-md"
      onClick={() => router.push(`/rfqs/${rfq.id}`)}
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
            {rfq.line_items.length} line {rfq.line_items.length === 1 ? "item" : "items"}
          </span>
        </div>

        {rfq.delivery_port && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <MapPin className="h-3.5 w-3.5 flex-shrink-0" />
            <span className="truncate">{rfq.delivery_port}</span>
          </div>
        )}

        {rfq.bidding_deadline && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="h-3.5 w-3.5 flex-shrink-0" />
            <span>Deadline: {formatShortDate(rfq.bidding_deadline)}</span>
          </div>
        )}

        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Calendar className="h-3.5 w-3.5 flex-shrink-0" />
          <span>Created {formatShortDate(rfq.created_at)}</span>
        </div>
      </CardContent>
    </Card>
  );
}
