"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listSuppliers } from "@/lib/api/suppliers";
import { SupplierCard } from "@/components/suppliers/supplier-card";
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
import { Search, Users } from "lucide-react";
import type { SupplierTier, OnboardingStatus } from "@/lib/api/types";

const TIER_OPTIONS: { label: string; value: SupplierTier | "ALL" }[] = [
  { label: "All Tiers", value: "ALL" },
  { label: "Pending", value: "PENDING" },
  { label: "Basic", value: "BASIC" },
  { label: "Verified", value: "VERIFIED" },
  { label: "Preferred", value: "PREFERRED" },
  { label: "Premium", value: "PREMIUM" },
];

const STATUS_OPTIONS: { label: string; value: OnboardingStatus | "ALL" }[] = [
  { label: "All Statuses", value: "ALL" },
  { label: "Started", value: "STARTED" },
  { label: "Documents Pending", value: "DOCUMENTS_PENDING" },
  { label: "Documents Submitted", value: "DOCUMENTS_SUBMITTED" },
  { label: "Verification In Progress", value: "VERIFICATION_IN_PROGRESS" },
  { label: "Verification Passed", value: "VERIFICATION_PASSED" },
  { label: "Approved", value: "APPROVED" },
  { label: "Rejected", value: "REJECTED" },
  { label: "Suspended", value: "SUSPENDED" },
];

const PAGE_SIZE = 12;

export default function SuppliersPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [tierFilter, setTierFilter] = useState<SupplierTier | "ALL">("ALL");
  const [statusFilter, setStatusFilter] = useState<OnboardingStatus | "ALL">("ALL");
  const [page, setPage] = useState(0);

  const { data, isLoading, error } = useQuery({
    queryKey: ["suppliers", searchTerm, tierFilter, statusFilter, page],
    queryFn: () =>
      listSuppliers({
        search: searchTerm || undefined,
        tier: tierFilter === "ALL" ? undefined : tierFilter,
        onboarding_status: statusFilter === "ALL" ? undefined : statusFilter,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Suppliers</h1>
        <p className="text-muted-foreground">
          Manage supplier profiles and onboarding
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search suppliers by name or email..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setPage(0);
            }}
            className="pl-9"
          />
        </div>
        <Select
          value={tierFilter}
          onValueChange={(value) => {
            setTierFilter(value as SupplierTier | "ALL");
            setPage(0);
          }}
        >
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Tier" />
          </SelectTrigger>
          <SelectContent>
            {TIER_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={statusFilter}
          onValueChange={(value) => {
            setStatusFilter(value as OnboardingStatus | "ALL");
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
          <Users className="mb-4 h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium">Failed to load suppliers</p>
          <p className="text-sm text-muted-foreground">
            Please check your connection and try again.
          </p>
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {data.items.map((supplier) => (
              <SupplierCard key={supplier.id} supplier={supplier} />
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
          <Users className="mb-4 h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium">No suppliers found</p>
          <p className="text-sm text-muted-foreground">
            {searchTerm || tierFilter !== "ALL" || statusFilter !== "ALL"
              ? "Try adjusting your filters."
              : "Suppliers will appear here once they begin onboarding."}
          </p>
        </div>
      )}
    </div>
  );
}
