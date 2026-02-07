"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Separator } from "@/components/ui/separator";
import { SupplierTierBadge } from "./supplier-tier-badge";
import { cn } from "@/lib/utils";
import type {
  SupplierProfileResponse,
  SupplierKycDocumentResponse,
  SupplierReviewLogResponse,
  KycDocumentStatus,
  OnboardingStatus,
} from "@/lib/api/types";

const documentStatusStyles: Record<KycDocumentStatus, string> = {
  PENDING: "bg-yellow-100 text-yellow-700",
  VERIFIED: "bg-green-100 text-green-700",
  REJECTED: "bg-red-100 text-red-700",
  EXPIRED: "bg-gray-100 text-gray-700",
};

function formatOnboardingStatus(status: OnboardingStatus): string {
  return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDocumentType(type: string): string {
  return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatDateTime(dateString: string): string {
  return new Date(dateString).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

interface SupplierDetailProps {
  supplier: SupplierProfileResponse;
  documents: SupplierKycDocumentResponse[];
  reviewLog: SupplierReviewLogResponse[];
}

export function SupplierDetail({ supplier, documents, reviewLog }: SupplierDetailProps) {
  const addressParts = [
    supplier.address_line1,
    supplier.address_line2,
    supplier.city,
    supplier.state,
    supplier.pincode,
    supplier.country,
  ].filter(Boolean);

  return (
    <div className="space-y-6">
      {/* Company Info */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Company Information</CardTitle>
            <div className="flex items-center gap-2">
              <SupplierTierBadge tier={supplier.tier} />
              <Badge
                variant="outline"
                className={cn(
                  "text-xs",
                  supplier.onboarding_status === "APPROVED"
                    ? "bg-green-100 text-green-700"
                    : "bg-yellow-100 text-yellow-700"
                )}
              >
                {formatOnboardingStatus(supplier.onboarding_status)}
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Company Name</dt>
              <dd className="mt-1 text-sm">{supplier.company_name}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Organization</dt>
              <dd className="mt-1 text-sm">{supplier.organization_name || "--"}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Contact Name</dt>
              <dd className="mt-1 text-sm">{supplier.contact_name}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Contact Email</dt>
              <dd className="mt-1 text-sm">{supplier.contact_email}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Contact Phone</dt>
              <dd className="mt-1 text-sm">{supplier.contact_phone || "--"}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Address</dt>
              <dd className="mt-1 text-sm">
                {addressParts.length > 0 ? addressParts.join(", ") : "--"}
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      {/* Verification Details */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Verification Details</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-4 sm:grid-cols-3">
            <div>
              <dt className="text-sm font-medium text-muted-foreground">GST Number</dt>
              <dd className="mt-1 text-sm font-mono">{supplier.gst_number || "--"}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">PAN Number</dt>
              <dd className="mt-1 text-sm font-mono">{supplier.pan_number || "--"}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">CIN Number</dt>
              <dd className="mt-1 text-sm font-mono">{supplier.cin_number || "--"}</dd>
            </div>
          </dl>

          {supplier.categories.length > 0 && (
            <>
              <Separator className="my-4" />
              <div>
                <dt className="text-sm font-medium text-muted-foreground mb-2">Categories</dt>
                <div className="flex flex-wrap gap-1">
                  {supplier.categories.map((category) => (
                    <Badge key={category} variant="secondary" className="text-xs">
                      {category}
                    </Badge>
                  ))}
                </div>
              </div>
            </>
          )}

          {supplier.port_coverage.length > 0 && (
            <>
              <Separator className="my-4" />
              <div>
                <dt className="text-sm font-medium text-muted-foreground mb-2">Port Coverage</dt>
                <div className="flex flex-wrap gap-1">
                  {supplier.port_coverage.map((port) => (
                    <Badge key={port} variant="outline" className="text-xs">
                      {port}
                    </Badge>
                  ))}
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* KYC Documents */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">KYC Documents</CardTitle>
        </CardHeader>
        <CardContent>
          {documents.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No documents uploaded yet
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Document Type</TableHead>
                  <TableHead>File Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Expiry</TableHead>
                  <TableHead>Uploaded</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell className="font-medium">
                      {formatDocumentType(doc.document_type)}
                    </TableCell>
                    <TableCell className="text-sm">{doc.file_name}</TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={cn("text-xs", documentStatusStyles[doc.status])}
                      >
                        {doc.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">
                      {doc.expiry_date ? formatDate(doc.expiry_date) : "--"}
                    </TableCell>
                    <TableCell className="text-sm">
                      {formatDate(doc.created_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Review History */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Review History</CardTitle>
        </CardHeader>
        <CardContent>
          {reviewLog.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No review actions yet
            </p>
          ) : (
            <div className="space-y-4">
              {reviewLog.map((entry, index) => (
                <div key={entry.id} className="relative flex gap-4">
                  {index < reviewLog.length - 1 && (
                    <div className="absolute left-[7px] top-6 bottom-0 w-px bg-border" />
                  )}
                  <div className="mt-1.5 h-3.5 w-3.5 rounded-full border-2 border-primary bg-background flex-shrink-0" />
                  <div className="flex-1 pb-4">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">
                        {entry.action.replace(/_/g, " ")}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {formatDateTime(entry.created_at)}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {formatOnboardingStatus(entry.from_status)} &rarr;{" "}
                      {formatOnboardingStatus(entry.to_status)}
                    </p>
                    {entry.reviewer_name && (
                      <p className="text-xs text-muted-foreground">
                        by {entry.reviewer_name}
                      </p>
                    )}
                    {entry.notes && (
                      <p className="mt-1 text-sm text-muted-foreground">{entry.notes}</p>
                    )}
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
