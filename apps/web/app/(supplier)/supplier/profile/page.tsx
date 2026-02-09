"use client";

import { useQuery } from "@tanstack/react-query";
import { getMyProfile, getMyDocuments, getMyTierCapabilities } from "@/lib/api/supplier-portal";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Building2,
  Mail,
  Phone,
  MapPin,
  Shield,
  FileCheck,
  Award,
} from "lucide-react";
import type { SupplierTier, KycDocumentStatus } from "@/lib/api/types";

// TODO: In a real app, the supplier ID would come from auth context
const PLACEHOLDER_SUPPLIER_ID = "";

const tierColors: Record<SupplierTier, string> = {
  PENDING: "bg-gray-100 text-gray-700",
  BASIC: "bg-blue-100 text-blue-700",
  VERIFIED: "bg-green-100 text-green-700",
  PREFERRED: "bg-purple-100 text-purple-700",
  PREMIUM: "bg-amber-100 text-amber-700",
};

const docStatusColors: Record<KycDocumentStatus, string> = {
  PENDING: "bg-gray-100 text-gray-700",
  VERIFIED: "bg-green-100 text-green-700",
  REJECTED: "bg-red-100 text-red-700",
  EXPIRED: "bg-amber-100 text-amber-700",
};

export default function SupplierProfilePage() {
  const supplierId = PLACEHOLDER_SUPPLIER_ID;

  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ["supplier-profile", supplierId],
    queryFn: () => getMyProfile(supplierId),
    enabled: !!supplierId,
  });

  const { data: documents, isLoading: docsLoading } = useQuery({
    queryKey: ["supplier-documents", supplierId],
    queryFn: () => getMyDocuments(supplierId),
    enabled: !!supplierId,
  });

  const { data: capabilities } = useQuery({
    queryKey: ["supplier-capabilities", supplierId],
    queryFn: () => getMyTierCapabilities(supplierId),
    enabled: !!supplierId,
  });

  if (!supplierId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Supplier Profile
          </h1>
          <p className="text-muted-foreground">
            View and manage your company information
          </p>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center py-12 text-center">
            <Building2 className="mb-3 h-10 w-10 text-muted-foreground" />
            <p className="font-medium">No supplier profile linked</p>
            <p className="text-sm text-muted-foreground mt-1">
              Please contact your administrator to link your account to a supplier profile.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          Supplier Profile
        </h1>
        <p className="text-muted-foreground">
          View and manage your company information
        </p>
      </div>

      {/* Company Information */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Building2 className="h-4 w-4" />
              Company Information
            </CardTitle>
            {profile && (
              <div className="flex items-center gap-2">
                <Badge
                  variant="outline"
                  className={tierColors[profile.tier]}
                >
                  <Award className="mr-1 h-3 w-3" />
                  {profile.tier}
                </Badge>
                <Badge variant="outline">
                  <Shield className="mr-1 h-3 w-3" />
                  {profile.onboarding_status.replace(/_/g, " ")}
                </Badge>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {profileLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-6 w-full" />
              ))}
            </div>
          ) : profile ? (
            <div className="grid gap-6 md:grid-cols-2">
              <div className="space-y-4">
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Company Name
                  </p>
                  <p className="text-sm font-medium mt-1">
                    {profile.company_name}
                  </p>
                </div>
                <div className="flex items-start gap-2">
                  <Mail className="h-4 w-4 text-muted-foreground mt-0.5" />
                  <div>
                    <p className="text-xs text-muted-foreground">
                      Contact Email
                    </p>
                    <p className="text-sm">{profile.contact_email}</p>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <Phone className="h-4 w-4 text-muted-foreground mt-0.5" />
                  <div>
                    <p className="text-xs text-muted-foreground">
                      Contact Phone
                    </p>
                    <p className="text-sm">
                      {profile.contact_phone || "Not provided"}
                    </p>
                  </div>
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Contact Person
                  </p>
                  <p className="text-sm mt-1">{profile.contact_name}</p>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-start gap-2">
                  <MapPin className="h-4 w-4 text-muted-foreground mt-0.5" />
                  <div>
                    <p className="text-xs text-muted-foreground">Address</p>
                    <p className="text-sm">
                      {[
                        profile.address_line1,
                        profile.address_line2,
                        profile.city,
                        profile.state,
                        profile.pincode,
                        profile.country,
                      ]
                        .filter(Boolean)
                        .join(", ") || "Not provided"}
                    </p>
                  </div>
                </div>
                {profile.gst_number && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      GST Number
                    </p>
                    <p className="text-sm font-mono mt-1">
                      {profile.gst_number}
                    </p>
                  </div>
                )}
                {profile.pan_number && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      PAN Number
                    </p>
                    <p className="text-sm font-mono mt-1">
                      {profile.pan_number}
                    </p>
                  </div>
                )}
                {profile.categories.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Categories
                    </p>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {profile.categories.map((cat) => (
                        <Badge key={cat} variant="secondary" className="text-xs">
                          {cat}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                {profile.port_coverage.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Port Coverage
                    </p>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {profile.port_coverage.map((port) => (
                        <Badge key={port} variant="outline" className="text-xs">
                          {port}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* Tier Capabilities */}
      {capabilities && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Award className="h-4 w-4" />
              Tier Capabilities
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <p className="text-xs text-muted-foreground">Quote Limit</p>
                <p className="text-sm font-medium">
                  {capabilities.max_quotes ?? "Unlimited"}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Can Bid RFQ</p>
                <p className="text-sm font-medium">
                  {capabilities.can_bid_rfq ? "Yes" : "No"}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Commission</p>
                <p className="text-sm font-medium">
                  {capabilities.commission_percent}%
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Visibility</p>
                <p className="text-sm font-medium capitalize">
                  {capabilities.visibility}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* KYC Documents */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <FileCheck className="h-4 w-4" />
            KYC Documents
          </CardTitle>
        </CardHeader>
        <CardContent>
          {docsLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : documents && documents.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Document Type</TableHead>
                  <TableHead>File Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Expiry</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell className="font-medium">
                      {doc.document_type.replace(/_/g, " ")}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {doc.file_name}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={docStatusColors[doc.status]}
                      >
                        {doc.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {doc.expiry_date
                        ? new Date(doc.expiry_date).toLocaleDateString()
                        : "--"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="flex flex-col items-center py-8 text-center">
              <FileCheck className="mb-3 h-10 w-10 text-muted-foreground" />
              <p className="text-sm font-medium">No documents uploaded</p>
              <p className="text-xs text-muted-foreground">
                KYC documents will appear here once uploaded.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
