"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getSupplierRfqDetail } from "@/lib/api/supplier-portal";
import { QuoteForm } from "@/components/supplier/quote-form";
import { Skeleton } from "@/components/ui/skeleton";
import { Package } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function SupplierQuotePage() {
  const params = useParams();
  const rfqId = params.id as string;

  const { data: rfq, isLoading, error } = useQuery({
    queryKey: ["supplier-rfq", rfqId],
    queryFn: () => getSupplierRfqDetail(rfqId),
    enabled: !!rfqId,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (error || !rfq) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Package className="mb-4 h-12 w-12 text-muted-foreground" />
        <p className="text-lg font-medium">RFQ not found</p>
        <p className="text-sm text-muted-foreground">
          Unable to load the RFQ details for quoting.
        </p>
        <Button variant="outline" className="mt-4" asChild>
          <Link href="/supplier/rfqs">Back to Opportunities</Link>
        </Button>
      </div>
    );
  }

  if (rfq.status !== "BIDDING_OPEN") {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Package className="mb-4 h-12 w-12 text-muted-foreground" />
        <p className="text-lg font-medium">Bidding not open</p>
        <p className="text-sm text-muted-foreground">
          This RFQ is not currently accepting quotes. Status: {rfq.status}
        </p>
        <Button variant="outline" className="mt-4" asChild>
          <Link href={`/supplier/rfqs/${rfqId}`}>Back to RFQ</Link>
        </Button>
      </div>
    );
  }

  return (
    <QuoteForm
      rfqId={rfqId}
      lineItems={rfq.line_items}
      currency={rfq.currency}
    />
  );
}
