import { apiClient } from "./client";
import type {
  SupplierProfileResponse,
  SupplierProfileCreateRequest,
  SupplierProfileUpdateRequest,
  SupplierListParams,
  SupplierListResponse,
  SupplierKycDocumentResponse,
  SupplierKycDocumentCreateRequest,
  SupplierKycDocumentUpdateRequest,
  SupplierReviewLogResponse,
  SupplierReviewRequest,
  TierCapabilities,
} from "./types";

const SUPPLIERS_BASE = "/api/v1/suppliers";

// ---------------------------------------------------------------------------
// Supplier Profiles
// ---------------------------------------------------------------------------

export async function listSuppliers(
  params?: SupplierListParams,
): Promise<SupplierListResponse> {
  return apiClient.get<SupplierListResponse>(
    SUPPLIERS_BASE,
    params as unknown as Record<string, string | number | boolean | undefined>,
  );
}

export async function getSupplier(id: string): Promise<SupplierProfileResponse> {
  return apiClient.get<SupplierProfileResponse>(`${SUPPLIERS_BASE}/${id}`);
}

export async function createSupplier(
  data: SupplierProfileCreateRequest,
): Promise<SupplierProfileResponse> {
  return apiClient.post<SupplierProfileResponse>(SUPPLIERS_BASE, data);
}

export async function updateSupplier(
  id: string,
  data: SupplierProfileUpdateRequest,
): Promise<SupplierProfileResponse> {
  return apiClient.patch<SupplierProfileResponse>(`${SUPPLIERS_BASE}/${id}`, data);
}

// ---------------------------------------------------------------------------
// KYC Documents
// ---------------------------------------------------------------------------

export async function listSupplierDocuments(
  supplierId: string,
): Promise<SupplierKycDocumentResponse[]> {
  return apiClient.get<SupplierKycDocumentResponse[]>(
    `${SUPPLIERS_BASE}/${supplierId}/documents`,
  );
}

export async function addSupplierDocument(
  supplierId: string,
  data: SupplierKycDocumentCreateRequest,
): Promise<SupplierKycDocumentResponse> {
  return apiClient.post<SupplierKycDocumentResponse>(
    `${SUPPLIERS_BASE}/${supplierId}/documents`,
    data,
  );
}

export async function updateDocumentStatus(
  supplierId: string,
  documentId: string,
  data: SupplierKycDocumentUpdateRequest,
): Promise<SupplierKycDocumentResponse> {
  return apiClient.patch<SupplierKycDocumentResponse>(
    `${SUPPLIERS_BASE}/${supplierId}/documents/${documentId}`,
    data,
  );
}

// ---------------------------------------------------------------------------
// Verification & Review
// ---------------------------------------------------------------------------

export async function submitForVerification(
  supplierId: string,
): Promise<SupplierProfileResponse> {
  return apiClient.post<SupplierProfileResponse>(
    `${SUPPLIERS_BASE}/${supplierId}/submit-for-verification`,
  );
}

export async function submitReview(
  supplierId: string,
  data: SupplierReviewRequest,
): Promise<SupplierProfileResponse> {
  return apiClient.post<SupplierProfileResponse>(
    `${SUPPLIERS_BASE}/${supplierId}/review`,
    data,
  );
}

export async function getReviewLog(
  supplierId: string,
): Promise<SupplierReviewLogResponse[]> {
  return apiClient.get<SupplierReviewLogResponse[]>(
    `${SUPPLIERS_BASE}/${supplierId}/review-log`,
  );
}

export async function getPendingReviews(): Promise<SupplierListResponse> {
  return apiClient.get<SupplierListResponse>(`${SUPPLIERS_BASE}/pending-reviews`);
}

// ---------------------------------------------------------------------------
// Tier Management
// ---------------------------------------------------------------------------

export async function requestTierUpgrade(
  supplierId: string,
): Promise<SupplierProfileResponse> {
  return apiClient.post<SupplierProfileResponse>(
    `${SUPPLIERS_BASE}/${supplierId}/request-tier-upgrade`,
  );
}

export async function getTierCapabilities(
  supplierId: string,
): Promise<TierCapabilities> {
  return apiClient.get<TierCapabilities>(
    `${SUPPLIERS_BASE}/${supplierId}/tier-capabilities`,
  );
}

// ---------------------------------------------------------------------------
// Admin Actions
// ---------------------------------------------------------------------------

export async function updateSupplierStatus(
  supplierId: string,
  status: "SUSPENDED" | "STARTED",
  notes?: string,
): Promise<SupplierProfileResponse> {
  return apiClient.put<SupplierProfileResponse>(
    `${SUPPLIERS_BASE}/${supplierId}/status`,
    { status, notes },
  );
}
