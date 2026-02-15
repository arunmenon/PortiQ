"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listOrders } from "@/lib/api/orders";
import type { OrderStatus } from "@/lib/api/orders";
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
import { Search, ShoppingCart, MapPin, Calendar, Package } from "lucide-react";
import Link from "next/link";

const STATUS_OPTIONS: { label: string; value: OrderStatus | "ALL" }[] = [
  { label: "All Statuses", value: "ALL" },
  { label: "Draft", value: "DRAFT" },
  { label: "Confirmed", value: "CONFIRMED" },
  { label: "Partially Fulfilled", value: "PARTIALLY_FULFILLED" },
  { label: "Fulfilled", value: "FULFILLED" },
  { label: "Completed", value: "COMPLETED" },
  { label: "Cancelled", value: "CANCELLED" },
];

const statusStyles: Record<OrderStatus, string> = {
  DRAFT: "border-gray-300 bg-gray-100 text-gray-700 hover:bg-gray-100",
  CONFIRMED: "border-transparent bg-blue-100 text-blue-700 hover:bg-blue-100",
  PARTIALLY_FULFILLED: "border-transparent bg-amber-100 text-amber-700 hover:bg-amber-100",
  FULFILLED: "border-transparent bg-indigo-100 text-indigo-700 hover:bg-indigo-100",
  COMPLETED: "border-transparent bg-emerald-100 text-emerald-700 hover:bg-emerald-100",
  CANCELLED: "border-transparent bg-red-100 text-red-700 hover:bg-red-100",
};

const statusLabels: Record<OrderStatus, string> = {
  DRAFT: "Draft",
  CONFIRMED: "Confirmed",
  PARTIALLY_FULFILLED: "Partially Fulfilled",
  FULFILLED: "Fulfilled",
  COMPLETED: "Completed",
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

export default function OrdersPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<OrderStatus | "ALL">("ALL");
  const [page, setPage] = useState(0);

  const { data, isLoading, error } = useQuery({
    queryKey: ["orders", searchTerm, statusFilter, page],
    queryFn: () =>
      listOrders({
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
          <h1 className="text-3xl font-bold tracking-tight">Orders</h1>
          <p className="text-muted-foreground">
            Track purchase orders and fulfillment
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search orders by reference..."
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
            setStatusFilter(value as OrderStatus | "ALL");
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
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <ShoppingCart className="mb-4 h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium">Failed to load orders</p>
          <p className="text-sm text-muted-foreground">
            Please check your connection and try again.
          </p>
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {data.items.map((order) => (
              <Link key={order.id} href={`/orders/${order.id}`}>
                <Card className="cursor-pointer transition-shadow hover:shadow-md">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="text-base leading-tight">
                        {order.reference_number}
                      </CardTitle>
                      <Badge
                        variant="outline"
                        className={statusStyles[order.status]}
                      >
                        {statusLabels[order.status]}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {formatCurrency(order.total_amount, order.currency)}
                    </p>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {order.vessel_name && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Package className="h-3.5 w-3.5 flex-shrink-0" />
                        <span className="truncate">{order.vessel_name}</span>
                      </div>
                    )}
                    {order.delivery_port && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <MapPin className="h-3.5 w-3.5 flex-shrink-0" />
                        <span className="truncate">{order.delivery_port}</span>
                      </div>
                    )}
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Calendar className="h-3.5 w-3.5 flex-shrink-0" />
                      <span>Created {formatShortDate(order.created_at)}</span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {order.vendor_orders.length} vendor{" "}
                      {order.vendor_orders.length === 1 ? "order" : "orders"}
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
          <ShoppingCart className="mb-4 h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium">No orders found</p>
          <p className="text-sm text-muted-foreground">
            {searchTerm || statusFilter !== "ALL"
              ? "Try adjusting your filters."
              : "Orders will appear here once RFQs are awarded."}
          </p>
        </div>
      )}
    </div>
  );
}
