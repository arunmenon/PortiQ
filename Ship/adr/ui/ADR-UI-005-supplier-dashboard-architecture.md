# ADR-UI-005: Supplier Dashboard Architecture

**Status:** Superseded
**Superseded By:** ADR-UI-014
**Date:** 2025-01-20 (original) | 2026-02-06 (superseded)
**Reason:** PortiQ AI-native UX specification replaces traditional dashboard paradigm. See ADR-UI-014 for the new architecture.
**Technical Area:** Frontend

---

> **This ADR has been superseded.** The PortiQ UX Design introduces an AI-assisted quoting paradigm that fundamentally changes the supplier workflow. Please refer to [ADR-UI-014](./ADR-UI-014-portiq-supplier-experience.md) for current architecture.

---

## Context (Historical)

The platform requires a dedicated supplier portal for managing quotes, orders, inventory, and customer relationships.

### Business Context
Supplier portal needs:
- RFQ discovery and bidding
- Quote management
- Order fulfillment tracking
- Inventory management
- Customer relationship management
- Analytics and reporting
- Invoice and payment tracking

### Technical Context
- Next.js 14 App Router (ADR-UI-001)
- Shared component library (ADR-UI-002)
- Same state management approach (ADR-UI-003)
- Role-based access control
- Real-time notifications for new RFQs

### Assumptions
- Suppliers may have multiple users
- Mobile access important for field operations
- Quick quote submission is critical
- Performance matters for large inventories

---

## Decision

We will build the supplier portal as a separate route group within the same Next.js application, sharing components with the buyer portal while having supplier-specific features and workflows.

---

## Implementation Notes

### Portal Structure

```
app/(supplier)/
├── layout.tsx              # Supplier dashboard layout
├── page.tsx                # Dashboard home
├── opportunities/
│   ├── page.tsx           # RFQ opportunities
│   └── [rfqId]/
│       ├── page.tsx       # RFQ detail
│       └── quote/
│           └── page.tsx   # Submit quote
├── quotes/
│   ├── page.tsx           # My quotes
│   └── [quoteId]/
│       └── page.tsx       # Quote detail
├── orders/
│   ├── page.tsx           # Orders to fulfill
│   └── [orderId]/
│       └── page.tsx       # Order detail
├── inventory/
│   ├── page.tsx           # Inventory list
│   └── upload/
│       └── page.tsx       # Bulk upload
├── customers/
│   └── page.tsx           # Customer list
├── analytics/
│   └── page.tsx           # Business analytics
└── settings/
    └── page.tsx           # Supplier settings
```

### Supplier Layout

```tsx
// app/(supplier)/layout.tsx
import { redirect } from 'next/navigation';
import { getSession } from '@/lib/auth';
import { SupplierSidebar } from '@/components/supplier/sidebar';
import { SupplierHeader } from '@/components/supplier/header';
import { NotificationBanner } from '@/components/supplier/notification-banner';

export default async function SupplierLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getSession();

  if (!session) {
    redirect('/login');
  }

  if (session.user.organizationType !== 'SUPPLIER') {
    redirect('/unauthorized');
  }

  const pendingCount = await getPendingOpportunitiesCount(
    session.user.organizationId
  );

  return (
    <div className="flex h-screen bg-gray-50">
      <SupplierSidebar pendingCount={pendingCount} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <SupplierHeader user={session.user} />
        <NotificationBanner />
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
```

### Supplier Dashboard

```tsx
// app/(supplier)/page.tsx
import { Suspense } from 'react';
import { SupplierMetrics } from '@/components/supplier/dashboard-metrics';
import { NewOpportunities } from '@/components/supplier/new-opportunities';
import { PendingOrders } from '@/components/supplier/pending-orders';
import { RevenueChart } from '@/components/supplier/revenue-chart';

export default function SupplierDashboard() {
  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Supplier Dashboard</h1>
        <QuickActions />
      </div>

      <Suspense fallback={<MetricsSkeleton />}>
        <SupplierMetrics />
      </Suspense>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Suspense fallback={<ChartSkeleton />}>
            <RevenueChart />
          </Suspense>
        </div>
        <Suspense fallback={<CardSkeleton />}>
          <NewOpportunities />
        </Suspense>
      </div>

      <Suspense fallback={<TableSkeleton />}>
        <PendingOrders />
      </Suspense>
    </div>
  );
}

async function SupplierMetrics() {
  const metrics = await getSupplierMetrics();

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <MetricCard
        title="New Opportunities"
        value={metrics.newOpportunities}
        icon={<Bell />}
        href="/opportunities"
        highlight={metrics.newOpportunities > 0}
      />
      <MetricCard
        title="Pending Quotes"
        value={metrics.pendingQuotes}
        icon={<FileText />}
        href="/quotes?status=pending"
      />
      <MetricCard
        title="Active Orders"
        value={metrics.activeOrders}
        icon={<Package />}
        href="/orders?status=active"
      />
      <MetricCard
        title="Monthly Revenue"
        value={formatCurrency(metrics.monthlyRevenue)}
        trend={metrics.revenueTrend}
        icon={<DollarSign />}
      />
    </div>
  );
}
```

