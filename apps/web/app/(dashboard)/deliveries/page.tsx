"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listDeliveries } from "@/lib/api/deliveries";
import type { DeliveryStatus } from "@/lib/api/deliveries";
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
import { Search, Truck, MapPin, Calendar, Ship } from "lucide-react";
import Link from "next/link";

const STATUS_OPTIONS: { label: string; value: DeliveryStatus | "ALL" }[] = [
  { label: "All Statuses", value: "ALL" },
  { label: "Pending", value: "PENDING" },
  { label: "Dispatched", value: "DISPATCHED" },
  { label: "In Transit", value: "IN_TRANSIT" },
  { label: "Delivered", value: "DELIVERED" },
  { label: "Accepted", value: "ACCEPTED" },
  { label: "Disputed", value: "DISPUTED" },
  { label: "Rejected", value: "REJECTED" },
];

const statusStyles: Record<DeliveryStatus, string> = {
  PENDING: "border-gray-300 bg-gray-100 text-gray-700 hover:bg-gray-100",
  DISPATCHED: "border-transparent bg-blue-100 text-blue-700 hover:bg-blue-100",
  IN_TRANSIT: "border-transparent bg-indigo-100 text-indigo-700 hover:bg-indigo-100",
  DELIVERED: "border-transparent bg-teal-100 text-teal-700 hover:bg-teal-100",
  ACCEPTED: "border-transparent bg-emerald-100 text-emerald-700 hover:bg-emerald-100",
  DISPUTED: "border-transparent bg-amber-100 text-amber-700 hover:bg-amber-100",
  REJECTED: "border-transparent bg-red-100 text-red-700 hover:bg-red-100",
};

const statusLabels: Record<DeliveryStatus, string> = {
  PENDING: "Pending",
  DISPATCHED: "Dispatched",
  IN_TRANSIT: "In Transit",
  DELIVERED: "Delivered",
  ACCEPTED: "Accepted",
  DISPUTED: "Disputed",
  REJECTED: "Rejected",
};

function formatShortDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

const PAGE_SIZE = 12;

export default function DeliveriesPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<DeliveryStatus | "ALL">(
    "ALL",
  );
  const [page, setPage] = useState(0);

  const { data, isLoading, error } = useQuery({
    queryKey: ["deliveries", searchTerm, statusFilter, page],
    queryFn: () =>
      listDeliveries({
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
          <h1 className="text-3xl font-bold tracking-tight">Deliveries</h1>
          <p className="text-muted-foreground">
            Track deliveries and proof-of-delivery
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search deliveries..."
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
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-48 w-full" />
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
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {data.items.map((delivery) => (
              <Link key={delivery.id} href={`/deliveries/${delivery.id}`}>
                <Card className="cursor-pointer transition-shadow hover:shadow-md">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="text-base leading-tight">
                        {delivery.delivery_number}
                      </CardTitle>
                      <Badge
                        variant="outline"
                        className={statusStyles[delivery.status]}
                      >
                        {statusLabels[delivery.status]}
                      </Badge>
                    </div>
                    {delivery.supplier_name && (
                      <p className="text-sm text-muted-foreground">
                        {delivery.supplier_name}
                      </p>
                    )}
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {delivery.vessel_name && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Ship className="h-3.5 w-3.5 flex-shrink-0" />
                        <span className="truncate">{delivery.vessel_name}</span>
                      </div>
                    )}
                    {delivery.delivery_port && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <MapPin className="h-3.5 w-3.5 flex-shrink-0" />
                        <span className="truncate">
                          {delivery.delivery_port}
                        </span>
                      </div>
                    )}
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Calendar className="h-3.5 w-3.5 flex-shrink-0" />
                      <span>
                        {delivery.actual_delivery_date
                          ? `Delivered ${formatShortDate(delivery.actual_delivery_date)}`
                          : delivery.estimated_delivery_date
                            ? `ETA ${formatShortDate(delivery.estimated_delivery_date)}`
                            : `Created ${formatShortDate(delivery.created_at)}`}
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {delivery.items.length}{" "}
                      {delivery.items.length === 1 ? "item" : "items"}
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
          <Truck className="mb-4 h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium">No deliveries found</p>
          <p className="text-sm text-muted-foreground">
            {searchTerm || statusFilter !== "ALL"
              ? "Try adjusting your filters."
              : "Deliveries will appear here once orders are fulfilled."}
          </p>
        </div>
      )}
    </div>
  );
}
