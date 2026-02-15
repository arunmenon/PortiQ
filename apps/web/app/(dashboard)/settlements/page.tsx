"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listSettlements } from "@/lib/api/invoices";
import type { SettlementStatus } from "@/lib/api/invoices";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Wallet, Calendar, Receipt } from "lucide-react";

const STATUS_OPTIONS: { label: string; value: SettlementStatus | "ALL" }[] = [
  { label: "All Statuses", value: "ALL" },
  { label: "Open", value: "OPEN" },
  { label: "Pending Review", value: "PENDING_REVIEW" },
  { label: "Approved", value: "APPROVED" },
  { label: "Settled", value: "SETTLED" },
  { label: "Closed", value: "CLOSED" },
];

const statusStyles: Record<SettlementStatus, string> = {
  OPEN: "border-transparent bg-blue-100 text-blue-700 hover:bg-blue-100",
  PENDING_REVIEW: "border-transparent bg-amber-100 text-amber-700 hover:bg-amber-100",
  APPROVED: "border-transparent bg-purple-100 text-purple-700 hover:bg-purple-100",
  SETTLED: "border-transparent bg-emerald-100 text-emerald-700 hover:bg-emerald-100",
  CLOSED: "border-gray-300 bg-gray-100 text-gray-700 hover:bg-gray-100",
};

const statusLabels: Record<SettlementStatus, string> = {
  OPEN: "Open",
  PENDING_REVIEW: "Pending Review",
  APPROVED: "Approved",
  SETTLED: "Settled",
  CLOSED: "Closed",
};

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatCurrency(amount: string, currency: string): string {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
  }).format(parseFloat(amount));
}

const PAGE_SIZE = 12;

export default function SettlementsPage() {
  const [statusFilter, setStatusFilter] = useState<SettlementStatus | "ALL">(
    "ALL",
  );
  const [page, setPage] = useState(0);

  const { data, isLoading, error } = useQuery({
    queryKey: ["settlements", statusFilter, page],
    queryFn: () =>
      listSettlements({
        status: statusFilter === "ALL" ? undefined : statusFilter,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Settlements</h1>
          <p className="text-muted-foreground">
            Settlement period summaries and financial overview
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Select
          value={statusFilter}
          onValueChange={(value) => {
            setStatusFilter(value as SettlementStatus | "ALL");
            setPage(0);
          }}
        >
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-56 w-full" />
          ))}
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Wallet className="mb-4 h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium">Failed to load settlements</p>
          <p className="text-sm text-muted-foreground">
            Please check your connection and try again.
          </p>
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {data.items.map((settlement) => (
              <Card key={settlement.id}>
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="text-base leading-tight">
                      {formatDate(settlement.period_start)} -{" "}
                      {formatDate(settlement.period_end)}
                    </CardTitle>
                    <Badge
                      variant="outline"
                      className={statusStyles[settlement.status]}
                    >
                      {statusLabels[settlement.status]}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="text-sm">
                      <p className="text-muted-foreground">Total Invoiced</p>
                      <p className="font-semibold">
                        {formatCurrency(
                          settlement.total_invoiced,
                          settlement.currency,
                        )}
                      </p>
                    </div>
                    <div className="text-sm">
                      <p className="text-muted-foreground">Total Paid</p>
                      <p className="font-semibold text-emerald-600">
                        {formatCurrency(
                          settlement.total_paid,
                          settlement.currency,
                        )}
                      </p>
                    </div>
                    <div className="text-sm">
                      <p className="text-muted-foreground">Outstanding</p>
                      <p className="font-semibold text-amber-600">
                        {formatCurrency(
                          settlement.total_outstanding,
                          settlement.currency,
                        )}
                      </p>
                    </div>
                    <div className="text-sm">
                      <p className="text-muted-foreground">Credits</p>
                      <p className="font-semibold">
                        {formatCurrency(
                          settlement.total_credit,
                          settlement.currency,
                        )}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Receipt className="h-3.5 w-3.5 flex-shrink-0" />
                    <span>
                      {settlement.invoice_count}{" "}
                      {settlement.invoice_count === 1
                        ? "invoice"
                        : "invoices"}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Calendar className="h-3.5 w-3.5 flex-shrink-0" />
                    <span>Updated {formatDate(settlement.updated_at)}</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 0}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page + 1} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page + 1 >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      ) : (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Wallet className="mb-4 h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium">No settlements found</p>
          <p className="text-sm text-muted-foreground">
            {statusFilter !== "ALL"
              ? "Try adjusting your filter."
              : "Settlement periods will appear once invoices are generated."}
          </p>
        </div>
      )}
    </div>
  );
}
