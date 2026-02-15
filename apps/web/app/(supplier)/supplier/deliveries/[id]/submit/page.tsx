"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  MapPin,
  Camera,
  Pen,
  Send,
  Navigation,
  Plus,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Ship,
} from "lucide-react";

interface OrderItem {
  id: string;
  product_name: string;
  impa_code: string | null;
  quantity: number;
  unit_of_measure: string;
}

interface OrderForDelivery {
  id: string;
  order_number: string;
  buyer_organization_name: string;
  vessel_name: string | null;
  delivery_port: string | null;
  items: OrderItem[];
}

interface GpsData {
  lat: number;
  lng: number;
  accuracy: number;
}

interface DeliveryItemInput {
  order_item_id: string;
  quantity_delivered: number;
}

interface DeliverySubmission {
  order_id: string;
  gps_latitude: number | null;
  gps_longitude: number | null;
  gps_accuracy: number | null;
  items: DeliveryItemInput[];
  receiver_name: string;
  receiver_designation: string;
  receiver_contact: string;
  notes: string;
}

async function getOrderForDelivery(orderId: string): Promise<OrderForDelivery> {
  return apiClient.get<OrderForDelivery>(
    `/api/v1/supplier/orders/${orderId}`,
  );
}

async function submitDelivery(data: DeliverySubmission): Promise<{ id: string }> {
  return apiClient.post<{ id: string }>(
    "/api/v1/supplier/deliveries",
    data,
  );
}

