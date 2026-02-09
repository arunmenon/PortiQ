"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getRfq,
  listInvitations,
  listQuotes,
  getTransitions,
  publishRfq,
  openBidding,
  closeBidding,
  startEvaluation,
  awardRfq,
  completeRfq,
  cancelRfq,
  deleteRfq,
} from "@/lib/api/rfqs";
import type {
  RfqResponse,
  RfqStatus,
  InvitationResponse,
  QuoteResponse,
  TransitionResponse,
  InvitationStatus,
  QuoteStatus,
} from "@/lib/api/types";
import { RfqStatusBadge } from "@/components/rfqs/rfq-status-badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
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
  FileText,
  Clock,
  MapPin,
  Calendar,
  Package,
  Send,
  XCircle,
  CheckCircle,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Tab definitions
// ---------------------------------------------------------------------------

type TabId = "overview" | "line-items" | "invitations" | "quotes" | "history";

const POST_BIDDING_STATUSES: RfqStatus[] = [
  "BIDDING_CLOSED",
  "EVALUATION",
  "AWARDED",
  "COMPLETED",
];

// ---------------------------------------------------------------------------
// Helper: format date string for display
// ---------------------------------------------------------------------------

function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return "---";
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ---------------------------------------------------------------------------
// Invitation status badge colors
// ---------------------------------------------------------------------------

const invitationStatusStyles: Record<InvitationStatus, string> = {
  PENDING: "bg-yellow-100 text-yellow-700",
  ACCEPTED: "bg-green-100 text-green-700",
  DECLINED: "bg-red-100 text-red-700",
  EXPIRED: "bg-gray-100 text-gray-500",
};

// ---------------------------------------------------------------------------
// Quote status badge colors
// ---------------------------------------------------------------------------

const quoteStatusStyles: Record<QuoteStatus, string> = {
  DRAFT: "bg-gray-100 text-gray-700",
  SUBMITTED: "bg-blue-100 text-blue-700",
  REVISED: "bg-indigo-100 text-indigo-700",
  WITHDRAWN: "bg-orange-100 text-orange-700",
  AWARDED: "bg-green-100 text-green-700",
  REJECTED: "bg-red-100 text-red-700",
  EXPIRED: "bg-gray-100 text-gray-500",
};

// ---------------------------------------------------------------------------
// RFQ Detail Page
// ---------------------------------------------------------------------------

