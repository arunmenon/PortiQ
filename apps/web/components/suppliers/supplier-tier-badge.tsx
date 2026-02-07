import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { SupplierTier } from "@/lib/api/types";

const tierStyles: Record<SupplierTier, string> = {
  PENDING: "border-gray-300 bg-gray-100 text-gray-700 hover:bg-gray-100",
  BASIC: "border-transparent bg-blue-100 text-blue-700 hover:bg-blue-100",
  VERIFIED: "border-transparent bg-green-100 text-green-700 hover:bg-green-100",
  PREFERRED: "border-transparent bg-amber-100 text-amber-700 hover:bg-amber-100",
  PREMIUM: "border-transparent bg-purple-100 text-purple-700 hover:bg-purple-100",
};

interface SupplierTierBadgeProps {
  tier: SupplierTier;
  className?: string;
}

export function SupplierTierBadge({ tier, className }: SupplierTierBadgeProps) {
  return (
    <Badge variant="outline" className={cn(tierStyles[tier], className)}>
      {tier}
    </Badge>
  );
}
