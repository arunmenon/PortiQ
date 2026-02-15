"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Search, Receipt, Eye } from "lucide-react";
import Link from "next/link";

type InvoiceStatus =
  | "DRAFT"
  | "GENERATED"
  | "SENT"
  | "ACKNOWLEDGED"
  | "DISPUTED"
  | "PAID"
  | "CANCELLED";

interface Invoice {
  id: string;
  invoice_number: string;
  order_number: string;
  buyer_organization_name: string;
  status: InvoiceStatus;
  total_amount: string;
  currency: string;
  due_date: string | null;
  paid_at: string | null;
  created_at: string;
}

interface InvoiceListResponse {
  items: Invoice[];
  total: number;
  limit: number;
  offset: number;
}

const STATUS_OPTIONS: { label: string; value: InvoiceStatus | "ALL" }[] = [
  { label: "All Statuses", value: "ALL" },
  { label: "Draft", value: "DRAFT" },
  { label: "Generated", value: "GENERATED" },
  { label: "Sent", value: "SENT" },
  { label: "Acknowledged", value: "ACKNOWLEDGED" },
  { label: "Disputed", value: "DISPUTED" },
  { label: "Paid", value: "PAID" },
  { label: "Cancelled", value: "CANCELLED" },
];

const STATUS_COLORS: Record<InvoiceStatus, string> = {
  DRAFT: "bg-gray-100 text-gray-800",
  GENERATED: "bg-blue-100 text-blue-800",
  SENT: "bg-indigo-100 text-indigo-800",
  ACKNOWLEDGED: "bg-yellow-100 text-yellow-800",
  DISPUTED: "bg-red-100 text-red-800",
  PAID: "bg-green-100 text-green-800",
  CANCELLED: "bg-gray-100 text-gray-600",
};

function formatShortDate(dateString: string): string {
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

const PAGE_SIZE = 20;

async function listSupplierInvoices(params?: {
  search?: string;
  status?: InvoiceStatus;
  limit?: number;
  offset?: number;
}): Promise<InvoiceListResponse> {
  return apiClient.get<InvoiceListResponse>(
    "/api/v1/supplier/invoices",
    params as Record<string, string | number | boolean | undefined>,
  );
}

export default function SupplierInvoicesPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | "ALL">(
    "ALL",
  );
  const [page, setPage] = useState(0);

  const { data, isLoading, error } = useQuery({
    queryKey: ["supplier-invoices", searchTerm, statusFilter, page],
    queryFn: () =>
      listSupplierInvoices({
        search: searchTerm || undefined,
        status: statusFilter === "ALL" ? undefined : statusFilter,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Invoices</h1>
        <p className="text-muted-foreground">
          Track generated invoices and payment status
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search invoices by number or buyer..."
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
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
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
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Invoice #</TableHead>
                  <TableHead>Order</TableHead>
                  <TableHead>Buyer</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead className="w-[60px]" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((invoice) => (
                  <TableRow key={invoice.id}>
                    <TableCell className="font-mono text-sm font-medium">
                      {invoice.invoice_number}
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {invoice.order_number}
                    </TableCell>
                    <TableCell>{invoice.buyer_organization_name}</TableCell>
                    <TableCell className="text-right font-medium">
                      {formatCurrency(invoice.total_amount, invoice.currency)}
                    </TableCell>
                    <TableCell>
                      <Badge
                        className={STATUS_COLORS[invoice.status]}
                        variant="secondary"
                      >
                        {invoice.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {invoice.due_date
                        ? formatShortDate(invoice.due_date)
                        : "-"}
                    </TableCell>
                    <TableCell>
                      <Button variant="ghost" size="icon" asChild>
                        <Link href={`/supplier/invoices/${invoice.id}`}>
                          <Eye className="h-4 w-4" />
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
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
              : "Invoices will be generated automatically after deliveries are accepted."}
          </p>
        </div>
      )}
    </div>
  );
}
