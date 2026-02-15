"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
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

type OrderStatus =
  | "CONFIRMED"
  | "IN_PROGRESS"
  | "PARTIALLY_FULFILLED"
  | "FULFILLED"
  | "COMPLETED"
  | "CANCELLED";

interface OrderItem {
  id: string;
  product_name: string;
  impa_code: string | null;
  quantity: number;
  unit_of_measure: string;
  unit_price: string;
  total_price: string;
}

interface Order {
  id: string;
  order_number: string;
  rfq_reference: string | null;
  buyer_organization_name: string;
  status: OrderStatus;
  vessel_name: string | null;
  delivery_port: string | null;
  delivery_date: string | null;
  total_amount: string;
  currency: string;
  item_count: number;
  items: OrderItem[];
  created_at: string;
  updated_at: string;
}

interface OrderListResponse {
  items: Order[];
  total: number;
  limit: number;
  offset: number;
}

const STATUS_OPTIONS: { label: string; value: OrderStatus | "ALL" }[] = [
  { label: "All Statuses", value: "ALL" },
  { label: "Confirmed", value: "CONFIRMED" },
  { label: "In Progress", value: "IN_PROGRESS" },
  { label: "Partially Fulfilled", value: "PARTIALLY_FULFILLED" },
  { label: "Fulfilled", value: "FULFILLED" },
  { label: "Completed", value: "COMPLETED" },
  { label: "Cancelled", value: "CANCELLED" },
];

const STATUS_COLORS: Record<OrderStatus, string> = {
  CONFIRMED: "bg-blue-100 text-blue-800",
  IN_PROGRESS: "bg-yellow-100 text-yellow-800",
  PARTIALLY_FULFILLED: "bg-orange-100 text-orange-800",
  FULFILLED: "bg-green-100 text-green-800",
  COMPLETED: "bg-gray-100 text-gray-800",
  CANCELLED: "bg-red-100 text-red-800",
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

const PAGE_SIZE = 12;

async function listSupplierOrders(params?: {
  search?: string;
  status?: OrderStatus;
  limit?: number;
  offset?: number;
}): Promise<OrderListResponse> {
  return apiClient.get<OrderListResponse>(
    "/api/v1/supplier/orders",
    params as Record<string, string | number | boolean | undefined>,
  );
}

export default function SupplierOrdersPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<OrderStatus | "ALL">("ALL");
  const [page, setPage] = useState(0);

  const { data, isLoading, error } = useQuery({
    queryKey: ["supplier-orders", searchTerm, statusFilter, page],
    queryFn: () =>
      listSupplierOrders({
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
        <h1 className="text-3xl font-bold tracking-tight">Orders</h1>
        <p className="text-muted-foreground">
          Manage confirmed purchase orders and track fulfillment
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search orders by number or buyer..."
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
              <Link
                key={order.id}
                href={`/supplier/orders/${order.id}`}
              >
                <Card className="cursor-pointer transition-shadow hover:shadow-md">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="text-base leading-tight">
                        {order.buyer_organization_name}
                      </CardTitle>
                      <Badge
                        className={STATUS_COLORS[order.status]}
                        variant="secondary"
                      >
                        {order.status.replace(/_/g, " ")}
                      </Badge>
                    </div>
                    <Badge variant="secondary" className="w-fit font-mono text-xs">
                      {order.order_number}
                    </Badge>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Package className="h-3.5 w-3.5 flex-shrink-0" />
                      <span>
                        {order.item_count} {order.item_count === 1 ? "item" : "items"}
                      </span>
                    </div>

                    {order.delivery_port && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <MapPin className="h-3.5 w-3.5 flex-shrink-0" />
                        <span className="truncate">{order.delivery_port}</span>
                      </div>
                    )}

                    {order.delivery_date && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Calendar className="h-3.5 w-3.5 flex-shrink-0" />
                        <span>Deliver by {formatShortDate(order.delivery_date)}</span>
                      </div>
                    )}

                    <div className="pt-2 text-right text-sm font-semibold">
                      {formatCurrency(order.total_amount, order.currency)}
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
              : "Orders will appear here once RFQs are awarded to you."}
          </p>
        </div>
      )}
    </div>
  );
}
