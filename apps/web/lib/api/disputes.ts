import { apiClient } from "./client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type DisputeStatus =
  | "OPEN"
  | "UNDER_REVIEW"
  | "AWAITING_RESPONSE"
  | "RESOLVED"
  | "ESCALATED"
  | "CLOSED";

export type DisputeType =
  | "QUANTITY_MISMATCH"
  | "QUALITY_ISSUE"
  | "DAMAGED_GOODS"
  | "WRONG_ITEMS"
  | "PRICING_DISCREPANCY"
  | "LATE_DELIVERY"
  | "OTHER";

export interface DisputeComment {
  id: string;
  dispute_id: string;
  author_id: string;
  author_name: string | null;
  content: string;
  attachment_keys: string[];
  created_at: string;
}

export interface DisputeResponse {
  id: string;
  dispute_number: string;
  order_id: string;
  delivery_id: string | null;
  invoice_id: string | null;
  dispute_type: DisputeType;
  status: DisputeStatus;
  title: string;
  description: string;
  raised_by: string;
  raised_by_name: string | null;
  assigned_to: string | null;
  assigned_to_name: string | null;
  resolution: string | null;
  resolved_at: string | null;
  comments: DisputeComment[];
  created_at: string;
  updated_at: string;
}

export interface DisputeListResponse {
  items: DisputeResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface DisputeListParams {
  search?: string;
  status?: DisputeStatus;
  dispute_type?: DisputeType;
  limit?: number;
  offset?: number;
}

export interface CreateDisputeRequest {
  order_id: string;
  delivery_id?: string | null;
  invoice_id?: string | null;
  dispute_type: DisputeType;
  title: string;
  description: string;
}

export interface AddCommentRequest {
  content: string;
  attachment_keys?: string[];
}

// ---------------------------------------------------------------------------
// API Functions
// ---------------------------------------------------------------------------

const DISPUTES_BASE = "/api/v1/disputes";

export async function listDisputes(
  params?: DisputeListParams,
): Promise<DisputeListResponse> {
  return apiClient.get<DisputeListResponse>(
    DISPUTES_BASE,
    params as unknown as Record<string, string | number | boolean | undefined>,
  );
}

export async function getDispute(
  disputeId: string,
): Promise<DisputeResponse> {
  return apiClient.get<DisputeResponse>(`${DISPUTES_BASE}/${disputeId}`);
}

export async function createDispute(
  data: CreateDisputeRequest,
): Promise<DisputeResponse> {
  return apiClient.post<DisputeResponse>(DISPUTES_BASE, data);
}

export async function addComment(
  disputeId: string,
  data: AddCommentRequest,
): Promise<DisputeComment> {
  return apiClient.post<DisputeComment>(
    `${DISPUTES_BASE}/${disputeId}/comments`,
    data,
  );
}

export async function assignReviewer(
  disputeId: string,
  reviewerId: string,
): Promise<DisputeResponse> {
  return apiClient.post<DisputeResponse>(
    `${DISPUTES_BASE}/${disputeId}/assign`,
    { reviewer_id: reviewerId },
  );
}

export async function resolveDispute(
  disputeId: string,
  resolution: string,
): Promise<DisputeResponse> {
  return apiClient.post<DisputeResponse>(
    `${DISPUTES_BASE}/${disputeId}/resolve`,
    { resolution },
  );
}

export async function escalateDispute(
  disputeId: string,
  reason: string,
): Promise<DisputeResponse> {
  return apiClient.post<DisputeResponse>(
    `${DISPUTES_BASE}/${disputeId}/escalate`,
    { reason },
  );
}
