"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { getDispute } from "@/lib/api/disputes";
import type { DisputeStatus, DisputeType } from "@/lib/api/disputes";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  ArrowLeft,
  AlertTriangle,
  Calendar,
  User,
  MessageSquare,
} from "lucide-react";
import Link from "next/link";

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

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatDateTime(dateString: string): string {
  return new Date(dateString).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function DisputeDetailPage() {
  const params = useParams();
  const { data: dispute, isLoading } = useQuery({
    queryKey: ["dispute", params.id],
    queryFn: () => getDispute(params.id as string),
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!dispute) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <AlertTriangle className="mb-4 h-12 w-12 text-muted-foreground" />
        <p className="text-lg font-medium">Dispute not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/disputes">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Disputes
          </Link>
        </Button>
      </div>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {dispute.title}
          </h1>
          <div className="mt-1 flex items-center gap-2">
            <Badge variant="secondary" className="font-mono text-xs">
              {dispute.dispute_number}
            </Badge>
            <Badge variant="outline" className="text-xs">
              {typeLabels[dispute.dispute_type]}
            </Badge>
          </div>
        </div>
        <Badge variant="outline" className={statusStyles[dispute.status]}>
          {statusLabels[dispute.status]}
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Dispute Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {dispute.raised_by_name && (
              <div className="flex items-center gap-2 text-sm">
                <User className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-muted-foreground">Raised By</p>
                  <p className="font-medium">{dispute.raised_by_name}</p>
                </div>
              </div>
            )}
            {dispute.assigned_to_name && (
              <div className="flex items-center gap-2 text-sm">
                <User className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-muted-foreground">Assigned To</p>
                  <p className="font-medium">{dispute.assigned_to_name}</p>
                </div>
              </div>
            )}
            <div className="flex items-center gap-2 text-sm">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-muted-foreground">Created</p>
                <p className="font-medium">{formatDate(dispute.created_at)}</p>
              </div>
            </div>
            {dispute.resolved_at && (
              <div className="flex items-center gap-2 text-sm">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-muted-foreground">Resolved</p>
                  <p className="font-medium">
                    {formatDate(dispute.resolved_at)}
                  </p>
                </div>
              </div>
            )}
          </div>
          <div className="text-sm">
            <p className="text-muted-foreground">Description</p>
            <p className="mt-1 whitespace-pre-wrap">{dispute.description}</p>
          </div>
          {dispute.resolution && (
            <div className="text-sm">
              <p className="text-muted-foreground">Resolution</p>
              <p className="mt-1 whitespace-pre-wrap">{dispute.resolution}</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            <CardTitle>
              Comments ({dispute.comments.length})
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {dispute.comments.length === 0 ? (
            <p className="text-sm text-muted-foreground">No comments yet.</p>
          ) : (
            <div className="space-y-4">
              {dispute.comments.map((comment, index) => (
                <div key={comment.id}>
                  {index > 0 && <Separator className="mb-4" />}
                  <div className="flex items-start gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
                      <User className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium">
                          {comment.author_name || "Unknown"}
                        </p>
                        <span className="text-xs text-muted-foreground">
                          {formatDateTime(comment.created_at)}
                        </span>
                      </div>
                      <p className="mt-1 text-sm whitespace-pre-wrap">
                        {comment.content}
                      </p>
                      {comment.attachment_keys.length > 0 && (
                        <div className="mt-2 text-xs text-muted-foreground">
                          {comment.attachment_keys.length}{" "}
                          {comment.attachment_keys.length === 1
                            ? "attachment"
                            : "attachments"}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
