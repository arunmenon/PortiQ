"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { getInvoice, getReconciliation } from "@/lib/api/invoices";
import type { InvoiceStatus } from "@/lib/api/invoices";
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
  TableFooter,
} from "@/components/ui/table";
import { ArrowLeft, Receipt, Calendar } from "lucide-react";
import Link from "next/link";

const statusStyles: Record<InvoiceStatus, string> = {
  DRAFT: "border-gray-300 bg-gray-100 text-gray-700 hover:bg-gray-100",
  READY: "border-transparent bg-blue-100 text-blue-700 hover:bg-blue-100",
  SENT: "border-transparent bg-indigo-100 text-indigo-700 hover:bg-indigo-100",
  ACKNOWLEDGED: "border-transparent bg-purple-100 text-purple-700 hover:bg-purple-100",
  DISPUTED: "border-transparent bg-amber-100 text-amber-700 hover:bg-amber-100",
  PAID: "border-transparent bg-emerald-100 text-emerald-700 hover:bg-emerald-100",
  CANCELLED: "border-transparent bg-red-100 text-red-700 hover:bg-red-100",
};

const statusLabels: Record<InvoiceStatus, string> = {
  DRAFT: "Draft",
  READY: "Ready",
  SENT: "Sent",
  ACKNOWLEDGED: "Acknowledged",
  DISPUTED: "Disputed",
  PAID: "Paid",
  CANCELLED: "Cancelled",
};

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatCurrency(amount: string, currency: string): string {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
  }).format(parseFloat(amount));
}

export default function InvoiceDetailPage() {
  const params = useParams();
  const invoiceId = params.id as string;

  const { data: invoice, isLoading: invoiceLoading } = useQuery({
    queryKey: ["invoice", invoiceId],
    queryFn: () => getInvoice(invoiceId),
  });

  const { data: reconciliation } = useQuery({
    queryKey: ["invoice-reconciliation", invoiceId],
    queryFn: () => getReconciliation(invoiceId),
    enabled: !!invoice,
  });

  if (invoiceLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!invoice) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Receipt className="mb-4 h-12 w-12 text-muted-foreground" />
        <p className="text-lg font-medium">Invoice not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/invoices">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Invoices
          </Link>
        </Button>
      </div>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {invoice.invoice_number}
          </h1>
          {invoice.supplier_name && (
            <p className="text-muted-foreground">{invoice.supplier_name}</p>
          )}
        </div>
        <Badge variant="outline" className={statusStyles[invoice.status]}>
          {statusLabels[invoice.status]}
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Invoice Summary</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="text-sm">
            <p className="text-muted-foreground">Subtotal</p>
            <p className="text-lg font-semibold">
              {formatCurrency(invoice.subtotal, invoice.currency)}
            </p>
          </div>
          <div className="text-sm">
            <p className="text-muted-foreground">Tax</p>
            <p className="text-lg font-semibold">
              {formatCurrency(invoice.tax_amount, invoice.currency)}
            </p>
          </div>
          <div className="text-sm">
            <p className="text-muted-foreground">Credit Adjustment</p>
            <p className="text-lg font-semibold">
              {formatCurrency(invoice.credit_adjustment, invoice.currency)}
            </p>
          </div>
          <div className="text-sm">
            <p className="text-muted-foreground">Total</p>
            <p className="text-2xl font-bold">
              {formatCurrency(invoice.total_amount, invoice.currency)}
            </p>
          </div>
          {invoice.due_date && (
            <div className="flex items-center gap-2 text-sm">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-muted-foreground">Due Date</p>
                <p className="font-medium">{formatDate(invoice.due_date)}</p>
              </div>
            </div>
          )}
          {invoice.paid_at && (
            <div className="flex items-center gap-2 text-sm">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-muted-foreground">Paid At</p>
                <p className="font-medium">{formatDate(invoice.paid_at)}</p>
              </div>
            </div>
          )}
          {invoice.notes && (
            <div className="col-span-full text-sm">
              <p className="text-muted-foreground">Notes</p>
              <p>{invoice.notes}</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Reconciliation</CardTitle>
        </CardHeader>
        <CardContent>
          {reconciliation ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>IMPA</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="text-right">Ordered</TableHead>
                  <TableHead className="text-right">Delivered</TableHead>
                  <TableHead className="text-right">Accepted</TableHead>
                  <TableHead className="text-right">Unit Price</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reconciliation.rows.map((row, index) => (
                  <TableRow key={index}>
                    <TableCell className="font-mono text-xs">
                      {row.impa_code || "-"}
                    </TableCell>
                    <TableCell>{row.description}</TableCell>
                    <TableCell className="text-right">
                      {row.quantity_ordered}
                    </TableCell>
                    <TableCell className="text-right">
                      {row.quantity_delivered}
                    </TableCell>
                    <TableCell className="text-right">
                      {row.quantity_accepted}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(row.unit_price, invoice.currency)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(row.line_total, invoice.currency)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
              <TableFooter>
                <TableRow>
                  <TableCell colSpan={6} className="text-right font-medium">
                    Subtotal
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {formatCurrency(reconciliation.subtotal, invoice.currency)}
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell colSpan={6} className="text-right font-medium">
                    Tax
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {formatCurrency(
                      reconciliation.tax_amount,
                      invoice.currency,
                    )}
                  </TableCell>
                </TableRow>
                {parseFloat(reconciliation.credit_adjustment) !== 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-right font-medium">
                      Credit Adjustment
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {formatCurrency(
                        reconciliation.credit_adjustment,
                        invoice.currency,
                      )}
                    </TableCell>
                  </TableRow>
                )}
                <TableRow>
                  <TableCell colSpan={6} className="text-right text-lg font-bold">
                    Total
                  </TableCell>
                  <TableCell className="text-right text-lg font-bold">
                    {formatCurrency(reconciliation.total, invoice.currency)}
                  </TableCell>
                </TableRow>
              </TableFooter>
            </Table>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>IMPA</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="text-right">Ordered</TableHead>
                  <TableHead className="text-right">Delivered</TableHead>
                  <TableHead className="text-right">Accepted</TableHead>
                  <TableHead className="text-right">Unit Price</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invoice.line_items.map((item) => (
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
                      {item.quantity_accepted}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(item.unit_price, invoice.currency)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(item.total_price, invoice.currency)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
