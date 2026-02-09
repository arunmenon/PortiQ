import { apiClient } from "./client";
import type {
  RfqResponse,
  RfqCreate,
  RfqUpdate,
  RfqListParams,
  RfqListResponse,
  RfqLineItemCreate,
  RfqLineItemUpdate,
  RfqLineItemResponse,
  InvitationCreate,
  InvitationResponse,
  InvitationRespondRequest,
  QuoteCreate,
  QuoteResponse,
  QuoteListResponse,
  AwardRequest,
  CancelRequest,
  TransitionResponse,
} from "./types";

const RFQS_BASE = "/api/v1/rfqs";

// ---------------------------------------------------------------------------
// RFQ CRUD
// ---------------------------------------------------------------------------

export async function listRfqs(
  params?: RfqListParams,
): Promise<RfqListResponse> {
  return apiClient.get<RfqListResponse>(
    RFQS_BASE,
    params as unknown as Record<string, string | number | boolean | undefined>,
  );
}

export async function getRfq(rfqId: string): Promise<RfqResponse> {
  return apiClient.get<RfqResponse>(`${RFQS_BASE}/${rfqId}`);
}

export async function createRfq(data: RfqCreate): Promise<RfqResponse> {
  return apiClient.post<RfqResponse>(RFQS_BASE, data);
}

export async function updateRfq(
  rfqId: string,
  data: RfqUpdate,
): Promise<RfqResponse> {
  return apiClient.patch<RfqResponse>(`${RFQS_BASE}/${rfqId}`, data);
}

export async function deleteRfq(rfqId: string): Promise<void> {
  return apiClient.delete<void>(`${RFQS_BASE}/${rfqId}`);
}

// ---------------------------------------------------------------------------
// Line Items
// ---------------------------------------------------------------------------

export async function addLineItem(
  rfqId: string,
  data: RfqLineItemCreate,
): Promise<RfqLineItemResponse> {
  return apiClient.post<RfqLineItemResponse>(
    `${RFQS_BASE}/${rfqId}/line-items`,
    data,
  );
}

export async function updateLineItem(
  rfqId: string,
  itemId: string,
  data: RfqLineItemUpdate,
): Promise<RfqLineItemResponse> {
  return apiClient.patch<RfqLineItemResponse>(
    `${RFQS_BASE}/${rfqId}/line-items/${itemId}`,
    data,
  );
}

export async function deleteLineItem(
  rfqId: string,
  itemId: string,
): Promise<void> {
  return apiClient.delete<void>(
    `${RFQS_BASE}/${rfqId}/line-items/${itemId}`,
  );
}

// ---------------------------------------------------------------------------
// Invitations
// ---------------------------------------------------------------------------

export async function inviteSuppliers(
  rfqId: string,
  data: InvitationCreate,
): Promise<InvitationResponse[]> {
  return apiClient.post<InvitationResponse[]>(
    `${RFQS_BASE}/${rfqId}/invitations`,
    data,
  );
}

export async function listInvitations(
  rfqId: string,
): Promise<InvitationResponse[]> {
  return apiClient.get<InvitationResponse[]>(
    `${RFQS_BASE}/${rfqId}/invitations`,
  );
}

export async function removeInvitation(
  rfqId: string,
  invitationId: string,
): Promise<void> {
  return apiClient.delete<void>(
    `${RFQS_BASE}/${rfqId}/invitations/${invitationId}`,
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
// State Transitions
// ---------------------------------------------------------------------------

export async function publishRfq(rfqId: string): Promise<RfqResponse> {
  return apiClient.post<RfqResponse>(`${RFQS_BASE}/${rfqId}/publish`);
}

export async function openBidding(rfqId: string): Promise<RfqResponse> {
  return apiClient.post<RfqResponse>(`${RFQS_BASE}/${rfqId}/open-bidding`);
}

export async function closeBidding(rfqId: string): Promise<RfqResponse> {
  return apiClient.post<RfqResponse>(`${RFQS_BASE}/${rfqId}/close-bidding`);
}

export async function startEvaluation(rfqId: string): Promise<RfqResponse> {
  return apiClient.post<RfqResponse>(`${RFQS_BASE}/${rfqId}/start-evaluation`);
}

export async function awardRfq(
  rfqId: string,
  data: AwardRequest,
): Promise<RfqResponse> {
  return apiClient.post<RfqResponse>(`${RFQS_BASE}/${rfqId}/award`, data);
}

export async function completeRfq(rfqId: string): Promise<RfqResponse> {
  return apiClient.post<RfqResponse>(`${RFQS_BASE}/${rfqId}/complete`);
}

export async function cancelRfq(
  rfqId: string,
  data: CancelRequest,
): Promise<RfqResponse> {
  return apiClient.post<RfqResponse>(`${RFQS_BASE}/${rfqId}/cancel`, data);
}

export async function getTransitions(
  rfqId: string,
): Promise<TransitionResponse[]> {
  return apiClient.get<TransitionResponse[]>(
    `${RFQS_BASE}/${rfqId}/transitions`,
  );
}

// ---------------------------------------------------------------------------
// Quotes
// ---------------------------------------------------------------------------

export async function submitQuote(
  rfqId: string,
  data: QuoteCreate,
): Promise<QuoteResponse> {
  return apiClient.post<QuoteResponse>(`${RFQS_BASE}/${rfqId}/quotes`, data);
}

export async function listQuotes(
  rfqId: string,
): Promise<QuoteListResponse> {
  return apiClient.get<QuoteListResponse>(`${RFQS_BASE}/${rfqId}/quotes`);
}

export async function getQuote(
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