### RFQ Opportunities List

```tsx
// app/(supplier)/opportunities/page.tsx
import { Suspense } from 'react';
import { getOpportunities } from '@/lib/api/supplier/opportunities';
import { OpportunitiesTable } from '@/components/supplier/opportunities-table';
import { OpportunityFilters } from '@/components/supplier/opportunity-filters';

interface OpportunitiesPageProps {
  searchParams: {
    category?: string;
    port?: string;
    deadline?: string;
  };
}

export default function OpportunitiesPage({ searchParams }: OpportunitiesPageProps) {
  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">RFQ Opportunities</h1>
          <p className="text-muted-foreground">
            Discover and bid on new procurement requests
          </p>
        </div>
      </div>

      <OpportunityFilters />

      <Suspense fallback={<TableSkeleton />}>
        <OpportunitiesList searchParams={searchParams} />
      </Suspense>
    </div>
  );
}

async function OpportunitiesList({ searchParams }) {
  const opportunities = await getOpportunities(searchParams);

  return (
    <OpportunitiesTable
      opportunities={opportunities.data}
      pagination={opportunities.pagination}
    />
  );
}
```

### Quote Submission Form

```tsx
// app/(supplier)/opportunities/[rfqId]/quote/page.tsx
'use client';

import { useRouter } from 'next/navigation';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useRfqDetail } from '@/hooks/queries/use-rfqs';
import { useSubmitQuote } from '@/hooks/queries/use-quotes';
import { quoteSchema } from '@/lib/schemas/quote';

export default function SubmitQuotePage({ params }: { params: { rfqId: string } }) {
  const router = useRouter();
  const { data: rfq, isLoading } = useRfqDetail(params.rfqId);
  const submitQuote = useSubmitQuote();

  const form = useForm({
    resolver: zodResolver(quoteSchema),
    defaultValues: {
      validUntil: null,
      deliveryDays: 0,
      notes: '',
      lineItems: [],
    },
  });

  const { fields } = useFieldArray({
    control: form.control,
    name: 'lineItems',
  });

  // Initialize line items from RFQ
  useEffect(() => {
    if (rfq) {
      form.setValue(
        'lineItems',
        rfq.lineItems.map((item) => ({
          rfqLineItemId: item.id,
          productId: item.productId,
          productName: item.product.name,
          requestedQuantity: item.quantity,
          unit: item.unit,
          unitPrice: 0,
          notes: '',
        }))
      );
    }
  }, [rfq]);

  const onSubmit = async (data) => {
    await submitQuote.mutateAsync({
      rfqId: params.rfqId,
      ...data,
    });
    router.push(`/quotes`);
  };

  if (isLoading) return <QuoteFormSkeleton />;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Submit Quote</h1>
        <p className="text-muted-foreground">
          RFQ: {rfq.title} | Deadline: {formatDate(rfq.biddingDeadline)}
        </p>
      </div>

      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Line Items</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Product</TableHead>
                  <TableHead>Requested Qty</TableHead>
                  <TableHead>Unit Price</TableHead>
                  <TableHead>Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {fields.map((field, index) => (
                  <TableRow key={field.id}>
                    <TableCell>
                      <div>
                        <p className="font-medium">{field.productName}</p>
                        <p className="text-sm text-muted-foreground">
                          {field.requestedQuantity} {field.unit}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>{field.requestedQuantity} {field.unit}</TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        step="0.01"
                        {...form.register(`lineItems.${index}.unitPrice`, {
                          valueAsNumber: true,
                        })}
                        className="w-32"
                      />
                    </TableCell>
                    <TableCell>
                      {formatCurrency(
                        (form.watch(`lineItems.${index}.unitPrice`) || 0) *
                          field.requestedQuantity
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
              <TableFooter>
                <TableRow>
                  <TableCell colSpan={3} className="text-right font-bold">
                    Total Quote Value
                  </TableCell>
                  <TableCell className="font-bold">
                    {formatCurrency(calculateTotal(form.watch('lineItems')))}
                  </TableCell>
                </TableRow>
              </TableFooter>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quote Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <FormField
              name="deliveryDays"
              label="Delivery Lead Time (days)"
              type="number"
            />
            <FormField
              name="validUntil"
              label="Quote Valid Until"
              type="date"
            />
            <FormField
              name="notes"
              label="Additional Notes"
              component="textarea"
            />
          </CardContent>
        </Card>

        <div className="flex justify-end gap-4">
          <Button type="button" variant="outline" onClick={() => router.back()}>
            Cancel
          </Button>
          <Button type="submit" loading={submitQuote.isPending}>
            Submit Quote
          </Button>
        </div>
      </form>
    </div>
  );
}
```

