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
import { Search, Truck, Eye } from "lucide-react";
import Link from "next/link";

type DeliveryStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "IN_TRANSIT"
  | "DELIVERED"
  | "ACCEPTED"
  | "DISPUTED"
  | "CANCELLED";

interface Delivery {
  id: string;
  delivery_number: string;
  order_id: string;
  order_number: string;
  buyer_organization_name: string;
  status: DeliveryStatus;
  vessel_name: string | null;
  delivery_port: string | null;
  submitted_at: string | null;
  delivered_at: string | null;
  item_count: number;
  created_at: string;
}

interface DeliveryListResponse {
  items: Delivery[];
  total: number;
  limit: number;
  offset: number;
}

const STATUS_OPTIONS: { label: string; value: DeliveryStatus | "ALL" }[] = [
  { label: "All Statuses", value: "ALL" },
  { label: "Draft", value: "DRAFT" },
  { label: "Submitted", value: "SUBMITTED" },
  { label: "In Transit", value: "IN_TRANSIT" },
  { label: "Delivered", value: "DELIVERED" },
  { label: "Accepted", value: "ACCEPTED" },
  { label: "Disputed", value: "DISPUTED" },
  { label: "Cancelled", value: "CANCELLED" },
];

const STATUS_COLORS: Record<DeliveryStatus, string> = {
  DRAFT: "bg-gray-100 text-gray-800",
  SUBMITTED: "bg-blue-100 text-blue-800",
  IN_TRANSIT: "bg-yellow-100 text-yellow-800",
  DELIVERED: "bg-green-100 text-green-800",
  ACCEPTED: "bg-emerald-100 text-emerald-800",
  DISPUTED: "bg-red-100 text-red-800",
  CANCELLED: "bg-gray-100 text-gray-600",
};

function formatShortDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

const PAGE_SIZE = 20;

async function listSupplierDeliveries(params?: {
  search?: string;
  status?: DeliveryStatus;
  limit?: number;
  offset?: number;
}): Promise<DeliveryListResponse> {
  return apiClient.get<DeliveryListResponse>(
    "/api/v1/supplier/deliveries",
    params as Record<string, string | number | boolean | undefined>,
  );
}

export default function SupplierDeliveriesPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<DeliveryStatus | "ALL">(
    "ALL",
  );
  const [page, setPage] = useState(0);

  const { data, isLoading, error } = useQuery({
    queryKey: ["supplier-deliveries", searchTerm, statusFilter, page],
    queryFn: () =>
      listSupplierDeliveries({
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
        <h1 className="text-3xl font-bold tracking-tight">Deliveries</h1>
        <p className="text-muted-foreground">
          Track and manage your delivery submissions
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by delivery number, order, or buyer..."
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
            setStatusFilter(value as DeliveryStatus | "ALL");
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
          <Truck className="mb-4 h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium">Failed to load deliveries</p>
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
                  <TableHead>Delivery #</TableHead>
                  <TableHead>Order</TableHead>
                  <TableHead>Buyer</TableHead>
                  <TableHead>Port</TableHead>
                  <TableHead>Items</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="w-[60px]" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((delivery) => (
                  <TableRow key={delivery.id}>
                    <TableCell className="font-mono text-sm font-medium">
                      {delivery.delivery_number}
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {delivery.order_number}
                    </TableCell>
                    <TableCell>{delivery.buyer_organization_name}</TableCell>
                    <TableCell>{delivery.delivery_port || "-"}</TableCell>
                    <TableCell>{delivery.item_count}</TableCell>
                    <TableCell>
                      <Badge
                        className={STATUS_COLORS[delivery.status]}
                        variant="secondary"
                      >
                        {delivery.status.replace(/_/g, " ")}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {delivery.submitted_at
                        ? formatShortDate(delivery.submitted_at)
                        : formatShortDate(delivery.created_at)}
                    </TableCell>
                    <TableCell>
                      <Button variant="ghost" size="icon" asChild>
                        <Link href={`/supplier/deliveries/${delivery.id}`}>
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
          <Truck className="mb-4 h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium">No deliveries found</p>
          <p className="text-sm text-muted-foreground">
            {searchTerm || statusFilter !== "ALL"
              ? "Try adjusting your filters."
              : "Deliveries will appear here when you fulfill orders."}
          </p>
        </div>
      )}
    </div>
  );
}
