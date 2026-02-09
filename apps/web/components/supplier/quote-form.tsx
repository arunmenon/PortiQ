"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { ArrowLeft, Send, Loader2 } from "lucide-react";
import { submitQuote } from "@/lib/api/supplier-portal";
import type { RfqLineItemResponse, QuoteLineItemCreate } from "@/lib/api/types";

interface QuoteFormProps {
  rfqId: string;
  lineItems: RfqLineItemResponse[];
  currency: string;
}

const PAYMENT_TERMS = [
  "Net 30",
  "Net 60",
  "Net 90",
  "Advance Payment",
  "LC at Sight",
  "50% Advance + 50% on Delivery",
];

const INCOTERMS = [
  "FOB",
  "CIF",
  "CFR",
  "EXW",
  "DDP",
  "DAP",
  "FCA",
];

interface LineItemRow {
  rfqLineItemId: string;
  description: string;
  quantity: number;
  unit: string;
  unitPrice: string;
  totalPrice: string;
  notes: string;
}

export function QuoteForm({ rfqId, lineItems, currency }: QuoteFormProps) {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [rows, setRows] = useState<LineItemRow[]>(
    lineItems.map((item) => ({
      rfqLineItemId: item.id,
      description: item.description,
      quantity: parseFloat(item.quantity),
      unit: item.unit_of_measure,
      unitPrice: "",
      totalPrice: "",
      notes: "",
    }))
  );

  const [paymentTerms, setPaymentTerms] = useState("");
  const [shippingTerms, setShippingTerms] = useState("");
  const [estimatedDeliveryDays, setEstimatedDeliveryDays] = useState("");
  const [quoteNotes, setQuoteNotes] = useState("");

  const grandTotal = useMemo(() => {
    return rows.reduce((sum, row) => {
      const total = parseFloat(row.totalPrice);
      return sum + (isNaN(total) ? 0 : total);
    }, 0);
  }, [rows]);

  function handleUnitPriceChange(index: number, value: string) {
    setRows((prev) => {
      const updated = [...prev];
      updated[index] = {
        ...updated[index],
        unitPrice: value,
        totalPrice:
          value && !isNaN(parseFloat(value))
            ? (parseFloat(value) * updated[index].quantity).toFixed(2)
            : "",
      };
      return updated;
    });
  }

  function handleTotalPriceChange(index: number, value: string) {
    setRows((prev) => {
      const updated = [...prev];
      updated[index] = {
        ...updated[index],
        totalPrice: value,
        unitPrice:
          value && !isNaN(parseFloat(value)) && updated[index].quantity > 0
            ? (parseFloat(value) / updated[index].quantity).toFixed(2)
            : "",
      };
      return updated;
    });
  }

  function handleNotesChange(index: number, value: string) {
    setRows((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], notes: value };
      return updated;
    });
  }

  const mutation = useMutation({
    mutationFn: () => {
      const quoteLineItems: QuoteLineItemCreate[] = rows
        .filter((row) => row.unitPrice && row.totalPrice)
        .map((row) => ({
          rfq_line_item_id: row.rfqLineItemId,
          unit_price: parseFloat(row.unitPrice),
          quantity: row.quantity,
          total_price: parseFloat(row.totalPrice),
          notes: row.notes || null,
        }));

      return submitQuote(rfqId, {
        currency,
        estimated_delivery_days: estimatedDeliveryDays
          ? parseInt(estimatedDeliveryDays)
          : null,
        payment_terms: paymentTerms || null,
        shipping_terms: shippingTerms || null,
        notes: quoteNotes || null,
        line_items: quoteLineItems,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["supplier-rfq", rfqId] });
      router.push(`/supplier/rfqs/${rfqId}`);
    },
  });

  const hasValidLineItems = rows.some(
    (row) => row.unitPrice && row.totalPrice && parseFloat(row.totalPrice) > 0
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push(`/supplier/rfqs/${rfqId}`)}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Submit Quote</h1>
          <p className="text-sm text-muted-foreground">
            Provide pricing for the requested line items
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Line Item Pricing</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Header row */}
            <div className="hidden md:grid md:grid-cols-12 gap-3 text-xs font-medium text-muted-foreground uppercase tracking-wider px-1">
              <div className="col-span-4">Item</div>
              <div className="col-span-1 text-right">Qty</div>
              <div className="col-span-1">Unit</div>
              <div className="col-span-2 text-right">Unit Price ({currency})</div>
              <div className="col-span-2 text-right">Total ({currency})</div>
              <div className="col-span-2">Notes</div>
            </div>
            <Separator />

            {rows.map((row, index) => (
              <div
                key={row.rfqLineItemId}
                className="grid grid-cols-1 md:grid-cols-12 gap-3 items-start"
              >
                <div className="md:col-span-4">
                  <Label className="md:hidden text-xs text-muted-foreground">
                    Item
                  </Label>
                  <p className="text-sm font-medium">{row.description}</p>
                </div>
                <div className="md:col-span-1 text-right">
                  <Label className="md:hidden text-xs text-muted-foreground">
                    Qty
                  </Label>
                  <p className="text-sm">{row.quantity}</p>
                </div>
                <div className="md:col-span-1">
                  <Label className="md:hidden text-xs text-muted-foreground">
                    Unit
                  </Label>
                  <p className="text-sm text-muted-foreground">{row.unit}</p>
                </div>
                <div className="md:col-span-2">
                  <Label className="md:hidden text-xs text-muted-foreground">
                    Unit Price
                  </Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    value={row.unitPrice}
                    onChange={(e) =>
                      handleUnitPriceChange(index, e.target.value)
                    }
                    className="text-right"
                  />
                </div>
                <div className="md:col-span-2">
                  <Label className="md:hidden text-xs text-muted-foreground">
                    Total
                  </Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    value={row.totalPrice}
                    onChange={(e) =>
                      handleTotalPriceChange(index, e.target.value)
                    }
                    className="text-right"
                  />
                </div>
                <div className="md:col-span-2">
                  <Label className="md:hidden text-xs text-muted-foreground">
                    Notes
                  </Label>
                  <Input
                    placeholder="Optional"
                    value={row.notes}
                    onChange={(e) => handleNotesChange(index, e.target.value)}
                  />
                </div>
              </div>
            ))}

            <Separator />

            <div className="flex justify-end">
              <div className="text-right">
                <p className="text-sm text-muted-foreground">Grand Total</p>
                <p className="text-2xl font-bold">
                  {currency} {grandTotal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Terms & Conditions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Payment Terms</Label>
              <Select value={paymentTerms} onValueChange={setPaymentTerms}>
                <SelectTrigger>
                  <SelectValue placeholder="Select terms" />
                </SelectTrigger>
                <SelectContent>
                  {PAYMENT_TERMS.map((term) => (
                    <SelectItem key={term} value={term}>
                      {term}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Shipping Terms (Incoterms)</Label>
              <Select value={shippingTerms} onValueChange={setShippingTerms}>
                <SelectTrigger>
                  <SelectValue placeholder="Select incoterms" />
                </SelectTrigger>
                <SelectContent>
                  {INCOTERMS.map((term) => (
                    <SelectItem key={term} value={term}>
                      {term}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Estimated Delivery (days)</Label>
              <Input
                type="number"
                min="1"
                placeholder="e.g. 14"
                value={estimatedDeliveryDays}
                onChange={(e) => setEstimatedDeliveryDays(e.target.value)}
              />
            </div>
          </div>
          <div className="mt-4 space-y-2">
            <Label>Additional Notes</Label>
            <Input
              placeholder="Any additional information for the buyer..."
              value={quoteNotes}
              onChange={(e) => setQuoteNotes(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {mutation.isError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Failed to submit quote. Please check your entries and try again.
        </div>
      )}

      <div className="flex items-center justify-end gap-3">
        <Button
          variant="outline"
          onClick={() => router.push(`/supplier/rfqs/${rfqId}`)}
        >
          Cancel
        </Button>
        <Button
          onClick={() => mutation.mutate()}
          disabled={!hasValidLineItems || mutation.isPending}
        >
          {mutation.isPending ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Send className="mr-2 h-4 w-4" />
          )}
          Submit Quote
        </Button>
      </div>
    </div>
  );
}