### Order Fulfillment View

```tsx
// app/(supplier)/orders/[orderId]/page.tsx
import { Suspense } from 'react';
import { getSupplierOrder } from '@/lib/api/supplier/orders';
import { OrderTimeline } from '@/components/supplier/order-timeline';
import { OrderActions } from '@/components/supplier/order-actions';
import { ShipmentTracker } from '@/components/supplier/shipment-tracker';

export default async function SupplierOrderPage({
  params,
}: {
  params: { orderId: string };
}) {
  const order = await getSupplierOrder(params.orderId);

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Order #{order.orderNumber}</h1>
          <p className="text-muted-foreground">
            {order.buyer.name} | {formatDate(order.createdAt)}
          </p>
        </div>
        <Badge variant={getOrderStatusVariant(order.status)}>
          {order.status}
        </Badge>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Order Items</CardTitle>
            </CardHeader>
            <CardContent>
              <OrderItemsTable items={order.lineItems} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Shipment</CardTitle>
            </CardHeader>
            <CardContent>
              <ShipmentTracker order={order} />
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <OrderActions order={order} />
          <OrderTimeline order={order} />
        </div>
      </div>
    </div>
  );
}
```

### Inventory Management

```tsx
// app/(supplier)/inventory/page.tsx
'use client';

import { useState } from 'react';
import { useInventory, useUpdateInventory } from '@/hooks/queries/use-inventory';
import { InventoryTable } from '@/components/supplier/inventory-table';
import { InventoryFilters } from '@/components/supplier/inventory-filters';
import { BulkUpdateDialog } from '@/components/supplier/bulk-update-dialog';

export default function InventoryPage() {
  const [filters, setFilters] = useState({});
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const { data, isLoading } = useInventory(filters);

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Inventory Management</h1>
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link href="/inventory/upload">
              <Upload className="w-4 h-4 mr-2" />
              Bulk Upload
            </Link>
          </Button>
          {selectedItems.length > 0 && (
            <BulkUpdateDialog
              selectedItems={selectedItems}
              onComplete={() => setSelectedItems([])}
            />
          )}
        </div>
      </div>

      <InventoryFilters filters={filters} onFiltersChange={setFilters} />

      <InventoryTable
        items={data?.items || []}
        isLoading={isLoading}
        selectedItems={selectedItems}
        onSelectionChange={setSelectedItems}
      />
    </div>
  );
}
```

### Dependencies
- ADR-UI-001: Next.js 14+ App Router
- ADR-UI-002: Component Library (shadcn/ui)
- ADR-UI-003: State Management Strategy
- ADR-UI-012: Real-Time Notifications

### Migration Strategy
1. Set up supplier route group
2. Create layout and navigation
3. Build dashboard page
4. Implement opportunities discovery
5. Create quote submission workflow
6. Build order fulfillment features
7. Add inventory management

---

## Operational Considerations

### Data Visualization Standards

#### Chart Library & Standards

| Chart Type | Use Case | Library | Accessibility |
|------------|----------|---------|---------------|
| Line charts | Revenue trends, order volume | Recharts | ARIA labels, keyboard nav |
| Bar charts | Category comparisons | Recharts | Color-blind safe palette |
| Pie/Donut | Status distribution | Recharts | Pattern fills + colors |
| Data tables | Detailed breakdowns | TanStack Table | Sortable, filterable |
| Sparklines | Inline trends | Recharts | Tooltip on focus |
| KPI cards | Key metrics | Custom | Screen reader friendly |

#### Color Palette for Charts

