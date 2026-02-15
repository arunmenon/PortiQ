"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { getDelivery } from "@/lib/api/deliveries";
import type { DeliveryStatus } from "@/lib/api/deliveries";
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
import {
  ArrowLeft,
  MapPin,
  Calendar,
  Ship,
  Truck,
  Camera,
  MapPinned,
  User,
} from "lucide-react";
import Link from "next/link";

const statusStyles: Record<DeliveryStatus, string> = {
  PENDING: "border-gray-300 bg-gray-100 text-gray-700 hover:bg-gray-100",
  DISPATCHED: "border-transparent bg-blue-100 text-blue-700 hover:bg-blue-100",
  IN_TRANSIT: "border-transparent bg-indigo-100 text-indigo-700 hover:bg-indigo-100",
  DELIVERED: "border-transparent bg-teal-100 text-teal-700 hover:bg-teal-100",
  ACCEPTED: "border-transparent bg-emerald-100 text-emerald-700 hover:bg-emerald-100",
  DISPUTED: "border-transparent bg-amber-100 text-amber-700 hover:bg-amber-100",
  REJECTED: "border-transparent bg-red-100 text-red-700 hover:bg-red-100",
};

const statusLabels: Record<DeliveryStatus, string> = {
  PENDING: "Pending",
  DISPATCHED: "Dispatched",
  IN_TRANSIT: "In Transit",
  DELIVERED: "Delivered",
  ACCEPTED: "Accepted",
  DISPUTED: "Disputed",
  REJECTED: "Rejected",
};

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function DeliveryDetailPage() {
  const params = useParams();
  const { data: delivery, isLoading } = useQuery({
    queryKey: ["delivery", params.id],
    queryFn: () => getDelivery(params.id as string),
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

  if (!delivery) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Truck className="mb-4 h-12 w-12 text-muted-foreground" />
        <p className="text-lg font-medium">Delivery not found</p>
      </div>
    );
  }

  const pod = delivery.proof_of_delivery;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/deliveries">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Deliveries
          </Link>
        </Button>
      </div>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {delivery.delivery_number}
          </h1>
          {delivery.supplier_name && (
            <p className="text-muted-foreground">{delivery.supplier_name}</p>
          )}
        </div>
        <Badge variant="outline" className={statusStyles[delivery.status]}>
          {statusLabels[delivery.status]}
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Delivery Details</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {delivery.vessel_name && (
            <div className="flex items-center gap-2 text-sm">
              <Ship className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-muted-foreground">Vessel</p>
                <p className="font-medium">{delivery.vessel_name}</p>
              </div>
            </div>
          )}
          {delivery.delivery_port && (
            <div className="flex items-center gap-2 text-sm">
              <MapPin className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-muted-foreground">Port</p>
                <p className="font-medium">{delivery.delivery_port}</p>
              </div>
            </div>
          )}
          {delivery.estimated_delivery_date && (
            <div className="flex items-center gap-2 text-sm">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-muted-foreground">Estimated Delivery</p>
                <p className="font-medium">
                  {formatDate(delivery.estimated_delivery_date)}
                </p>
              </div>
            </div>
          )}
          {delivery.actual_delivery_date && (
            <div className="flex items-center gap-2 text-sm">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-muted-foreground">Actual Delivery</p>
                <p className="font-medium">
                  {formatDate(delivery.actual_delivery_date)}
                </p>
              </div>
            </div>
          )}
          <div className="flex items-center gap-2 text-sm">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-muted-foreground">Created</p>
              <p className="font-medium">{formatDate(delivery.created_at)}</p>
            </div>
          </div>
          {delivery.notes && (
            <div className="col-span-full text-sm">
              <p className="text-muted-foreground">Notes</p>
              <p>{delivery.notes}</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Delivery Items</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>IMPA</TableHead>
                <TableHead>Description</TableHead>
                <TableHead className="text-right">Ordered</TableHead>
                <TableHead className="text-right">Delivered</TableHead>
                <TableHead className="text-right">Accepted</TableHead>
                <TableHead>Unit</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {delivery.items.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-mono text-xs">
                    {item.impa_code || "-"}
                  </TableCell>
                  <TableCell>{item.description}</TableCell>
                  <TableCell className="text-right">
                    {item.quantity_ordered}
                  </TableCell>
                  <TableCell className="text-right">
                    {item.quantity_delivered}
                  </TableCell>
                  <TableCell className="text-right">
                    {item.quantity_accepted ?? "-"}
                  </TableCell>
                  <TableCell>{item.unit_of_measure}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {pod && (
        <Card>
          <CardHeader>
            <CardTitle>Proof of Delivery</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {pod.gps_latitude && pod.gps_longitude && (
                <div className="flex items-center gap-2 text-sm">
                  <MapPinned className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-muted-foreground">GPS Location</p>
                    <p className="font-medium">
                      {pod.gps_latitude}, {pod.gps_longitude}
                    </p>
                    {pod.gps_accuracy && (
                      <p className="text-xs text-muted-foreground">
                        Accuracy: {pod.gps_accuracy}m
                      </p>
                    )}
                  </div>
                </div>
              )}
              {pod.receiver_name && (
                <div className="flex items-center gap-2 text-sm">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-muted-foreground">Receiver</p>
                    <p className="font-medium">{pod.receiver_name}</p>
                    {pod.receiver_designation && (
                      <p className="text-xs text-muted-foreground">
                        {pod.receiver_designation}
                      </p>
                    )}
                  </div>
                </div>
              )}
              {pod.delivered_at && (
                <div className="flex items-center gap-2 text-sm">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-muted-foreground">Delivered At</p>
                    <p className="font-medium">{formatDate(pod.delivered_at)}</p>
                  </div>
                </div>
              )}
            </div>

            {pod.photos.length > 0 && (
              <div>
                <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                  <Camera className="h-4 w-4" />
                  <span>Delivery Photos ({pod.photos.length})</span>
                </div>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
                  {pod.photos.map((photo) => (
                    <div
                      key={photo.id}
                      className="flex aspect-square items-center justify-center rounded-md border bg-muted"
                    >
                      <div className="text-center text-xs text-muted-foreground">
                        <Camera className="mx-auto mb-1 h-6 w-6" />
                        <span className="line-clamp-1">{photo.file_name}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