export default function DeliverySubmitPage() {
  const params = useParams();
  const router = useRouter();
  const orderId = params.id as string;

  const [gps, setGps] = useState<GpsData | null>(null);
  const [gpsLoading, setGpsLoading] = useState(false);
  const [gpsError, setGpsError] = useState<string | null>(null);
  const [photoCount, setPhotoCount] = useState(0);
  const [deliveredQtys, setDeliveredQtys] = useState<Record<string, number>>(
    {},
  );
  const [receiverName, setReceiverName] = useState("");
  const [receiverDesignation, setReceiverDesignation] = useState("");
  const [receiverContact, setReceiverContact] = useState("");
  const [notes, setNotes] = useState("");

  const {
    data: order,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["supplier-order-for-delivery", orderId],
    queryFn: () => getOrderForDelivery(orderId),
    enabled: !!orderId,
  });

  useEffect(() => {
    if (order) {
      const initial: Record<string, number> = {};
      order.items.forEach((item) => {
        initial[item.id] = item.quantity;
      });
      setDeliveredQtys((prev) => {
        if (Object.keys(prev).length === 0) return initial;
        return prev;
      });
    }
  }, [order]);

  const mutation = useMutation({
    mutationFn: submitDelivery,
    onSuccess: (result) => {
      router.push(`/supplier/deliveries/${result.id}`);
    },
  });

  const captureGPS = () => {
    if (!navigator.geolocation) {
      setGpsError("Geolocation is not supported by this browser.");
      return;
    }
    setGpsLoading(true);
    setGpsError(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGps({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        });
        setGpsLoading(false);
      },
      (err) => {
        setGpsError(err.message);
        setGpsLoading(false);
      },
      { enableHighAccuracy: true },
    );
  };

  const handleSubmit = () => {
    if (!order) return;
    const items: DeliveryItemInput[] = order.items.map((item) => ({
      order_item_id: item.id,
      quantity_delivered: deliveredQtys[item.id] ?? item.quantity,
    }));

    mutation.mutate({
      order_id: orderId,
      gps_latitude: gps?.lat ?? null,
      gps_longitude: gps?.lng ?? null,
      gps_accuracy: gps?.accuracy ?? null,
      items,
      receiver_name: receiverName,
      receiver_designation: receiverDesignation,
      receiver_contact: receiverContact,
      notes,
    });
  };

  if (isLoading) {
    return (
      <div className="mx-auto max-w-lg space-y-6 p-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <AlertCircle className="mb-4 h-12 w-12 text-muted-foreground" />
        <p className="text-lg font-medium">Order not found</p>
        <p className="text-sm text-muted-foreground">
          Cannot load order details for delivery submission.
        </p>
        <Button variant="outline" className="mt-4" onClick={() => router.back()}>
          Go Back
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Submit Delivery</h1>
          <p className="text-sm text-muted-foreground">
            {order.order_number} &mdash; {order.buyer_organization_name}
          </p>
        </div>
      </div>

      {order.vessel_name && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Ship className="h-4 w-4" />
          <span>Vessel: {order.vessel_name}</span>
          {order.delivery_port && (
            <>
              <span className="mx-1">&bull;</span>
              <MapPin className="h-4 w-4" />
              <span>{order.delivery_port}</span>
            </>
          )}
        </div>
      )}

      {/* GPS Capture */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Navigation className="h-5 w-5" />
            Location
          </CardTitle>
        </CardHeader>
        <CardContent>
          {gps ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm text-green-700">
                <CheckCircle2 className="h-4 w-4" />
                <span>Location captured</span>
              </div>
              <div className="rounded-md bg-muted p-3 text-sm">
                <p>Lat: {gps.lat.toFixed(6)}</p>
                <p>Lng: {gps.lng.toFixed(6)}</p>
                <p className="text-muted-foreground">
                  Accuracy: {gps.accuracy.toFixed(0)}m
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={captureGPS}>
                Recapture
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              <Button
                onClick={captureGPS}
                disabled={gpsLoading}
                className="w-full"
                variant="outline"
              >
                <MapPin className="mr-2 h-4 w-4" />
                {gpsLoading ? "Capturing..." : "Capture Location"}
              </Button>
              {gpsError && (
                <p className="text-sm text-destructive">{gpsError}</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Photos */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Camera className="h-5 w-5" />
            Photos
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            {Array.from({ length: photoCount }).map((_, idx) => (
              <div
                key={idx}
                className="flex h-20 w-20 items-center justify-center rounded-md border bg-muted"
              >
                <Camera className="h-6 w-6 text-muted-foreground" />
              </div>
            ))}
            <button
              type="button"
              onClick={() => setPhotoCount((c) => c + 1)}
              className="flex h-20 w-20 items-center justify-center rounded-md border-2 border-dashed border-muted-foreground/25 transition-colors hover:border-muted-foreground/50"
            >
              <Plus className="h-6 w-6 text-muted-foreground" />
            </button>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Tap + to add delivery photos
          </p>
        </CardContent>
      </Card>

      {/* Item Quantities */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Items Delivered</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {order.items.map((item) => (
            <div key={item.id} className="rounded-md border p-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-medium">{item.product_name}</p>
                  {item.impa_code && (
                    <Badge
                      variant="secondary"
                      className="mt-1 font-mono text-xs"
                    >
                      IMPA {item.impa_code}
                    </Badge>
                  )}
                </div>
              </div>
              <div className="mt-3 flex items-center gap-3">
                <div className="text-sm text-muted-foreground">
                  Ordered: {item.quantity} {item.unit_of_measure}
                </div>
                <div className="flex items-center gap-2">
                  <Label htmlFor={`qty-${item.id}`} className="text-sm">
                    Delivered:
                  </Label>
                  <Input
                    id={`qty-${item.id}`}
                    type="number"
                    min={0}
                    max={item.quantity}
                    value={deliveredQtys[item.id] ?? item.quantity}
                    onChange={(e) =>
                      setDeliveredQtys((prev) => ({
                        ...prev,
                        [item.id]: parseInt(e.target.value, 10) || 0,
                      }))
                    }
                    className="w-24"
                  />
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Receiver Info */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Pen className="h-5 w-5" />
            Receiver Information
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="receiver-name">Name</Label>
            <Input
              id="receiver-name"
              placeholder="Receiver's full name"
              value={receiverName}
              onChange={(e) => setReceiverName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="receiver-designation">Designation</Label>
            <Input
              id="receiver-designation"
              placeholder="e.g. Chief Officer, Bosun"
              value={receiverDesignation}
              onChange={(e) => setReceiverDesignation(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="receiver-contact">Contact</Label>
            <Input
              id="receiver-contact"
              placeholder="Phone number or email"
              value={receiverContact}
              onChange={(e) => setReceiverContact(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {/* Signature */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Pen className="h-5 w-5" />
            Signature
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-32 items-center justify-center rounded-md border-2 border-dashed border-muted-foreground/25">
            <p className="text-sm text-muted-foreground">Tap to sign</p>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Signature canvas will be enabled in a future update
          </p>
        </CardContent>
      </Card>

      {/* Notes */}
      <div className="space-y-2">
        <Label htmlFor="delivery-notes">Notes (optional)</Label>
        <Input
          id="delivery-notes"
          placeholder="Any additional notes about the delivery..."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </div>

      {/* Submit */}
      {mutation.isError && (
        <div className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
          Failed to submit delivery. Please try again.
        </div>
      )}

      <Button
        className="w-full"
        size="lg"
        onClick={handleSubmit}
        disabled={mutation.isPending}
      >
        <Send className="mr-2 h-4 w-4" />
        {mutation.isPending ? "Submitting..." : "Submit Delivery"}
      </Button>
    </div>
  );
}
