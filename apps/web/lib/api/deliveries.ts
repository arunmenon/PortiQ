import { apiClient } from "./client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type DeliveryStatus =
  | "PENDING"
  | "DISPATCHED"
  | "IN_TRANSIT"
  | "DELIVERED"
  | "ACCEPTED"
  | "DISPUTED"
  | "REJECTED";

export interface DeliveryItem {
  id: string;
  delivery_id: string;
  product_id: string | null;
  impa_code: string | null;
  description: string;
  quantity_ordered: string;
  quantity_delivered: string;
  quantity_accepted: string | null;
  unit_of_measure: string;
  notes: string | null;
}

export interface DeliveryPhoto {
  id: string;
  delivery_id: string;
  file_key: string;
  file_name: string;
  caption: string | null;
  uploaded_at: string;
}

export interface ProofOfDelivery {
  gps_latitude: string | null;
  gps_longitude: string | null;
  gps_accuracy: string | null;
  receiver_name: string | null;
  receiver_designation: string | null;
  signature_file_key: string | null;
  delivered_at: string | null;
  photos: DeliveryPhoto[];
}

export interface DeliveryResponse {
  id: string;
  delivery_number: string;
  order_id: string;
  vendor_order_id: string;
  supplier_name: string | null;
  vessel_name: string | null;
  delivery_port: string | null;
  status: DeliveryStatus;
  estimated_delivery_date: string | null;
  actual_delivery_date: string | null;
  items: DeliveryItem[];
  proof_of_delivery: ProofOfDelivery | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface DeliveryListResponse {
  items: DeliveryResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface DeliveryListParams {
  search?: string;
  status?: DeliveryStatus;
  limit?: number;
  offset?: number;
}

export interface CreateDeliveryRequest {
  order_id: string;
  vendor_order_id: string;
  estimated_delivery_date?: string | null;
  notes?: string | null;
}

export interface RecordDeliveryRequest {
  gps_latitude?: string | null;
  gps_longitude?: string | null;
  gps_accuracy?: string | null;
  receiver_name?: string | null;
  receiver_designation?: string | null;
  items: {
    delivery_item_id: string;
    quantity_delivered: number;
  }[];
}

// ---------------------------------------------------------------------------
// API Functions
// ---------------------------------------------------------------------------

const DELIVERIES_BASE = "/api/v1/deliveries";

export async function listDeliveries(
  params?: DeliveryListParams,
): Promise<DeliveryListResponse> {
  return apiClient.get<DeliveryListResponse>(
    DELIVERIES_BASE,
    params as unknown as Record<string, string | number | boolean | undefined>,
  );
}

export async function getDelivery(
  deliveryId: string,
): Promise<DeliveryResponse> {
  return apiClient.get<DeliveryResponse>(`${DELIVERIES_BASE}/${deliveryId}`);
}

export async function createDelivery(
  data: CreateDeliveryRequest,
): Promise<DeliveryResponse> {
  return apiClient.post<DeliveryResponse>(DELIVERIES_BASE, data);
}

export async function dispatchDelivery(
  deliveryId: string,
): Promise<DeliveryResponse> {
  return apiClient.post<DeliveryResponse>(
    `${DELIVERIES_BASE}/${deliveryId}/dispatch`,
  );
}

export async function recordDelivery(
  deliveryId: string,
  data: RecordDeliveryRequest,
): Promise<DeliveryResponse> {
  return apiClient.post<DeliveryResponse>(
    `${DELIVERIES_BASE}/${deliveryId}/record`,
    data,
  );
}

export async function acceptDelivery(
  deliveryId: string,
  items: { delivery_item_id: string; quantity_accepted: number }[],
): Promise<DeliveryResponse> {
  return apiClient.post<DeliveryResponse>(
    `${DELIVERIES_BASE}/${deliveryId}/accept`,
    { items },
  );
}

export async function disputeDelivery(
  deliveryId: string,
  reason: string,
): Promise<DeliveryResponse> {
  return apiClient.post<DeliveryResponse>(
    `${DELIVERIES_BASE}/${deliveryId}/dispute`,
    { reason },
  );
}
