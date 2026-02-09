"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getSupplierRfqDetail,
  respondToInvitation,
} from "@/lib/api/supplier-portal";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { RfqStatusBadge } from "@/components/rfqs/rfq-status-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ArrowLeft,
  MapPin,
  Calendar,
  Clock,
  Package,
  Send,
  CheckCircle,
  Loader2,
} from "lucide-react";
import Link from "next/link";

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default function SupplierRfqDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const rfqId = params.id as string;

  const { data: rfq, isLoading, error } = useQuery({
    queryKey: ["supplier-rfq", rfqId],
    queryFn: () => getSupplierRfqDetail(rfqId),
    enabled: !!rfqId,
  });

  const acceptMutation = useMutation({
    mutationFn: () =>
      respondToInvitation(rfqId, { accept: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["supplier-rfq", rfqId] });
    },
  });

  const canSubmitQuote =
    rfq?.status === "BIDDING_OPEN";

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error || !rfq) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Package className="mb-4 h-12 w-12 text-muted-foreground" />
        <p className="text-lg font-medium">RFQ not found</p>
        <p className="text-sm text-muted-foreground">
          This RFQ may not exist or you may not have access.
        </p>
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => router.push("/supplier/rfqs")}
        >
          Back to Opportunities
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push("/supplier/rfqs")}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">
                {rfq.title}
              </h1>
              <div className="mt-1 flex items-center gap-2">
                <Badge variant="secondary" className="font-mono text-xs">
                  {rfq.reference_number}
                </Badge>
                <RfqStatusBadge status={rfq.status} />
              </div>
            </div>
            <div className="flex gap-2">
              {rfq.status === "PUBLISHED" && (
                <Button
                  onClick={() => acceptMutation.mutate()}
                  disabled={acceptMutation.isPending}
                >
                  {acceptMutation.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <CheckCircle className="mr-2 h-4 w-4" />
                  )}
                  Accept Invitation
                </Button>
              )}
              {canSubmitQuote && (
                <Button asChild>
                  <Link href={`/supplier/rfqs/${rfqId}/quote`}>
                    <Send className="mr-2 h-4 w-4" />
                    Submit Quote
                  </Link>
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* RFQ Details */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {rfq.description && (
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Description
                </p>
                <p className="text-sm mt-1">{rfq.description}</p>
              </div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Currency
                </p>
                <p className="text-sm mt-1">{rfq.currency}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Auction Type
                </p>
                <p className="text-sm mt-1">Sealed Bid</p>
              </div>
            </div>
            {rfq.notes && (
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Notes
                </p>
                <p className="text-sm mt-1">{rfq.notes}</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Delivery & Timeline</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {rfq.delivery_port && (
              <div className="flex items-center gap-2 text-sm">
                <MapPin className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-xs text-muted-foreground">Delivery Port</p>
                  <p className="font-medium">{rfq.delivery_port}</p>
                </div>
              </div>
            )}
            {rfq.delivery_date && (
              <div className="flex items-center gap-2 text-sm">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-xs text-muted-foreground">Delivery Date</p>
                  <p className="font-medium">{formatDate(rfq.delivery_date)}</p>
                </div>
              </div>
            )}
            {rfq.bidding_deadline && (
              <div className="flex items-center gap-2 text-sm">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-xs text-muted-foreground">
                    Bidding Deadline
                  </p>
                  <p className="font-medium">
                    {formatDate(rfq.bidding_deadline)}
                  </p>
                </div>
              </div>
            )}
            <Separator />
            <div className="flex flex-wrap gap-2 text-xs">
              {rfq.allow_partial_quotes && (
                <Badge variant="outline">Partial Quotes Allowed</Badge>
              )}
              {rfq.allow_quote_revision && (
                <Badge variant="outline">Quote Revision Allowed</Badge>
              )}
              {rfq.require_all_line_items && (
                <Badge variant="outline">All Line Items Required</Badge>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Line Items Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Line Items ({rfq.line_items.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">#</TableHead>
                <TableHead>Description</TableHead>
                <TableHead className="w-24">IMPA Code</TableHead>
                <TableHead className="w-20 text-right">Qty</TableHead>
                <TableHead className="w-20">Unit</TableHead>
                <TableHead>Notes</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rfq.line_items.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {item.line_number}
                  </TableCell>
                  <TableCell className="font-medium">
                    {item.description}
                  </TableCell>
                  <TableCell>
                    {item.impa_code ? (
                      <Badge variant="secondary" className="font-mono text-xs">
                        {item.impa_code}
                      </Badge>
                    ) : (
                      <span className="text-xs text-muted-foreground">--</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">{item.quantity}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {item.unit_of_measure}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {item.notes || "--"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {acceptMutation.isError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Failed to accept invitation. Please try again.
        </div>
      )}

      {acceptMutation.isSuccess && (
        <div className="rounded-md border border-green-200 bg-green-50 p-4 text-sm text-green-700">
          Invitation accepted successfully. You can now submit a quote when bidding opens.
        </div>
      )}
    </div>
  );
}
