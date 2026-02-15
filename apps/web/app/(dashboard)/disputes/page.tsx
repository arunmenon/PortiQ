"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listDisputes } from "@/lib/api/disputes";
import type { DisputeStatus, DisputeType } from "@/lib/api/disputes";
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
import { Search, AlertTriangle, Calendar, MessageSquare } from "lucide-react";
import Link from "next/link";

const STATUS_OPTIONS: { label: string; value: DisputeStatus | "ALL" }[] = [
  { label: "All Statuses", value: "ALL" },
  { label: "Open", value: "OPEN" },
  { label: "Under Review", value: "UNDER_REVIEW" },
  { label: "Awaiting Response", value: "AWAITING_RESPONSE" },
  { label: "Resolved", value: "RESOLVED" },
  { label: "Escalated", value: "ESCALATED" },
  { label: "Closed", value: "CLOSED" },
];

const TYPE_OPTIONS: { label: string; value: DisputeType | "ALL" }[] = [
  { label: "All Types", value: "ALL" },
  { label: "Quantity Mismatch", value: "QUANTITY_MISMATCH" },
  { label: "Quality Issue", value: "QUALITY_ISSUE" },
  { label: "Damaged Goods", value: "DAMAGED_GOODS" },
  { label: "Wrong Items", value: "WRONG_ITEMS" },
  { label: "Pricing Discrepancy", value: "PRICING_DISCREPANCY" },
  { label: "Late Delivery", value: "LATE_DELIVERY" },
  { label: "Other", value: "OTHER" },
];

const statusStyles: Record<DisputeStatus, string> = {
  OPEN: "border-transparent bg-blue-100 text-blue-700 hover:bg-blue-100",
  UNDER_REVIEW: "border-transparent bg-purple-100 text-purple-700 hover:bg-purple-100",
  AWAITING_RESPONSE: "border-transparent bg-amber-100 text-amber-700 hover:bg-amber-100",
  RESOLVED: "border-transparent bg-emerald-100 text-emerald-700 hover:bg-emerald-100",
  ESCALATED: "border-transparent bg-red-100 text-red-700 hover:bg-red-100",
  CLOSED: "border-gray-300 bg-gray-100 text-gray-700 hover:bg-gray-100",
};

const statusLabels: Record<DisputeStatus, string> = {
  OPEN: "Open",
  UNDER_REVIEW: "Under Review",
  AWAITING_RESPONSE: "Awaiting Response",
  RESOLVED: "Resolved",
  ESCALATED: "Escalated",
  CLOSED: "Closed",
};

const typeLabels: Record<DisputeType, string> = {
  QUANTITY_MISMATCH: "Quantity Mismatch",
  QUALITY_ISSUE: "Quality Issue",
  DAMAGED_GOODS: "Damaged Goods",
  WRONG_ITEMS: "Wrong Items",
  PRICING_DISCREPANCY: "Pricing Discrepancy",
  LATE_DELIVERY: "Late Delivery",
  OTHER: "Other",
};

function formatShortDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

const PAGE_SIZE = 12;

export default function DisputesPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<DisputeStatus | "ALL">(
    "ALL",
  );
  const [typeFilter, setTypeFilter] = useState<DisputeType | "ALL">("ALL");
  const [page, setPage] = useState(0);

  const { data, isLoading, error } = useQuery({
    queryKey: ["disputes", searchTerm, statusFilter, typeFilter, page],
    queryFn: () =>
      listDisputes({
        search: searchTerm || undefined,
        status: statusFilter === "ALL" ? undefined : statusFilter,
        dispute_type: typeFilter === "ALL" ? undefined : typeFilter,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Disputes</h1>
          <p className="text-muted-foreground">
            Manage delivery and invoice disputes
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search disputes..."
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
            setStatusFilter(value as DisputeStatus | "ALL");
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
        <Select
          value={typeFilter}
          onValueChange={(value) => {
            setTypeFilter(value as DisputeType | "ALL");
            setPage(0);
          }}
        >
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            {TYPE_OPTIONS.map((option) => (
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
          <AlertTriangle className="mb-4 h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium">Failed to load disputes</p>
          <p className="text-sm text-muted-foreground">
            Please check your connection and try again.
          </p>
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {data.items.map((dispute) => (
              <Link key={dispute.id} href={`/disputes/${dispute.id}`}>
                <Card className="cursor-pointer transition-shadow hover:shadow-md">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="text-base leading-tight">
                        {dispute.title}
                      </CardTitle>
                      <Badge
                        variant="outline"
                        className={statusStyles[dispute.status]}
                      >
                        {statusLabels[dispute.status]}
                      </Badge>
                    </div>
                    <Badge variant="secondary" className="w-fit text-xs">
                      {dispute.dispute_number}
                    </Badge>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <Badge variant="outline" className="text-xs">
                      {typeLabels[dispute.dispute_type]}
                    </Badge>
                    {dispute.raised_by_name && (
                      <p className="text-sm text-muted-foreground">
                        Raised by {dispute.raised_by_name}
                      </p>
                    )}
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <MessageSquare className="h-3.5 w-3.5 flex-shrink-0" />
                      <span>
                        {dispute.comments.length}{" "}
                        {dispute.comments.length === 1
                          ? "comment"
                          : "comments"}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Calendar className="h-3.5 w-3.5 flex-shrink-0" />
                      <span>
                        Created {formatShortDate(dispute.created_at)}
                      </span>
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
          <AlertTriangle className="mb-4 h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium">No disputes found</p>
          <p className="text-sm text-muted-foreground">
            {searchTerm || statusFilter !== "ALL" || typeFilter !== "ALL"
              ? "Try adjusting your filters."
              : "No disputes have been raised yet."}
          </p>
        </div>
      )}
    </div>
  );
}
