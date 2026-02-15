"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ArrowLeft,
  MapPin,
  Calendar,
  Building2,
  Ship,
  Truck,
  ShoppingCart,
} from "lucide-react";
import Link from "next/link";

interface OrderItem {
  id: string;
  product_name: string;
  impa_code: string | null;
  quantity: number;
  unit_of_measure: string;
  unit_price: string;
  total_price: string;
}

type OrderStatus =
  | "CONFIRMED"
  | "IN_PROGRESS"
  | "PARTIALLY_FULFILLED"
  | "FULFILLED"
  | "COMPLETED"
  | "CANCELLED";

interface OrderDetail {
  id: string;
  order_number: string;
  rfq_id: string | null;
  rfq_reference: string | null;
  buyer_organization_id: string;
  buyer_organization_name: string;
  status: OrderStatus;
  vessel_name: string | null;
  delivery_port: string | null;
  delivery_date: string | null;
  total_amount: string;
  currency: string;
  payment_terms: string | null;
  shipping_terms: string | null;
  notes: string | null;
  items: OrderItem[];
  created_at: string;
  updated_at: string;
}

const STATUS_COLORS: Record<OrderStatus, string> = {
  CONFIRMED: "bg-blue-100 text-blue-800",
  IN_PROGRESS: "bg-yellow-100 text-yellow-800",
  PARTIALLY_FULFILLED: "bg-orange-100 text-orange-800",
  FULFILLED: "bg-green-100 text-green-800",
  COMPLETED: "bg-gray-100 text-gray-800",
  CANCELLED: "bg-red-100 text-red-800",
};

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function formatCurrency(amount: string, currency: string): string {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
  }).format(parseFloat(amount));
}

async function getSupplierOrder(orderId: string): Promise<OrderDetail> {
  return apiClient.get<OrderDetail>(`/api/v1/supplier/orders/${orderId}`);
}

export default function SupplierOrderDetailPage() {
  const params = useParams();
  const router = useRouter();
  const orderId = params.id as string;

  const { data: order, isLoading, error } = useQuery({
    queryKey: ["supplier-order", orderId],
    queryFn: () => getSupplierOrder(orderId),
    enabled: !!orderId,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <ShoppingCart className="mb-4 h-12 w-12 text-muted-foreground" />
        <p className="text-lg font-medium">Order not found</p>
        <p className="text-sm text-muted-foreground">
          The order you are looking for does not exist or you do not have access.
        </p>
        <Button variant="outline" className="mt-4" onClick={() => router.back()}>
          Go Back
        </Button>
      </div>
    );
  }

  const canCreateDelivery =
    order.status === "CONFIRMED" ||
    order.status === "IN_PROGRESS" ||
    order.status === "PARTIALLY_FULFILLED";

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">
              {order.order_number}
            </h1>
            <Badge
              className={STATUS_COLORS[order.status]}
              variant="secondary"
            >
              {order.status.replace(/_/g, " ")}
            </Badge>
          </div>
          <p className="text-muted-foreground">
            Order from {order.buyer_organization_name}
          </p>
        </div>
        {canCreateDelivery && (
          <Button asChild>
            <Link href={`/supplier/deliveries/${order.id}/submit`}>
              <Truck className="mr-2 h-4 w-4" />
              Prepare Delivery
            </Link>
          </Button>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Building2 className="h-4 w-4" />
              <span>Buyer</span>
            </div>
            <p className="mt-1 font-medium">{order.buyer_organization_name}</p>
          </CardContent>
        </Card>

        {order.vessel_name && (
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Ship className="h-4 w-4" />
                <span>Vessel</span>
              </div>
              <p className="mt-1 font-medium">{order.vessel_name}</p>
            </CardContent>
          </Card>
        )}

        {order.delivery_port && (
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <MapPin className="h-4 w-4" />
                <span>Delivery Port</span>
              </div>
              <p className="mt-1 font-medium">{order.delivery_port}</p>
            </CardContent>
          </Card>
        )}

        {order.delivery_date && (
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Calendar className="h-4 w-4" />
                <span>Delivery Date</span>
              </div>
              <p className="mt-1 font-medium">{formatDate(order.delivery_date)}</p>
            </CardContent>
          </Card>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Order Items</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Product</TableHead>
                <TableHead>IMPA Code</TableHead>
                <TableHead className="text-right">Qty</TableHead>
                <TableHead>Unit</TableHead>
                <TableHead className="text-right">Unit Price</TableHead>
                <TableHead className="text-right">Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {order.items.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-medium">{item.product_name}</TableCell>
                  <TableCell>
                    {item.impa_code ? (
                      <Badge variant="secondary" className="font-mono text-xs">
                        {item.impa_code}
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">{item.quantity}</TableCell>
                  <TableCell>{item.unit_of_measure}</TableCell>
                  <TableCell className="text-right">
                    {formatCurrency(item.unit_price, order.currency)}
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {formatCurrency(item.total_price, order.currency)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="mt-4 flex justify-end border-t pt-4">
            <div className="text-right">
              <span className="text-sm text-muted-foreground">Total Amount</span>
              <p className="text-xl font-bold">
                {formatCurrency(order.total_amount, order.currency)}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {(order.payment_terms || order.shipping_terms || order.notes) && (
        <Card>
          <CardHeader>
            <CardTitle>Terms & Notes</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {order.payment_terms && (
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Payment Terms
                </p>
                <p className="mt-1">{order.payment_terms}</p>
              </div>
            )}
            {order.shipping_terms && (
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Shipping Terms
                </p>
                <p className="mt-1">{order.shipping_terms}</p>
              </div>
            )}
            {order.notes && (
              <div>
                <p className="text-sm font-medium text-muted-foreground">Notes</p>
                <p className="mt-1">{order.notes}</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
