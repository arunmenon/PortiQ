import { apiClient } from "./client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type InvoiceStatus =
  | "DRAFT"
  | "READY"
  | "SENT"
  | "ACKNOWLEDGED"
  | "DISPUTED"
  | "PAID"
  | "CANCELLED";

export type SettlementStatus =
  | "OPEN"
  | "PENDING_REVIEW"
  | "APPROVED"
  | "SETTLED"
  | "CLOSED";

export interface InvoiceLineItem {
  id: string;
  invoice_id: string;
  product_id: string | null;
  impa_code: string | null;
  description: string;
  quantity_ordered: string;
  quantity_delivered: string;
  quantity_accepted: string;
  unit_price: string;
  total_price: string;
  notes: string | null;
}

export interface InvoiceResponse {
  id: string;
  invoice_number: string;
  order_id: string;
  vendor_order_id: string | null;
  supplier_name: string | null;
  buyer_organization_id: string;
  status: InvoiceStatus;
  subtotal: string;
  tax_amount: string;
  credit_adjustment: string;
  total_amount: string;
  currency: string;
  due_date: string | null;
  paid_at: string | null;
  line_items: InvoiceLineItem[];
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface InvoiceListResponse {
  items: InvoiceResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface InvoiceListParams {
  search?: string;
  status?: InvoiceStatus;
  limit?: number;
  offset?: number;
}

export interface ReconciliationRow {
  impa_code: string | null;
  description: string;
  quantity_ordered: string;
  quantity_delivered: string;
  quantity_accepted: string;
  unit_price: string;
  line_total: string;
  adjustment: string | null;
}

export interface ReconciliationResponse {
  invoice_id: string;
  rows: ReconciliationRow[];
  subtotal: string;
  tax_amount: string;
  credit_adjustment: string;
  total: string;
}

export interface SettlementResponse {
  id: string;
  period_start: string;
  period_end: string;
  status: SettlementStatus;
  total_invoiced: string;
  total_paid: string;
  total_outstanding: string;
  total_credit: string;
  invoice_count: number;
  currency: string;
  created_at: string;
  updated_at: string;
}

export interface SettlementListResponse {
  items: SettlementResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface SettlementListParams {
  status?: SettlementStatus;
  limit?: number;
  offset?: number;
}

// ---------------------------------------------------------------------------
// API Functions
// ---------------------------------------------------------------------------

const INVOICES_BASE = "/api/v1/invoices";
const SETTLEMENTS_BASE = "/api/v1/settlements";

export async function listInvoices(
  params?: InvoiceListParams,
): Promise<InvoiceListResponse> {
  return apiClient.get<InvoiceListResponse>(
    INVOICES_BASE,
    params as unknown as Record<string, string | number | boolean | undefined>,
  );
}

export async function getInvoice(
  invoiceId: string,
): Promise<InvoiceResponse> {
  return apiClient.get<InvoiceResponse>(`${INVOICES_BASE}/${invoiceId}`);
}

export async function generateInvoice(
  orderId: string,
  vendorOrderId?: string,
): Promise<InvoiceResponse> {
  return apiClient.post<InvoiceResponse>(INVOICES_BASE, {
    order_id: orderId,
    vendor_order_id: vendorOrderId,
  });
}

export async function markInvoiceReady(
  invoiceId: string,
): Promise<InvoiceResponse> {
  return apiClient.post<InvoiceResponse>(
    `${INVOICES_BASE}/${invoiceId}/ready`,
  );
}

export async function acknowledgeInvoice(
  invoiceId: string,
): Promise<InvoiceResponse> {
  return apiClient.post<InvoiceResponse>(
    `${INVOICES_BASE}/${invoiceId}/acknowledge`,
  );
}

export async function markInvoicePaid(
  invoiceId: string,
): Promise<InvoiceResponse> {
  return apiClient.post<InvoiceResponse>(
    `${INVOICES_BASE}/${invoiceId}/paid`,
  );
}

export async function getReconciliation(
  invoiceId: string,
): Promise<ReconciliationResponse> {
  return apiClient.get<ReconciliationResponse>(
    `${INVOICES_BASE}/${invoiceId}/reconciliation`,
  );
}

export async function listSettlements(
  params?: SettlementListParams,
): Promise<SettlementListResponse> {
  return apiClient.get<SettlementListResponse>(
    SETTLEMENTS_BASE,
    params as unknown as Record<string, string | number | boolean | undefined>,
  );
}