export default function RfqDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const rfqId = params.id as string;

  const [activeTab, setActiveTab] = useState<TabId>("overview");

  // --- Data fetching ---

  const {
    data: rfq,
    isLoading: rfqLoading,
    error: rfqError,
  } = useQuery({
    queryKey: ["rfq", rfqId],
    queryFn: () => getRfq(rfqId),
    enabled: !!rfqId,
  });

  const { data: invitations, isLoading: invitationsLoading } = useQuery({
    queryKey: ["rfq-invitations", rfqId],
    queryFn: () => listInvitations(rfqId),
    enabled: !!rfqId,
  });

  const { data: quotesData, isLoading: quotesLoading } = useQuery({
    queryKey: ["rfq-quotes", rfqId],
    queryFn: () => listQuotes(rfqId),
    enabled: !!rfqId && POST_BIDDING_STATUSES.includes(rfq?.status as RfqStatus),
  });

  const { data: transitions, isLoading: transitionsLoading } = useQuery({
    queryKey: ["rfq-transitions", rfqId],
    queryFn: () => getTransitions(rfqId),
    enabled: !!rfqId,
  });

  // --- Mutations ---

  function invalidateRfq() {
    queryClient.invalidateQueries({ queryKey: ["rfq", rfqId] });
    queryClient.invalidateQueries({ queryKey: ["rfq-transitions", rfqId] });
    queryClient.invalidateQueries({ queryKey: ["rfqs"] });
  }

  const publishMutation = useMutation({
    mutationFn: () => publishRfq(rfqId),
    onSuccess: invalidateRfq,
  });

  const openBiddingMutation = useMutation({
    mutationFn: () => openBidding(rfqId),
    onSuccess: invalidateRfq,
  });

  const closeBiddingMutation = useMutation({
    mutationFn: () => closeBidding(rfqId),
    onSuccess: invalidateRfq,
  });

  const startEvaluationMutation = useMutation({
    mutationFn: () => startEvaluation(rfqId),
    onSuccess: invalidateRfq,
  });

  const awardMutation = useMutation({
    mutationFn: (quoteId: string) => awardRfq(rfqId, { quote_id: quoteId }),
    onSuccess: invalidateRfq,
  });

  const completeMutation = useMutation({
    mutationFn: () => completeRfq(rfqId),
    onSuccess: invalidateRfq,
  });

  const cancelMutation = useMutation({
    mutationFn: (reason: string) => cancelRfq(rfqId, { reason }),
    onSuccess: invalidateRfq,
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteRfq(rfqId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rfqs"] });
      router.push("/rfqs");
    },
  });

  // --- Status action handlers ---

  function handlePublish() {
    publishMutation.mutate();
  }

  function handleOpenBidding() {
    openBiddingMutation.mutate();
  }

  function handleCloseBidding() {
    closeBiddingMutation.mutate();
  }

  function handleStartEvaluation() {
    startEvaluationMutation.mutate();
  }

  function handleAward() {
    const quotes = quotesData?.items ?? [];
    const rankedQuotes = quotes
      .filter((q) => q.status === "SUBMITTED" || q.status === "REVISED")
      .sort((a, b) => (a.price_rank ?? 999) - (b.price_rank ?? 999));

    if (rankedQuotes.length === 0) {
      const selectedQuoteId = prompt("Enter the quote ID to award:");
      if (selectedQuoteId) {
        awardMutation.mutate(selectedQuoteId);
      }
      return;
    }

    const topQuote = rankedQuotes[0];
    const confirmed = confirm(
      `Award to quote from supplier ${topQuote.supplier_organization_id} (rank #${topQuote.price_rank}, total: ${topQuote.total_amount} ${topQuote.currency})?`
    );
    if (confirmed) {
      awardMutation.mutate(topQuote.id);
    }
  }

  function handleComplete() {
    completeMutation.mutate();
  }

  function handleCancel() {
    const reason = prompt("Enter cancellation reason:");
    if (reason) {
      cancelMutation.mutate(reason);
    }
  }

  function handleDelete() {
    const confirmed = confirm(
      "Are you sure you want to delete this RFQ? This action cannot be undone."
    );
    if (confirmed) {
      deleteMutation.mutate();
    }
  }

  // --- Loading / Error / Not found ---

  const isLoading = rfqLoading;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.push("/rfqs")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to RFQs
          </Button>
        </div>
        <div className="space-y-4">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      </div>
    );
  }

  if (rfqError || !rfq) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.push("/rfqs")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to RFQs
          </Button>
        </div>
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <FileText className="mb-4 h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium">RFQ not found</p>
          <p className="text-sm text-muted-foreground">
            The RFQ you are looking for does not exist or has been removed.
          </p>
        </div>
      </div>
    );
  }

  // --- Derived values ---

  const invitationList: InvitationResponse[] = invitations ?? [];
  const quoteList: QuoteResponse[] = quotesData?.items ?? [];
  const transitionList: TransitionResponse[] = transitions ?? [];
  const lineItems = rfq.line_items ?? [];
  const isTerminal = rfq.status === "COMPLETED" || rfq.status === "CANCELLED";
  const anyMutating =
    publishMutation.isPending ||
    openBiddingMutation.isPending ||
    closeBiddingMutation.isPending ||
    startEvaluationMutation.isPending ||
    awardMutation.isPending ||
    completeMutation.isPending ||
    cancelMutation.isPending ||
    deleteMutation.isPending;

  // --- Tab definitions with labels ---

  const tabs: { id: TabId; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "line-items", label: `Line Items (${lineItems.length})` },
    {
      id: "invitations",
      label: `Invitations (${invitationList.length})`,
    },
    { id: "quotes", label: `Quotes (${quoteList.length})` },
    { id: "history", label: `History (${transitionList.length})` },
  ];

  return (
    <div className="space-y-6">
      {/* Back button */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => router.push("/rfqs")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to RFQs
        </Button>
      </div>

      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">{rfq.title}</h1>
            <Badge variant="outline" className="font-mono text-xs">
              {rfq.reference_number}
            </Badge>
            <RfqStatusBadge status={rfq.status} />
          </div>
          <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <Package className="h-3.5 w-3.5" />
              {rfq.currency}
            </span>
            {rfq.delivery_port && (
              <span className="flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5" />
                {rfq.delivery_port}
              </span>
            )}
            {rfq.bidding_deadline && (
              <span className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                Bidding deadline: {formatDate(rfq.bidding_deadline)}
              </span>
            )}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {rfq.status === "DRAFT" && (
            <>
              <Button
                size="sm"
                onClick={handlePublish}
                disabled={anyMutating}
              >
                <Send className="mr-2 h-4 w-4" />
                Publish
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={handleDelete}
                disabled={anyMutating}
              >
                <XCircle className="mr-2 h-4 w-4" />
                Delete
              </Button>
            </>
          )}
          {rfq.status === "PUBLISHED" && (
            <Button
              size="sm"
              onClick={handleOpenBidding}
              disabled={anyMutating}
            >
              <CheckCircle className="mr-2 h-4 w-4" />
              Open Bidding
            </Button>
          )}
          {rfq.status === "BIDDING_OPEN" && (
            <Button
              size="sm"
              onClick={handleCloseBidding}
              disabled={anyMutating}
            >
              <Clock className="mr-2 h-4 w-4" />
              Close Bidding
            </Button>
          )}
          {rfq.status === "BIDDING_CLOSED" && (
            <Button
              size="sm"
              onClick={handleStartEvaluation}
              disabled={anyMutating}
            >
              <AlertCircle className="mr-2 h-4 w-4" />
              Start Evaluation
            </Button>
          )}
          {rfq.status === "EVALUATION" && (
            <Button
              size="sm"
              onClick={handleAward}
              disabled={anyMutating}
            >
              <CheckCircle className="mr-2 h-4 w-4" />
              Award
            </Button>
          )}
          {rfq.status === "AWARDED" && (
            <Button
              size="sm"
              onClick={handleComplete}
              disabled={anyMutating}
            >
              <CheckCircle className="mr-2 h-4 w-4" />
              Complete
            </Button>
          )}
          {!isTerminal && (
            <Button
              size="sm"
              variant="destructive"
              onClick={handleCancel}
              disabled={anyMutating}
            >
              <XCircle className="mr-2 h-4 w-4" />
              Cancel
            </Button>
          )}
        </div>
      </div>

      {/* Tab selector */}
      <div className="flex gap-1 border-b">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={cn(
              "px-4 py-2 text-sm font-medium transition-colors",
              "border-b-2 -mb-px",
              activeTab === tab.id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground/50"
            )}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "overview" && <OverviewTab rfq={rfq} />}
      {activeTab === "line-items" && <LineItemsTab lineItems={lineItems} />}
      {activeTab === "invitations" && (
        <InvitationsTab
          invitations={invitationList}
          isLoading={invitationsLoading}
        />
      )}
      {activeTab === "quotes" && (
        <QuotesTab
          quotes={quoteList}
          rfqStatus={rfq.status}
          isLoading={quotesLoading}
        />
      )}
      {activeTab === "history" && (
        <HistoryTab
          transitions={transitionList}
          isLoading={transitionsLoading}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Overview Tab
// ---------------------------------------------------------------------------

function OverviewTab({ rfq }: { rfq: RfqResponse }) {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {rfq.description && (
            <div>
              <p className="text-sm font-medium text-muted-foreground">
                Description
              </p>
              <p className="text-sm">{rfq.description}</p>
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground">
                Auction Type
              </p>
              <p className="text-sm">
                {rfq.auction_type.replace(/_/g, " ")}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">
                Currency
              </p>
              <p className="text-sm">{rfq.currency}</p>
            </div>
            {rfq.vessel_id && (
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Vessel ID
                </p>
                <p className="text-sm font-mono">{rfq.vessel_id}</p>
              </div>
            )}
            {rfq.delivery_port && (
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Delivery Port
                </p>
                <p className="text-sm">{rfq.delivery_port}</p>
              </div>
            )}
            {rfq.delivery_date && (
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Delivery Date
                </p>
                <p className="text-sm">{formatDate(rfq.delivery_date)}</p>
              </div>
            )}
            {rfq.bidding_deadline && (
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Bidding Deadline
                </p>
                <p className="text-sm">
                  {formatDate(rfq.bidding_deadline)}
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <SettingRow
              label="Allow Partial Quotes"
              enabled={rfq.allow_partial_quotes}
            />
            <SettingRow
              label="Allow Quote Revision"
              enabled={rfq.allow_quote_revision}
            />
            <SettingRow
              label="Require All Line Items"
              enabled={rfq.require_all_line_items}
            />
          </div>
          <Separator />
          {rfq.notes && (
            <div>
              <p className="text-sm font-medium text-muted-foreground">Notes</p>
              <p className="text-sm">{rfq.notes}</p>
            </div>
          )}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="font-medium text-muted-foreground">Created</p>
              <p>{formatDate(rfq.created_at)}</p>
            </div>
            <div>
              <p className="font-medium text-muted-foreground">Updated</p>
              <p>{formatDate(rfq.updated_at)}</p>
            </div>
            {rfq.bidding_start && (
              <div>
                <p className="font-medium text-muted-foreground">
                  Bidding Start
                </p>
                <p>{formatDate(rfq.bidding_start)}</p>
              </div>
            )}
            {rfq.awarded_at && (
              <div>
                <p className="font-medium text-muted-foreground">Awarded At</p>
                <p>{formatDate(rfq.awarded_at)}</p>
              </div>
            )}
            {rfq.cancelled_at && (
              <div className="col-span-2">
                <p className="font-medium text-muted-foreground">
                  Cancelled At
                </p>
                <p>{formatDate(rfq.cancelled_at)}</p>
                {rfq.cancellation_reason && (
                  <p className="mt-1 text-sm text-red-600">
                    Reason: {rfq.cancellation_reason}
                  </p>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function SettingRow({
  label,
  enabled,
}: {
  label: string;
  enabled: boolean;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm">{label}</span>
      <Badge
        variant="outline"
        className={cn(
          enabled
            ? "bg-green-50 text-green-700 border-green-200"
            : "bg-gray-50 text-gray-500 border-gray-200"
        )}
      >
        {enabled ? "Yes" : "No"}
      </Badge>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Line Items Tab
// ---------------------------------------------------------------------------

function LineItemsTab({
  lineItems,
}: {
  lineItems: RfqResponse["line_items"];
}) {
  if (lineItems.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Package className="mb-4 h-12 w-12 text-muted-foreground" />
        <p className="text-lg font-medium">No line items</p>
        <p className="text-sm text-muted-foreground">
          This RFQ does not have any line items yet.
        </p>
      </div>
    );
  }

  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-16">#</TableHead>
              <TableHead>Description</TableHead>
              <TableHead className="w-24">Qty</TableHead>
              <TableHead className="w-24">UoM</TableHead>
              <TableHead className="w-28">IMPA Code</TableHead>
              <TableHead>Notes</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {lineItems.map((item) => (
              <TableRow key={item.id}>
                <TableCell className="font-mono text-muted-foreground">
                  {item.line_number}
                </TableCell>
                <TableCell className="font-medium">
                  {item.description}
                </TableCell>
                <TableCell>{item.quantity}</TableCell>
                <TableCell>{item.unit_of_measure}</TableCell>
                <TableCell className="font-mono">
                  {item.impa_code || "---"}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {item.notes || "---"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Invitations Tab
// ---------------------------------------------------------------------------

function InvitationsTab({
  invitations,
  isLoading,
}: {
  invitations: InvitationResponse[];
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  if (invitations.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Send className="mb-4 h-12 w-12 text-muted-foreground" />
        <p className="text-lg font-medium">No invitations</p>
        <p className="text-sm text-muted-foreground">
          No suppliers have been invited to this RFQ yet.
        </p>
      </div>
    );
  }

  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Supplier Org ID</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Invited At</TableHead>
              <TableHead>Responded At</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {invitations.map((invitation) => (
              <TableRow key={invitation.id}>
                <TableCell className="font-mono text-sm">
                  {invitation.supplier_organization_id}
                </TableCell>
                <TableCell>
                  <Badge
                    variant="outline"
                    className={cn(
                      "border-transparent",
                      invitationStatusStyles[invitation.status]
                    )}
                  >
                    {invitation.status.replace(/_/g, " ")}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm">
                  {formatDate(invitation.invited_at)}
                </TableCell>
                <TableCell className="text-sm">
                  {formatDate(invitation.responded_at)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Quotes Tab
// ---------------------------------------------------------------------------

function QuotesTab({
  quotes,
  rfqStatus,
  isLoading,
}: {
  quotes: QuoteResponse[];
  rfqStatus: RfqStatus;
  isLoading: boolean;
}) {
  if (!POST_BIDDING_STATUSES.includes(rfqStatus)) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Clock className="mb-4 h-12 w-12 text-muted-foreground" />
        <p className="text-lg font-medium">
          Quotes visible after bidding closes
        </p>
        <p className="text-sm text-muted-foreground">
          Quote details will be available once the bidding period has ended.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  if (quotes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <FileText className="mb-4 h-12 w-12 text-muted-foreground" />
        <p className="text-lg font-medium">No quotes received</p>
        <p className="text-sm text-muted-foreground">
          No suppliers have submitted quotes for this RFQ.
        </p>
      </div>
    );
  }

  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Supplier Org ID</TableHead>
              <TableHead>Total Amount</TableHead>
              <TableHead>Currency</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="w-16">Ver.</TableHead>
              <TableHead>Submitted At</TableHead>
              <TableHead className="w-16">Rank</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {quotes.map((quote) => (
              <TableRow key={quote.id}>
                <TableCell className="font-mono text-sm">
                  {quote.supplier_organization_id}
                </TableCell>
                <TableCell className="font-medium">
                  {quote.total_amount ?? "---"}
                </TableCell>
                <TableCell>{quote.currency}</TableCell>
                <TableCell>
                  <Badge
                    variant="outline"
                    className={cn(
                      "border-transparent",
                      quoteStatusStyles[quote.status]
                    )}
                  >
                    {quote.status.replace(/_/g, " ")}
                  </Badge>
                </TableCell>
                <TableCell className="text-center">{quote.version}</TableCell>
                <TableCell className="text-sm">
                  {formatDate(quote.submitted_at)}
                </TableCell>
                <TableCell className="text-center font-medium">
                  {quote.price_rank ?? "---"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// History Tab (Vertical Timeline)
// ---------------------------------------------------------------------------

function HistoryTab({
  transitions,
  isLoading,
}: {
  transitions: TransitionResponse[];
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  if (transitions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Calendar className="mb-4 h-12 w-12 text-muted-foreground" />
        <p className="text-lg font-medium">No history</p>
        <p className="text-sm text-muted-foreground">
          No state transitions have been recorded for this RFQ.
        </p>
      </div>
    );
  }

  const sortedTransitions = [...transitions].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="relative space-y-0">
          {sortedTransitions.map((transition, index) => {
            const isLast = index === sortedTransitions.length - 1;
            return (
              <div key={transition.id} className="relative flex gap-4 pb-8">
                {/* Vertical line */}
                {!isLast && (
                  <div className="absolute left-[9px] top-5 h-full w-px bg-border" />
                )}
                {/* Dot */}
                <div className="relative mt-1.5 h-[18px] w-[18px] shrink-0 rounded-full border-2 border-primary bg-background" />
                {/* Content */}
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <RfqStatusBadge status={transition.from_status} className="text-xs" />
                    <ArrowLeft className="h-3 w-3 rotate-180 text-muted-foreground" />
                    <RfqStatusBadge status={transition.to_status} className="text-xs" />
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                    <span>
                      {transition.transition_type.replace(/_/g, " ")}
                    </span>
                    <span className="text-xs">
                      via {transition.trigger_source}
                    </span>
                  </div>
                  {transition.reason && (
                    <p className="text-sm text-muted-foreground italic">
                      {transition.reason}
                    </p>
                  )}
                  <p className="text-xs text-muted-foreground">
                    {formatDate(transition.created_at)}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
