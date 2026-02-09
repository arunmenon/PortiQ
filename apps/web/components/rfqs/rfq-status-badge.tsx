import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { RfqStatus } from "@/lib/api/types";

const statusStyles: Record<RfqStatus, string> = {
  DRAFT: "border-gray-300 bg-gray-100 text-gray-700 hover:bg-gray-100",
  PUBLISHED: "border-transparent bg-blue-100 text-blue-700 hover:bg-blue-100",
  BIDDING_OPEN: "border-transparent bg-indigo-100 text-indigo-700 hover:bg-indigo-100",
  BIDDING_CLOSED: "border-transparent bg-amber-100 text-amber-700 hover:bg-amber-100",
  EVALUATION: "border-transparent bg-purple-100 text-purple-700 hover:bg-purple-100",
  AWARDED: "border-transparent bg-green-100 text-green-700 hover:bg-green-100",
  COMPLETED: "border-transparent bg-emerald-100 text-emerald-700 hover:bg-emerald-100",
  CANCELLED: "border-transparent bg-red-100 text-red-700 hover:bg-red-100",
};

const statusLabels: Record<RfqStatus, string> = {
  DRAFT: "Draft",
  PUBLISHED: "Published",
  BIDDING_OPEN: "Bidding Open",
  BIDDING_CLOSED: "Bidding Closed",
  EVALUATION: "Evaluation",
  AWARDED: "Awarded",
  COMPLETED: "Completed",
  CANCELLED: "Cancelled",
};

interface RfqStatusBadgeProps {
  status: RfqStatus;
  className?: string;
}

export function RfqStatusBadge({ status, className }: RfqStatusBadgeProps) {
  return (
    <Badge variant="outline" className={cn(statusStyles[status], className)}>
      {statusLabels[status]}
    </Badge>
  );
}
