import { apiClient } from "./client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type OrderStatus =
  | "DRAFT"
  | "CONFIRMED"
  | "PARTIALLY_FULFILLED"
  | "FULFILLED"
  | "COMPLETED"
  | "CANCELLED";

export type VendorOrderStatus =
  | "PENDING"
  | "CONFIRMED"
  | "PROCESSING"
  | "SHIPPED"
  | "DELIVERED"
  | "COMPLETED"
  | "CANCELLED";

export type FulfillmentStatus =
  | "PENDING"
  | "SHIPPED"
  | "DELIVERED"
  | "ACCEPTED"
  | "DISPUTED";

export interface OrderLineItem {
  id: string;
  order_id: string;
  product_id: string | null;
  impa_code: string | null;
  description: string;
  quantity: string;
  unit_of_measure: string;
  unit_price: string;
  total_price: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface FulfillmentResponse {
  id: string;
  vendor_order_id: string;
  fulfillment_number: string;
  status: FulfillmentStatus;
  shipped_at: string | null;
  delivered_at: string | null;
  tracking_number: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface VendorOrderResponse {
  id: string;
  order_id: string;
  supplier_organization_id: string;
  supplier_name: string | null;
  status: VendorOrderStatus;
  total_amount: string | null;
  currency: string;
  notes: string | null;
  line_items: OrderLineItem[];
  fulfillments: FulfillmentResponse[];
  created_at: string;
  updated_at: string;
}

export interface OrderResponse {
  id: string;
  reference_number: string;
  rfq_id: string | null;
  buyer_organization_id: string;
  status: OrderStatus;
  total_amount: string | null;
  currency: string;
  vessel_id: string | null;
  vessel_name: string | null;
  delivery_port: string | null;
  delivery_date: string | null;
  notes: string | null;
  vendor_orders: VendorOrderResponse[];
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface OrderListResponse {
  items: OrderResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface OrderListParams {
  search?: string;
  status?: OrderStatus;
  limit?: number;
  offset?: number;
}

export interface CreateOrderFromAwardRequest {
  rfq_id: string;
  quote_id: string;
  notes?: string | null;
}

export interface CreateFulfillmentRequest {
  tracking_number?: string | null;
  notes?: string | null;
}

// ---------------------------------------------------------------------------
// API Functions
// ---------------------------------------------------------------------------

const ORDERS_BASE = "/api/v1/orders";

export async function listOrders(
  params?: OrderListParams,
): Promise<OrderListResponse> {
  return apiClient.get<OrderListResponse>(
    ORDERS_BASE,
    params as unknown as Record<string, string | number | boolean | undefined>,
  );
}

export async function getOrder(orderId: string): Promise<OrderResponse> {
  return apiClient.get<OrderResponse>(`${ORDERS_BASE}/${orderId}`);
}

export async function createOrderFromAward(
  data: CreateOrderFromAwardRequest,
): Promise<OrderResponse> {
  return apiClient.post<OrderResponse>(ORDERS_BASE, data);
}

export async function cancelOrder(
  orderId: string,
  reason: string,
): Promise<OrderResponse> {
  return apiClient.post<OrderResponse>(`${ORDERS_BASE}/${orderId}/cancel`, {
    reason,
  });
}

export async function listVendorOrders(
  orderId: string,
): Promise<VendorOrderResponse[]> {
  return apiClient.get<VendorOrderResponse[]>(
    `${ORDERS_BASE}/${orderId}/vendor-orders`,
  );
}

export async function getVendorOrder(
  orderId: string,
  vendorOrderId: string,
): Promise<VendorOrderResponse> {
  return apiClient.get<VendorOrderResponse>(
    `${ORDERS_BASE}/${orderId}/vendor-orders/${vendorOrderId}`,
  );
}

export async function updateVendorOrderStatus(
  orderId: string,
  vendorOrderId: string,
  status: VendorOrderStatus,
): Promise<VendorOrderResponse> {
  return apiClient.patch<VendorOrderResponse>(
    `${ORDERS_BASE}/${orderId}/vendor-orders/${vendorOrderId}`,
    { status },
  );
}

export async function createFulfillment(
  orderId: string,
  vendorOrderId: string,
  data?: CreateFulfillmentRequest,
): Promise<FulfillmentResponse> {
  return apiClient.post<FulfillmentResponse>(
    `${ORDERS_BASE}/${orderId}/vendor-orders/${vendorOrderId}/fulfillments`,
    data,
  );
}
