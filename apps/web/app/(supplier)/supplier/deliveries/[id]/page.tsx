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
  Truck,
  Navigation,
  Camera,
  Pen,
} from "lucide-react";

type DeliveryStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "IN_TRANSIT"
  | "DELIVERED"
  | "ACCEPTED"
  | "DISPUTED"
  | "CANCELLED";

interface DeliveryItem {
  id: string;
  product_name: string;
  impa_code: string | null;
  quantity_ordered: number;
  quantity_delivered: number;
  unit_of_measure: string;
}

interface GpsCoordinates {
  latitude: number;
  longitude: number;
  accuracy: number;
}

interface DeliveryDetail {
  id: string;
  delivery_number: string;
  order_id: string;
  order_number: string;
  buyer_organization_name: string;
  status: DeliveryStatus;
  vessel_name: string | null;
  delivery_port: string | null;
  gps_coordinates: GpsCoordinates | null;
  photos: string[];
  receiver_name: string | null;
  receiver_designation: string | null;
  receiver_contact: string | null;
  signature_url: string | null;
  notes: string | null;
  items: DeliveryItem[];
  submitted_at: string | null;
  delivered_at: string | null;
  created_at: string;
  updated_at: string;
}

const STATUS_COLORS: Record<DeliveryStatus, string> = {
  DRAFT: "bg-gray-100 text-gray-800",
  SUBMITTED: "bg-blue-100 text-blue-800",
  IN_TRANSIT: "bg-yellow-100 text-yellow-800",
  DELIVERED: "bg-green-100 text-green-800",
  ACCEPTED: "bg-emerald-100 text-emerald-800",
  DISPUTED: "bg-red-100 text-red-800",
  CANCELLED: "bg-gray-100 text-gray-600",
};

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function getSupplierDelivery(
  deliveryId: string,
): Promise<DeliveryDetail> {
  return apiClient.get<DeliveryDetail>(
    `/api/v1/supplier/deliveries/${deliveryId}`,
  );
}

export default function SupplierDeliveryDetailPage() {
  const params = useParams();
  const router = useRouter();
  const deliveryId = params.id as string;

  const {
    data: delivery,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["supplier-delivery", deliveryId],
    queryFn: () => getSupplierDelivery(deliveryId),
    enabled: !!deliveryId,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error || !delivery) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Truck className="mb-4 h-12 w-12 text-muted-foreground" />
        <p className="text-lg font-medium">Delivery not found</p>
        <p className="text-sm text-muted-foreground">
          The delivery you are looking for does not exist or you do not have
          access.
        </p>
        <Button variant="outline" className="mt-4" onClick={() => router.back()}>
          Go Back
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">
              {delivery.delivery_number}
            </h1>
            <Badge
              className={STATUS_COLORS[delivery.status]}
              variant="secondary"
            >
              {delivery.status.replace(/_/g, " ")}
            </Badge>
          </div>
          <p className="text-muted-foreground">
            For order {delivery.order_number} &mdash;{" "}
            {delivery.buyer_organization_name}
          </p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Building2 className="h-4 w-4" />
              <span>Buyer</span>
            </div>
            <p className="mt-1 font-medium">
              {delivery.buyer_organization_name}
            </p>
          </CardContent>
        </Card>

        {delivery.delivery_port && (
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <MapPin className="h-4 w-4" />
                <span>Delivery Port</span>
              </div>
              <p className="mt-1 font-medium">{delivery.delivery_port}</p>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Calendar className="h-4 w-4" />
              <span>
                {delivery.delivered_at ? "Delivered" : "Created"}
              </span>
            </div>
            <p className="mt-1 font-medium">
              {formatDate(delivery.delivered_at || delivery.created_at)}
            </p>
          </CardContent>
        </Card>
      </div>

      {delivery.gps_coordinates && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Navigation className="h-5 w-5" />
              GPS Location
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm">
              Lat: {delivery.gps_coordinates.latitude.toFixed(6)}, Lng:{" "}
              {delivery.gps_coordinates.longitude.toFixed(6)}
            </p>
            <p className="text-sm text-muted-foreground">
              Accuracy: {delivery.gps_coordinates.accuracy.toFixed(0)}m
            </p>
          </CardContent>
        </Card>
      )}

      {delivery.photos.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Camera className="h-5 w-5" />
              Photos ({delivery.photos.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-6">
              {delivery.photos.map((photo, idx) => (
                <div
                  key={idx}
                  className="aspect-square rounded-md border bg-muted"
                >
                  {/* Photo thumbnails will render here when photo URLs are available */}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Delivered Items</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Product</TableHead>
                <TableHead>IMPA Code</TableHead>
                <TableHead className="text-right">Ordered</TableHead>
                <TableHead className="text-right">Delivered</TableHead>
                <TableHead>Unit</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {delivery.items.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-medium">
                    {item.product_name}
                  </TableCell>
                  <TableCell>
                    {item.impa_code ? (
                      <Badge variant="secondary" className="font-mono text-xs">
                        {item.impa_code}
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    {item.quantity_ordered}
                  </TableCell>
                  <TableCell className="text-right">
                    {item.quantity_delivered}
                  </TableCell>
                  <TableCell>{item.unit_of_measure}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {(delivery.receiver_name || delivery.signature_url) && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Pen className="h-5 w-5" />
              Receiver Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {delivery.receiver_name && (
              <div>
                <p className="text-sm text-muted-foreground">Name</p>
                <p className="font-medium">{delivery.receiver_name}</p>
              </div>
            )}
            {delivery.receiver_designation && (
              <div>
                <p className="text-sm text-muted-foreground">Designation</p>
                <p className="font-medium">{delivery.receiver_designation}</p>
              </div>
            )}
            {delivery.receiver_contact && (
              <div>
                <p className="text-sm text-muted-foreground">Contact</p>
                <p className="font-medium">{delivery.receiver_contact}</p>
              </div>
            )}
            {delivery.signature_url && (
              <div>
                <p className="text-sm text-muted-foreground">Signature</p>
                <div className="mt-1 h-24 w-48 rounded-md border bg-muted">
                  {/* Signature image renders here */}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {delivery.notes && (
        <Card>
          <CardHeader>
            <CardTitle>Notes</CardTitle>
          </CardHeader>
          <CardContent>
            <p>{delivery.notes}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