```typescript
// Design system chart colors (color-blind safe)
export const chartColors = {
  primary: ['#0ea5e9', '#0284c7', '#0369a1', '#075985'], // Blues
  secondary: ['#f97316', '#ea580c', '#c2410c', '#9a3412'], // Oranges
  semantic: {
    success: '#22c55e',
    warning: '#f59e0b',
    error: '#ef4444',
    neutral: '#6b7280',
  },
  // Alternative patterns for accessibility
  patterns: ['solid', 'striped', 'dotted', 'crosshatch'],
};

// Chart configuration standard
export const chartDefaults = {
  animation: {
    duration: 300,
    easing: 'ease-out',
  },
  tooltip: {
    backgroundColor: 'hsl(var(--popover))',
    borderColor: 'hsl(var(--border))',
    textColor: 'hsl(var(--foreground))',
  },
  grid: {
    strokeDasharray: '3 3',
    stroke: 'hsl(var(--border))',
  },
};
```

#### Visualization Components

```typescript
// components/analytics/revenue-chart.tsx
export function RevenueChart({ data, period }: RevenueChartProps) {
  const { theme } = useTheme();

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Revenue</CardTitle>
          <CardDescription>Monthly revenue trend</CardDescription>
        </div>
        <PeriodSelector value={period} onChange={setPeriod} />
      </CardHeader>
      <CardContent>
        <div className="h-[300px]" role="img" aria-label="Revenue chart showing monthly trends">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid {...chartDefaults.grid} />
              <XAxis
                dataKey="month"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
                tickLine={false}
                tickFormatter={(value) => formatCurrency(value, { compact: true })}
              />
              <Tooltip
                content={<CustomTooltip />}
                {...chartDefaults.tooltip}
              />
              <Line
                type="monotone"
                dataKey="revenue"
                stroke={chartColors.primary[0]}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 6, fill: chartColors.primary[0] }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
```

### Real-Time Data Refresh Cadence

| Data Type | Refresh Method | Cadence | User Control |
|-----------|---------------|---------|--------------|
| New opportunities | WebSocket push | Instant | N/A |
| Bid updates | WebSocket push | Instant | N/A |
| Dashboard KPIs | Poll + push | 60 seconds | Manual refresh |
| Revenue charts | Poll | 5 minutes | Date range selector |
| Order status | WebSocket push | Instant | N/A |
| Inventory levels | Poll | 15 minutes | Manual refresh |
| Analytics reports | On-demand | User-triggered | Regenerate button |

#### Refresh Implementation

```typescript
// hooks/use-dashboard-metrics.ts
export function useDashboardMetrics() {
  return useQuery({
    queryKey: ['supplier', 'dashboard', 'metrics'],
    queryFn: getSupplierMetrics,
    staleTime: 1000 * 30, // 30 seconds
    refetchInterval: 1000 * 60, // Poll every 60 seconds
    refetchOnWindowFocus: true,
  });
}

// Real-time updates via WebSocket
export function useLiveOpportunities() {
  const queryClient = useQueryClient();

  useEffect(() => {
    const socket = getSocket();

    socket.on('new_rfq', (rfq) => {
      // Optimistically add to list
      queryClient.setQueryData(['opportunities'], (old) => [rfq, ...old]);
      // Also invalidate to ensure consistency
      queryClient.invalidateQueries({ queryKey: ['opportunities'] });
    });

    return () => socket.off('new_rfq');
  }, [queryClient]);
}
```

### Export & Reporting

#### Export Capabilities

| Report Type | Formats | Schedule Options | Data Range |
|------------|---------|-----------------|------------|
| Sales summary | PDF, Excel, CSV | Daily, Weekly, Monthly | Up to 2 years |
| Order history | Excel, CSV | On-demand, Monthly | Up to 5 years |
| Quote performance | PDF, Excel | Weekly, Monthly | Up to 1 year |
| Inventory report | Excel, CSV | Daily, On-demand | Current |
| Revenue analytics | PDF | Monthly, Quarterly | Up to 3 years |
| Tax/compliance | PDF | Quarterly, Annual | Up to 7 years |

#### Export Implementation

