"use client";

import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SupplierTierBadge } from "./supplier-tier-badge";
import { MapPin, Mail, User } from "lucide-react";
import type { SupplierProfileResponse, OnboardingStatus } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const onboardingStatusStyles: Record<string, string> = {
  APPROVED: "bg-green-100 text-green-700",
  VERIFICATION_PASSED: "bg-green-100 text-green-700",
  STARTED: "bg-gray-100 text-gray-700",
  DOCUMENTS_PENDING: "bg-yellow-100 text-yellow-700",
  DOCUMENTS_SUBMITTED: "bg-blue-100 text-blue-700",
  VERIFICATION_IN_PROGRESS: "bg-blue-100 text-blue-700",
  VERIFICATION_FAILED: "bg-red-100 text-red-700",
  MANUAL_REVIEW_PENDING: "bg-yellow-100 text-yellow-700",
  MANUAL_REVIEW_IN_PROGRESS: "bg-blue-100 text-blue-700",
  REJECTED: "bg-red-100 text-red-700",
  SUSPENDED: "bg-red-100 text-red-700",
};

function formatOnboardingStatus(status: OnboardingStatus): string {
  return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

interface SupplierCardProps {
  supplier: SupplierProfileResponse;
}

export function SupplierCard({ supplier }: SupplierCardProps) {
  const router = useRouter();

  return (
    <Card
      className="cursor-pointer transition-shadow hover:shadow-md"
      onClick={() => router.push(`/suppliers/${supplier.id}`)}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base leading-tight">
            {supplier.company_name}
          </CardTitle>
          <SupplierTierBadge tier={supplier.tier} />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <User className="h-3.5 w-3.5 flex-shrink-0" />
          <span className="truncate">{supplier.contact_name}</span>
        </div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Mail className="h-3.5 w-3.5 flex-shrink-0" />
          <span className="truncate">{supplier.contact_email}</span>
        </div>

        {supplier.port_coverage.length > 0 && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <MapPin className="h-3.5 w-3.5 flex-shrink-0" />
            <span className="truncate">{supplier.port_coverage.join(", ")}</span>
          </div>
        )}

        <div className="flex items-center gap-2 pt-1">
          <Badge
            variant="outline"
            className={cn(
              "text-xs",
              onboardingStatusStyles[supplier.onboarding_status] || "bg-gray-100 text-gray-700"
            )}
          >
            {formatOnboardingStatus(supplier.onboarding_status)}
          </Badge>
        </div>

        {supplier.categories.length > 0 && (
          <div className="flex flex-wrap gap-1 pt-1">
            {supplier.categories.slice(0, 3).map((category) => (
              <Badge key={category} variant="secondary" className="text-xs">
                {category}
              </Badge>
            ))}
            {supplier.categories.length > 3 && (
              <Badge variant="secondary" className="text-xs">
                +{supplier.categories.length - 3}
              </Badge>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
