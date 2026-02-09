import { apiClient } from "./client";
import type {
  RfqResponse,
  RfqListResponse,
  RfqListParams,
  InvitationResponse,
  InvitationRespondRequest,
  QuoteCreate,
  QuoteResponse,
  QuoteListResponse,
  SupplierProfileResponse,
  SupplierKycDocumentResponse,
  TierCapabilities,
} from "./types";

const RFQS_BASE = "/api/v1/rfqs";
const SUPPLIERS_BASE = "/api/v1/suppliers";

// ---------------------------------------------------------------------------
// Supplier Portal: RFQ Opportunities (supplier sees published/bidding RFQs)
// ---------------------------------------------------------------------------

export async function listSupplierOpportunities(
  params?: RfqListParams,
): Promise<RfqListResponse> {
  return apiClient.get<RfqListResponse>(
    RFQS_BASE,
    params as unknown as Record<string, string | number | boolean | undefined>,
  );
}

export async function getSupplierRfqDetail(
  rfqId: string,
): Promise<RfqResponse> {
  return apiClient.get<RfqResponse>(`${RFQS_BASE}/${rfqId}`);
}

// ---------------------------------------------------------------------------
// Invitations (supplier-side)
// ---------------------------------------------------------------------------

export async function listMyInvitations(
  rfqId: string,
): Promise<InvitationResponse[]> {
  return apiClient.get<InvitationResponse[]>(
    `${RFQS_BASE}/${rfqId}/invitations`,
  );
}

export async function respondToInvitation(
  rfqId: string,
  data: InvitationRespondRequest,
): Promise<InvitationResponse> {
  return apiClient.post<InvitationResponse>(
    `${RFQS_BASE}/${rfqId}/invitations/respond`,
    data,
  );
}

// ---------------------------------------------------------------------------
// Quotes (supplier submits and manages)
// ---------------------------------------------------------------------------

export async function submitQuote(
  rfqId: string,
  data: QuoteCreate,
): Promise<QuoteResponse> {
  return apiClient.post<QuoteResponse>(`${RFQS_BASE}/${rfqId}/quotes`, data);
}

export async function listMyQuotes(
  rfqId: string,
): Promise<QuoteListResponse> {
  return apiClient.get<QuoteListResponse>(`${RFQS_BASE}/${rfqId}/quotes`);
}

export async function getMyQuote(
  rfqId: string,
  quoteId: string,
): Promise<QuoteResponse> {
  return apiClient.get<QuoteResponse>(
    `${RFQS_BASE}/${rfqId}/quotes/${quoteId}`,
  );
}

export async function withdrawQuote(
  rfqId: string,
  quoteId: string,
  reason?: string,
): Promise<QuoteResponse> {
  return apiClient.post<QuoteResponse>(
    `${RFQS_BASE}/${rfqId}/quotes/${quoteId}/withdraw`,
    reason ? { reason } : undefined,
  );
}

// ---------------------------------------------------------------------------
// Supplier Profile (own profile)
// ---------------------------------------------------------------------------

export async function getMyProfile(
  supplierId: string,
): Promise<SupplierProfileResponse> {
  return apiClient.get<SupplierProfileResponse>(
    `${SUPPLIERS_BASE}/${supplierId}`,
  );
}

export async function getMyDocuments(
  supplierId: string,
): Promise<SupplierKycDocumentResponse[]> {
  return apiClient.get<SupplierKycDocumentResponse[]>(
    `${SUPPLIERS_BASE}/${supplierId}/documents`,
  );
}

export async function getMyTierCapabilities(
  supplierId: string,
): Promise<TierCapabilities> {
  return apiClient.get<TierCapabilities>(
    `${SUPPLIERS_BASE}/${supplierId}/tier-capabilities`,
  );
}