```typescript
// components/reports/export-dialog.tsx
export function ExportDialog({ reportType, defaultFilters }: ExportDialogProps) {
  const [format, setFormat] = useState<'pdf' | 'excel' | 'csv'>('excel');
  const [dateRange, setDateRange] = useState<DateRange>(defaultFilters.dateRange);
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const response = await api.post(`/reports/${reportType}/export`, {
        format,
        dateRange,
        filters: defaultFilters,
      }, {
        responseType: 'blob',
      });

      // Trigger download
      const url = window.URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${reportType}-${format}-${Date.now()}.${format}`;
      link.click();

      toast.success('Export completed');
    } catch (error) {
      toast.error('Export failed. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <Dialog>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Export Report</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>Format</Label>
            <RadioGroup value={format} onValueChange={setFormat}>
              <RadioGroupItem value="pdf">PDF</RadioGroupItem>
              <RadioGroupItem value="excel">Excel (.xlsx)</RadioGroupItem>
              <RadioGroupItem value="csv">CSV</RadioGroupItem>
            </RadioGroup>
          </div>
          <div>
            <Label>Date Range</Label>
            <DateRangePicker value={dateRange} onChange={setDateRange} />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={handleExport} loading={isExporting}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Scheduled report configuration
export function ScheduledReportSettings() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Scheduled Reports</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Report</TableHead>
              <TableHead>Frequency</TableHead>
              <TableHead>Recipients</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {/* Configurable scheduled reports */}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
```

### Notification Configuration

#### Supplier Notification Types

| Notification | Channel | Priority | User Configurable |
|--------------|---------|----------|------------------|
| New RFQ matching categories | Push + Email + In-app | High | Categories only |
| RFQ deadline approaching | Push + In-app | High | Time threshold |
| Quote accepted | Push + Email + In-app | High | No |
| Quote rejected | Email + In-app | Medium | Yes |
| Order received | Push + Email + In-app | High | No |
| Payment received | Email + In-app | Medium | No |
| Low inventory alert | Email + In-app | Medium | Threshold |
| Weekly performance digest | Email | Low | Yes |

### Day One KPIs (Mission Critical)

| KPI | Definition | Target | Display |
|-----|------------|--------|---------|
| **New Opportunities** | RFQs matching supplier categories in last 24h | Response rate > 30% | Badge count + list |
| **Pending Quotes** | Submitted quotes awaiting buyer decision | Track conversion | Card with status breakdown |
| **Active Orders** | Orders in fulfillment (not shipped) | 100% on-time | List with due dates |
| **Monthly Revenue** | Total revenue MTD | N/A (benchmark) | Chart with YoY comparison |
| **Response Time** | Avg time from RFQ publish to quote submit | < 4 hours | Trend indicator |
| **Win Rate** | Quotes accepted / quotes submitted (30d) | > 25% | Percentage with trend |

#### KPI Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │ New Opps    │ │ Pending     │ │ Active      │ │ Monthly   │ │
│  │ 12          │ │ Quotes: 8   │ │ Orders: 15  │ │ Revenue   │ │
│  │ [View All]  │ │ [View All]  │ │ [View All]  │ │ $45,230   │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
│                                                                 │
│  ┌──────────────────────────────────┐ ┌──────────────────────┐ │
│  │ Revenue Trend (Chart)            │ │ Quick Actions        │ │
│  │                                  │ │ • View New RFQs      │ │
│  │ [Sparkline: Last 12 months]      │ │ • Update Inventory   │ │
│  │                                  │ │ • Check Orders       │ │
│  └──────────────────────────────────┘ └──────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Recent Activity                                           │  │
│  │ • New RFQ: "Deck Supplies for MV Pacific" - 2 min ago    │  │
│  │ • Quote Accepted: #Q-2024-001 - 1 hour ago               │  │
│  │ • Order Shipped: #ORD-2024-155 - 3 hours ago             │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Open Questions - Resolved

- **Q:** Which KPIs are mission critical for suppliers on day one?
  - **A:** The following 6 KPIs are mission critical for supplier day-one success:
    1. **New Opportunities (count)**: Immediate visibility into business potential
    2. **Pending Quotes (count + breakdown)**: Track what's awaiting decision
    3. **Active Orders (count + due dates)**: Fulfillment workload visibility
    4. **Monthly Revenue (amount + trend)**: Business health indicator
    5. **Response Time (average)**: Competitive metric for winning bids
    6. **Win Rate (percentage)**: Quote quality and pricing effectiveness

    These KPIs are displayed prominently at the top of the dashboard with one-click navigation to detailed views. Real-time updates via WebSocket ensure suppliers never miss time-sensitive opportunities.

---

## References
- [B2B Supplier Portal Best Practices](https://www.nngroup.com/articles/b2b-usability/)
- [Dashboard Design Patterns](https://www.smashingmagazine.com/2022/06/designing-better-dashboards/)
