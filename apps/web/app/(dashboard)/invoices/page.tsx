"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listInvoices } from "@/lib/api/invoices";
import type { InvoiceStatus } from "@/lib/api/invoices";
import { Input } from "@/components/ui/input";
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
import { Search, Receipt, Calendar } from "lucide-react";
import Link from "next/link";

const STATUS_OPTIONS: { label: string; value: InvoiceStatus | "ALL" }[] = [
  { label: "All Statuses", value: "ALL" },
  { label: "Draft", value: "DRAFT" },
  { label: "Ready", value: "READY" },
  { label: "Sent", value: "SENT" },
  { label: "Acknowledged", value: "ACKNOWLEDGED" },
  { label: "Disputed", value: "DISPUTED" },
  { label: "Paid", value: "PAID" },
  { label: "Cancelled", value: "CANCELLED" },
];

const statusStyles: Record<InvoiceStatus, string> = {
  DRAFT: "border-gray-300 bg-gray-100 text-gray-700 hover:bg-gray-100",
  READY: "border-transparent bg-blue-100 text-blue-700 hover:bg-blue-100",
  SENT: "border-transparent bg-indigo-100 text-indigo-700 hover:bg-indigo-100",
  ACKNOWLEDGED: "border-transparent bg-purple-100 text-purple-700 hover:bg-purple-100",
  DISPUTED: "border-transparent bg-amber-100 text-amber-700 hover:bg-amber-100",
  PAID: "border-transparent bg-emerald-100 text-emerald-700 hover:bg-emerald-100",
  CANCELLED: "border-transparent bg-red-100 text-red-700 hover:bg-red-100",
};

const statusLabels: Record<InvoiceStatus, string> = {
  DRAFT: "Draft",
  READY: "Ready",
  SENT: "Sent",
  ACKNOWLEDGED: "Acknowledged",
  DISPUTED: "Disputed",
  PAID: "Paid",
  CANCELLED: "Cancelled",
};

function formatShortDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatCurrency(amount: string | null, currency: string): string {
  if (!amount) return "-";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
  }).format(parseFloat(amount));
}

const PAGE_SIZE = 12;

export default function InvoicesPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | "ALL">(
    "ALL",
  );
  const [page, setPage] = useState(0);

  const { data, isLoading, error } = useQuery({
    queryKey: ["invoices", searchTerm, statusFilter, page],
    queryFn: () =>
      listInvoices({
        search: searchTerm || undefined,
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
          <h1 className="text-3xl font-bold tracking-tight">Invoices</h1>
          <p className="text-muted-foreground">
            View and manage supplier invoices
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search invoices by number..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setPage(0);
            }}
            className="pl-9"
          />
        </div>
        <Select
          value={statusFilter}
          onValueChange={(value) => {
            setStatusFilter(value as InvoiceStatus | "ALL");
            setPage(0);
          }}
        >
          <SelectTrigger className="w-[180px]">
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
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Receipt className="mb-4 h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium">Failed to load invoices</p>
          <p className="text-sm text-muted-foreground">
            Please check your connection and try again.
          </p>
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {data.items.map((invoice) => (
              <Link key={invoice.id} href={`/invoices/${invoice.id}`}>
                <Card className="cursor-pointer transition-shadow hover:shadow-md">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="text-base leading-tight">
                        {invoice.invoice_number}
                      </CardTitle>
                      <Badge
                        variant="outline"
                        className={statusStyles[invoice.status]}
                      >
                        {statusLabels[invoice.status]}
                      </Badge>
                    </div>
                    {invoice.supplier_name && (
                      <p className="text-sm text-muted-foreground">
                        {invoice.supplier_name}
                      </p>
                    )}
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="text-lg font-semibold">
                      {formatCurrency(invoice.total_amount, invoice.currency)}
                    </div>
                    {invoice.due_date && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Calendar className="h-3.5 w-3.5 flex-shrink-0" />
                        <span>Due {formatShortDate(invoice.due_date)}</span>
                      </div>
                    )}
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Calendar className="h-3.5 w-3.5 flex-shrink-0" />
                      <span>
                        Created {formatShortDate(invoice.created_at)}
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {invoice.line_items.length}{" "}
                      {invoice.line_items.length === 1
                        ? "line item"
                        : "line items"}
                    </div>
                  </CardContent>
                </Card>
              </Link>
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
          <Receipt className="mb-4 h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium">No invoices found</p>
          <p className="text-sm text-muted-foreground">
            {searchTerm || statusFilter !== "ALL"
              ? "Try adjusting your filters."
              : "Invoices will appear here once deliveries are completed."}
          </p>
        </div>
      )}
    </div>
  );
}
