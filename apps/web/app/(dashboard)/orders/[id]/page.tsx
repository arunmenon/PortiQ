"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { getOrder } from "@/lib/api/orders";
import type { OrderStatus, VendorOrderStatus, FulfillmentStatus } from "@/lib/api/orders";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ArrowLeft, MapPin, Calendar, Ship, Package } from "lucide-react";
import Link from "next/link";

const orderStatusStyles: Record<OrderStatus, string> = {
  DRAFT: "border-gray-300 bg-gray-100 text-gray-700 hover:bg-gray-100",
  CONFIRMED: "border-transparent bg-blue-100 text-blue-700 hover:bg-blue-100",
  PARTIALLY_FULFILLED: "border-transparent bg-amber-100 text-amber-700 hover:bg-amber-100",
  FULFILLED: "border-transparent bg-indigo-100 text-indigo-700 hover:bg-indigo-100",
  COMPLETED: "border-transparent bg-emerald-100 text-emerald-700 hover:bg-emerald-100",
  CANCELLED: "border-transparent bg-red-100 text-red-700 hover:bg-red-100",
};

const orderStatusLabels: Record<OrderStatus, string> = {
  DRAFT: "Draft",
  CONFIRMED: "Confirmed",
  PARTIALLY_FULFILLED: "Partially Fulfilled",
  FULFILLED: "Fulfilled",
  COMPLETED: "Completed",
  CANCELLED: "Cancelled",
};

const vendorStatusStyles: Record<VendorOrderStatus, string> = {
  PENDING: "border-gray-300 bg-gray-100 text-gray-700 hover:bg-gray-100",
  CONFIRMED: "border-transparent bg-blue-100 text-blue-700 hover:bg-blue-100",
  PROCESSING: "border-transparent bg-purple-100 text-purple-700 hover:bg-purple-100",
  SHIPPED: "border-transparent bg-indigo-100 text-indigo-700 hover:bg-indigo-100",
  DELIVERED: "border-transparent bg-teal-100 text-teal-700 hover:bg-teal-100",
  COMPLETED: "border-transparent bg-emerald-100 text-emerald-700 hover:bg-emerald-100",
  CANCELLED: "border-transparent bg-red-100 text-red-700 hover:bg-red-100",
};

const vendorStatusLabels: Record<VendorOrderStatus, string> = {
  PENDING: "Pending",
  CONFIRMED: "Confirmed",
  PROCESSING: "Processing",
  SHIPPED: "Shipped",
  DELIVERED: "Delivered",
  COMPLETED: "Completed",
  CANCELLED: "Cancelled",
};

const fulfillmentStatusStyles: Record<FulfillmentStatus, string> = {
  PENDING: "border-gray-300 bg-gray-100 text-gray-700 hover:bg-gray-100",
  SHIPPED: "border-transparent bg-indigo-100 text-indigo-700 hover:bg-indigo-100",
  DELIVERED: "border-transparent bg-teal-100 text-teal-700 hover:bg-teal-100",
  ACCEPTED: "border-transparent bg-emerald-100 text-emerald-700 hover:bg-emerald-100",
  DISPUTED: "border-transparent bg-red-100 text-red-700 hover:bg-red-100",
};

const fulfillmentStatusLabels: Record<FulfillmentStatus, string> = {
  PENDING: "Pending",
  SHIPPED: "Shipped",
  DELIVERED: "Delivered",
  ACCEPTED: "Accepted",
  DISPUTED: "Disputed",
};

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatCurrency(amount: string | null, currency: string): string {
  if (!amount) return "-";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
  }).format(parseFloat(amount));
}

export default function OrderDetailPage() {
  const params = useParams();
  const { data: order, isLoading } = useQuery({
    queryKey: ["order", params.id],
    queryFn: () => getOrder(params.id as string),
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!order) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Package className="mb-4 h-12 w-12 text-muted-foreground" />
        <p className="text-lg font-medium">Order not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/orders">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Orders
          </Link>
        </Button>
      </div>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {order.reference_number}
          </h1>
          <p className="text-muted-foreground">
            {formatCurrency(order.total_amount, order.currency)}
          </p>
        </div>
        <Badge variant="outline" className={orderStatusStyles[order.status]}>
          {orderStatusLabels[order.status]}
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Order Details</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {order.vessel_name && (
            <div className="flex items-center gap-2 text-sm">
              <Ship className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-muted-foreground">Vessel</p>
                <p className="font-medium">{order.vessel_name}</p>
              </div>
            </div>
          )}
          {order.delivery_port && (
            <div className="flex items-center gap-2 text-sm">
              <MapPin className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-muted-foreground">Delivery Port</p>
                <p className="font-medium">{order.delivery_port}</p>
              </div>
            </div>
          )}
          {order.delivery_date && (
            <div className="flex items-center gap-2 text-sm">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-muted-foreground">Delivery Date</p>
                <p className="font-medium">{formatDate(order.delivery_date)}</p>
              </div>
            </div>
          )}
          <div className="flex items-center gap-2 text-sm">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-muted-foreground">Created</p>
              <p className="font-medium">{formatDate(order.created_at)}</p>
            </div>
          </div>
          {order.notes && (
            <div className="col-span-full text-sm">
              <p className="text-muted-foreground">Notes</p>
              <p>{order.notes}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {order.vendor_orders.map((vo) => (
        <Card key={vo.id}>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="text-lg">
                  {vo.supplier_name || "Supplier"}
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  {formatCurrency(vo.total_amount, vo.currency)}
                </p>
              </div>
              <Badge
                variant="outline"
                className={vendorStatusStyles[vo.status]}
              >
                {vendorStatusLabels[vo.status]}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="mb-2 text-sm font-medium">Line Items</h4>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>IMPA</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="text-right">Qty</TableHead>
                    <TableHead>Unit</TableHead>
                    <TableHead className="text-right">Unit Price</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {vo.line_items.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="font-mono text-xs">
                        {item.impa_code || "-"}
                      </TableCell>
                      <TableCell>{item.description}</TableCell>
                      <TableCell className="text-right">
                        {item.quantity}
                      </TableCell>
                      <TableCell>{item.unit_of_measure}</TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(item.unit_price, vo.currency)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(item.total_price, vo.currency)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {vo.fulfillments.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-medium">Fulfillments</h4>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Fulfillment #</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Tracking</TableHead>
                      <TableHead>Shipped</TableHead>
                      <TableHead>Delivered</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {vo.fulfillments.map((f) => (
                      <TableRow key={f.id}>
                        <TableCell className="font-mono text-xs">
                          {f.fulfillment_number}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className={fulfillmentStatusStyles[f.status]}
                          >
                            {fulfillmentStatusLabels[f.status]}
                          </Badge>
                        </TableCell>
                        <TableCell>{f.tracking_number || "-"}</TableCell>
                        <TableCell>
                          {f.shipped_at ? formatDate(f.shipped_at) : "-"}
                        </TableCell>
                        <TableCell>
                          {f.delivered_at ? formatDate(f.delivered_at) : "-"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
