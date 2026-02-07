"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getSupplier, listSupplierDocuments, getReviewLog } from "@/lib/api/suppliers";
import { SupplierDetail } from "@/components/suppliers/supplier-detail";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, Users } from "lucide-react";

export default function SupplierDetailPage() {
  const params = useParams();
  const router = useRouter();
  const supplierId = params.id as string;

  const { data: supplier, isLoading: supplierLoading, error: supplierError } = useQuery({
    queryKey: ["supplier", supplierId],
    queryFn: () => getSupplier(supplierId),
    enabled: !!supplierId,
  });

  const { data: documents, isLoading: documentsLoading } = useQuery({
    queryKey: ["supplier-documents", supplierId],
    queryFn: () => listSupplierDocuments(supplierId),
    enabled: !!supplierId,
  });

  const { data: reviewLog, isLoading: reviewLoading } = useQuery({
    queryKey: ["supplier-review-log", supplierId],
    queryFn: () => getReviewLog(supplierId),
    enabled: !!supplierId,
  });

  const isLoading = supplierLoading || documentsLoading || reviewLoading;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => router.push("/suppliers")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Suppliers
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      ) : supplierError || !supplier ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Users className="mb-4 h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium">Supplier not found</p>
          <p className="text-sm text-muted-foreground">
            The supplier you are looking for does not exist or has been removed.
          </p>
        </div>
      ) : (
        <>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              {supplier.company_name}
            </h1>
            <p className="text-muted-foreground">
              Supplier profile and verification details
            </p>
          </div>
          <SupplierDetail
            supplier={supplier}
            documents={documents || []}
            reviewLog={reviewLog || []}
          />
        </>
      )}
    </div>
  );
}
