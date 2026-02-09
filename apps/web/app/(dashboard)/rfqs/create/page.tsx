"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { createRfq } from "@/lib/api/rfqs";
import type { RfqCreate, RfqLineItemCreate } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { ArrowLeft, Plus, Trash2, Save } from "lucide-react";
import { IntelligenceSidebar } from "@/components/portiq/intelligence-sidebar";

// ---------------------------------------------------------------------------
// Line item form state (without id, used for local state)
// ---------------------------------------------------------------------------

interface LineItemFormData {
  localId: number;
  description: string;
  quantity: number;
  unit_of_measure: string;
  impa_code: string;
  notes: string;
}

let nextLocalId = 1;

function createEmptyLineItem(lineNumber: number): LineItemFormData {
  return {
    localId: nextLocalId++,
    description: "",
    quantity: 1,
    unit_of_measure: "EA",
    impa_code: "",
    notes: "",
  };
}

// ---------------------------------------------------------------------------
// Create RFQ Page
// ---------------------------------------------------------------------------

export default function CreateRfqPage() {
  const router = useRouter();

  // --- Form state ---

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [deliveryPort, setDeliveryPort] = useState("");
  const [deliveryDate, setDeliveryDate] = useState("");
  const [biddingDeadline, setBiddingDeadline] = useState("");
  const [allowPartialQuotes, setAllowPartialQuotes] = useState(false);
  const [allowQuoteRevision, setAllowQuoteRevision] = useState(true);
  const [requireAllLineItems, setRequireAllLineItems] = useState(false);
  const [notes, setNotes] = useState("");
  const [lineItems, setLineItems] = useState<LineItemFormData[]>([]);

  // --- Mutation ---

  const createMutation = useMutation({
    mutationFn: (data: RfqCreate) => createRfq(data),
    onSuccess: (newRfq) => {
      router.push(`/rfqs/${newRfq.id}`);
    },
  });

  // --- Line item handlers ---

  function handleAddLineItem() {
    setLineItems((prev) => [
      ...prev,
      createEmptyLineItem(prev.length + 1),
    ]);
  }

  function handleRemoveLineItem(localId: number) {
    setLineItems((prev) => prev.filter((item) => item.localId !== localId));
  }

  function handleLineItemChange(
    localId: number,
    field: keyof Omit<LineItemFormData, "localId">,
    value: string | number
  ) {
    setLineItems((prev) =>
      prev.map((item) =>
        item.localId === localId ? { ...item, [field]: value } : item
      )
    );
  }

  // --- Form submission ---

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();

    const rfqLineItems: RfqLineItemCreate[] = lineItems.map(
      (item, index) => ({
        line_number: index + 1,
        description: item.description,
        quantity: item.quantity,
        unit_of_measure: item.unit_of_measure,
        impa_code: item.impa_code || null,
        notes: item.notes || null,
      })
    );

    const payload: RfqCreate = {
      title,
      description: description || null,
      currency: currency || "USD",
      delivery_port: deliveryPort || null,
      delivery_date: deliveryDate ? new Date(deliveryDate).toISOString() : null,
      bidding_deadline: biddingDeadline
        ? new Date(biddingDeadline).toISOString()
        : null,
      allow_partial_quotes: allowPartialQuotes,
      allow_quote_revision: allowQuoteRevision,
      require_all_line_items: requireAllLineItems,
      notes: notes || null,
      line_items: rfqLineItems.length > 0 ? rfqLineItems : undefined,
    };

    createMutation.mutate(payload);
  }

  const isSubmitting = createMutation.isPending;

  // Collect IMPA codes from line items for intelligence sidebar
  const impaCodes = lineItems
    .map((item) => item.impa_code)
    .filter((code) => code.length > 0);

  return (
    <div className="space-y-6">
      {/* Back button */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => router.push("/rfqs")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to RFQs
        </Button>
      </div>

      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Create RFQ</h1>
        <p className="text-muted-foreground">
          Create a new request for quotes to collect supplier bids.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main form column */}
        <div className="lg:col-span-2">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Basic Information */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Basic Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="title">
                    Title <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="title"
                    placeholder="Enter RFQ title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="description">Description</Label>
                  <textarea
                    id="description"
                    placeholder="Describe what you need..."
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    rows={3}
                    className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  />
                </div>

                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <div className="space-y-2">
                    <Label htmlFor="currency">Currency</Label>
                    <Input
                      id="currency"
                      placeholder="USD"
                      value={currency}
                      onChange={(e) =>
                        setCurrency(e.target.value.toUpperCase().slice(0, 3))
                      }
                      maxLength={3}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="deliveryPort">Delivery Port</Label>
                    <Input
                      id="deliveryPort"
                      placeholder="e.g. Mumbai Port"
                      value={deliveryPort}
                      onChange={(e) => setDeliveryPort(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="deliveryDate">Delivery Date</Label>
                    <input
                      id="deliveryDate"
                      type="datetime-local"
                      value={deliveryDate}
                      onChange={(e) => setDeliveryDate(e.target.value)}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="biddingDeadline">Bidding Deadline</Label>
                  <input
                    id="biddingDeadline"
                    type="datetime-local"
                    value={biddingDeadline}
                    onChange={(e) => setBiddingDeadline(e.target.value)}
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  />
                </div>
              </CardContent>
            </Card>

            {/* Settings */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={allowPartialQuotes}
                      onChange={(e) => setAllowPartialQuotes(e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                    />
                    <div>
                      <p className="text-sm font-medium">Allow Partial Quotes</p>
                      <p className="text-xs text-muted-foreground">
                        Suppliers can submit quotes for a subset of line items
                      </p>
                    </div>
                  </label>

                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={allowQuoteRevision}
                      onChange={(e) => setAllowQuoteRevision(e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                    />
                    <div>
                      <p className="text-sm font-medium">Allow Quote Revision</p>
                      <p className="text-xs text-muted-foreground">
                        Suppliers can revise their quotes before the deadline
                      </p>
                    </div>
                  </label>

                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={requireAllLineItems}
                      onChange={(e) => setRequireAllLineItems(e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                    />
                    <div>
                      <p className="text-sm font-medium">
                        Require All Line Items
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Suppliers must quote all line items to submit
                      </p>
                    </div>
                  </label>
                </div>

                <Separator />

                <div className="space-y-2">
                  <Label htmlFor="notes">Notes</Label>
                  <textarea
                    id="notes"
                    placeholder="Additional notes or instructions for suppliers..."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows={3}
                    className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  />
                </div>
              </CardContent>
            </Card>

            {/* Line Items */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">Line Items</CardTitle>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleAddLineItem}
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    Add Line Item
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {lineItems.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-8 text-center">
                    <p className="text-sm text-muted-foreground">
                      No line items added yet. Click &quot;Add Line Item&quot; to
                      add items to this RFQ.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {lineItems.map((item, index) => (
                      <div
                        key={item.localId}
                        className="rounded-lg border p-4 space-y-3"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-muted-foreground">
                            Line Item #{index + 1}
                          </span>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => handleRemoveLineItem(item.localId)}
                            className="text-red-500 hover:text-red-700 hover:bg-red-50"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>

                        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                          <div className="space-y-1 sm:col-span-2">
                            <Label className="text-xs">
                              Description{" "}
                              <span className="text-red-500">*</span>
                            </Label>
                            <Input
                              placeholder="Item description"
                              value={item.description}
                              onChange={(e) =>
                                handleLineItemChange(
                                  item.localId,
                                  "description",
                                  e.target.value
                                )
                              }
                              required
                            />
                          </div>

                          <div className="space-y-1">
                            <Label className="text-xs">
                              Quantity{" "}
                              <span className="text-red-500">*</span>
                            </Label>
                            <Input
                              type="number"
                              min={0}
                              step="any"
                              placeholder="1"
                              value={item.quantity}
                              onChange={(e) =>
                                handleLineItemChange(
                                  item.localId,
                                  "quantity",
                                  parseFloat(e.target.value) || 0
                                )
                              }
                              required
                            />
                          </div>

                          <div className="space-y-1">
                            <Label className="text-xs">
                              Unit of Measure{" "}
                              <span className="text-red-500">*</span>
                            </Label>
                            <Input
                              placeholder="EA, KG, LTR..."
                              value={item.unit_of_measure}
                              onChange={(e) =>
                                handleLineItemChange(
                                  item.localId,
                                  "unit_of_measure",
                                  e.target.value
                                )
                              }
                              required
                            />
                          </div>

                          <div className="space-y-1">
                            <Label className="text-xs">IMPA Code</Label>
                            <Input
                              placeholder="e.g. 370101"
                              value={item.impa_code}
                              onChange={(e) =>
                                handleLineItemChange(
                                  item.localId,
                                  "impa_code",
                                  e.target.value
                                )
                              }
                            />
                          </div>

                          <div className="space-y-1 sm:col-span-2 lg:col-span-3">
                            <Label className="text-xs">Notes</Label>
                            <Input
                              placeholder="Additional notes for this item..."
                              value={item.notes}
                              onChange={(e) =>
                                handleLineItemChange(
                                  item.localId,
                                  "notes",
                                  e.target.value
                                )
                              }
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Error message */}
            {createMutation.isError && (
              <div className="rounded-md border border-red-200 bg-red-50 p-4">
                <p className="text-sm text-red-700">
                  Failed to create RFQ. Please check your input and try again.
                </p>
              </div>
            )}

            {/* Submit */}
            <div className="flex items-center justify-end gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => router.push("/rfqs")}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting || !title.trim()}>
                {isSubmitting ? (
                  <>
                    <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Save className="mr-2 h-4 w-4" />
                    Create RFQ
                  </>
                )}
              </Button>
            </div>
          </form>
        </div>

        {/* Intelligence sidebar column */}
        <div className="lg:col-span-1">
          <IntelligenceSidebar
            deliveryPort={deliveryPort}
            impaCodes={impaCodes.length > 0 ? impaCodes : undefined}
            deliveryDate={deliveryDate || undefined}
            biddingDeadline={biddingDeadline || undefined}
          />
        </div>
      </div>
    </div>
  );
}
