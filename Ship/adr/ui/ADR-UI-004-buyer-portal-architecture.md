# ADR-UI-004: Buyer Portal Architecture

**Status:** Superseded
**Superseded By:** ADR-UI-013
**Date:** 2025-01-20 (original) | 2026-02-06 (superseded)
**Reason:** PortiQ AI-native UX specification replaces traditional dashboard paradigm. See ADR-UI-013 for the new architecture.
**Technical Area:** Frontend

---

> **This ADR has been superseded.** The PortiQ UX Design introduces a conversation-first, AI-native interface that fundamentally changes the interaction paradigm. Please refer to [ADR-UI-013](./ADR-UI-013-portiq-buyer-experience.md) for current architecture.

---

## Context (Historical)

The platform requires a dedicated buyer portal for ship chandlery procurement activities.

### Business Context
Buyer portal needs:
- Product catalog browsing and search
- RFQ creation and management
- Quote comparison and acceptance
- Order tracking and history
- Invoice management
- Supplier relationship management
- Dashboard with key metrics

### Technical Context
- Next.js 14 App Router (ADR-UI-001)
- shadcn/ui components (ADR-UI-002)
- React Query for data fetching (ADR-UI-003)
- Role-based access control
- Real-time updates for bidding

### Assumptions
- Primary user is procurement officer
- Desktop-first, mobile-responsive
- Complex workflows need good UX
- Performance critical for large catalogs

---

## Decision Drivers

- User workflow efficiency
- Feature discoverability
- Performance for large datasets
- Mobile responsiveness
- Accessibility compliance

---

## Decision

We will build the buyer portal as a multi-page application with a consistent dashboard layout, using Next.js App Router with server components for data fetching and client components for interactivity.

---

## Implementation Notes

### Portal Structure

```
app/(buyer)/
├── layout.tsx              # Buyer dashboard layout
├── page.tsx                # Dashboard home
├── catalog/
│   ├── page.tsx           # Product search
│   └── [productId]/
│       └── page.tsx       # Product detail
├── rfqs/
│   ├── page.tsx           # RFQ list
│   ├── new/
│   │   └── page.tsx       # Create RFQ
│   └── [rfqId]/
│       ├── page.tsx       # RFQ detail
│       ├── quotes/
│       │   └── page.tsx   # Compare quotes
│       └── award/
│           └── page.tsx   # Award RFQ
├── orders/
│   ├── page.tsx           # Order list
│   └── [orderId]/
│       └── page.tsx       # Order detail
├── suppliers/
│   ├── page.tsx           # Supplier directory
│   └── [supplierId]/
│       └── page.tsx       # Supplier profile
├── invoices/
│   └── page.tsx           # Invoice list
└── settings/
    └── page.tsx           # Buyer settings
```

### Dashboard Layout

```tsx
// app/(buyer)/layout.tsx
import { redirect } from 'next/navigation';
import { getSession } from '@/lib/auth';
import { BuyerSidebar } from '@/components/buyer/sidebar';
import { BuyerHeader } from '@/components/buyer/header';

export default async function BuyerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getSession();

  if (!session) {
    redirect('/login');
  }

  if (session.user.organizationType !== 'BUYER') {
    redirect('/unauthorized');
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <BuyerSidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <BuyerHeader user={session.user} />
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
```

### Dashboard Home

```tsx
// app/(buyer)/page.tsx
import { Suspense } from 'react';
import { DashboardMetrics } from '@/components/buyer/dashboard-metrics';
import { RecentOrders } from '@/components/buyer/recent-orders';
import { ActiveRfqs } from '@/components/buyer/active-rfqs';
import { PendingActions } from '@/components/buyer/pending-actions';

export default function BuyerDashboard() {
  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <Suspense fallback={<MetricsSkeleton />}>
        <DashboardMetrics />
      </Suspense>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Suspense fallback={<CardSkeleton />}>
          <PendingActions />
        </Suspense>

        <Suspense fallback={<CardSkeleton />}>
          <ActiveRfqs />
        </Suspense>
      </div>

      <Suspense fallback={<TableSkeleton />}>
        <RecentOrders />
      </Suspense>
    </div>
  );
}

// Server Component for metrics
async function DashboardMetrics() {
  const metrics = await getBuyerMetrics();

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <MetricCard
        title="Active RFQs"
        value={metrics.activeRfqs}
        trend={metrics.rfqTrend}
        icon={<FileText />}
      />
      <MetricCard
        title="Pending Orders"
        value={metrics.pendingOrders}
        trend={metrics.orderTrend}
        icon={<ShoppingCart />}
      />
      <MetricCard
        title="Monthly Spend"
        value={formatCurrency(metrics.monthlySpend)}
        trend={metrics.spendTrend}
        icon={<DollarSign />}
      />
      <MetricCard
        title="Savings"
        value={formatCurrency(metrics.savings)}
        subtext={`${metrics.savingsPercent}% vs. list price`}
        icon={<TrendingDown />}
      />
    </div>
  );
}
```

### RFQ Creation Workflow

```tsx
// app/(buyer)/rfqs/new/page.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { RfqBasicInfo } from '@/components/rfq/rfq-basic-info';
import { RfqLineItems } from '@/components/rfq/rfq-line-items';
import { RfqSuppliers } from '@/components/rfq/rfq-suppliers';
import { RfqReview } from '@/components/rfq/rfq-review';
import { createRfqSchema } from '@/lib/schemas/rfq';
import { useCreateRfq } from '@/hooks/queries/use-rfqs';

const steps = [
  { id: 'basic', title: 'Basic Information' },
  { id: 'items', title: 'Line Items' },
  { id: 'suppliers', title: 'Invite Suppliers' },
  { id: 'review', title: 'Review & Publish' },
];

export default function CreateRfqPage() {
  const [currentStep, setCurrentStep] = useState(0);
  const router = useRouter();
  const createRfq = useCreateRfq();

  const form = useForm({
    resolver: zodResolver(createRfqSchema),
    defaultValues: {
      title: '',
      description: '',
      deliveryPort: '',
      deliveryDate: null,
      biddingDeadline: null,
      lineItems: [],
      invitedSuppliers: [],
      visibility: 'INVITED',
    },
  });

  const onSubmit = async (data: CreateRfqInput) => {
    const rfq = await createRfq.mutateAsync(data);
    router.push(`/rfqs/${rfq.id}`);
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Create Request for Quote</h1>

      {/* Stepper */}
      <nav className="mb-8">
        <ol className="flex items-center">
          {steps.map((step, index) => (
            <li key={step.id} className="flex items-center">
              <div
                className={cn(
                  'flex items-center justify-center w-8 h-8 rounded-full',
                  index <= currentStep
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-gray-200'
                )}
              >
                {index < currentStep ? <Check className="w-4 h-4" /> : index + 1}
              </div>
              <span className="ml-2 text-sm font-medium">{step.title}</span>
              {index < steps.length - 1 && (
                <div className="w-12 h-0.5 mx-4 bg-gray-200" />
              )}
            </li>
          ))}
        </ol>
      </nav>

      <FormProvider {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)}>
          {currentStep === 0 && <RfqBasicInfo />}
          {currentStep === 1 && <RfqLineItems />}
          {currentStep === 2 && <RfqSuppliers />}
          {currentStep === 3 && <RfqReview />}

          <div className="flex justify-between mt-8">
            <Button
              type="button"
              variant="outline"
              onClick={() => setCurrentStep((s) => s - 1)}
              disabled={currentStep === 0}
            >
              Previous
            </Button>

            {currentStep < steps.length - 1 ? (
              <Button
                type="button"
                onClick={() => setCurrentStep((s) => s + 1)}
              >
                Next
              </Button>
            ) : (
              <Button type="submit" loading={createRfq.isPending}>
                Publish RFQ
              </Button>
            )}
          </div>
        </form>
      </FormProvider>
    </div>
  );
}
```

### Quote Comparison View

```tsx
// app/(buyer)/rfqs/[rfqId]/quotes/page.tsx
import { Suspense } from 'react';
import { getRfqWithQuotes } from '@/lib/api/rfqs';
import { QuoteComparisonTable } from '@/components/rfq/quote-comparison-table';
import { QuoteAnalysis } from '@/components/rfq/quote-analysis';

interface QuotesPageProps {
  params: { rfqId: string };
}

export default async function QuotesPage({ params }: QuotesPageProps) {
  return (
    <div className="p-6 space-y-6">
      <Suspense fallback={<ComparisonSkeleton />}>
        <QuotesComparison rfqId={params.rfqId} />
      </Suspense>
    </div>
  );
}

async function QuotesComparison({ rfqId }: { rfqId: string }) {
  const { rfq, quotes } = await getRfqWithQuotes(rfqId);

  if (quotes.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <FileQuestion className="w-12 h-12 mx-auto text-gray-400 mb-4" />
          <h3 className="text-lg font-medium">No quotes yet</h3>
          <p className="text-muted-foreground">
            Suppliers have until {formatDate(rfq.biddingDeadline)} to submit quotes.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">{rfq.title}</h1>
          <p className="text-muted-foreground">
            {quotes.length} quotes received
          </p>
        </div>
        <Badge>{rfq.status}</Badge>
      </div>

      <QuoteAnalysis quotes={quotes} rfq={rfq} />

      <Card>
        <CardHeader>
          <CardTitle>Quote Comparison</CardTitle>
        </CardHeader>
        <CardContent>
          <QuoteComparisonTable rfq={rfq} quotes={quotes} />
        </CardContent>
      </Card>
    </>
  );
}
```

### Product Catalog with Search

```tsx
// app/(buyer)/catalog/page.tsx
import { Suspense } from 'react';
import { ProductSearch } from '@/components/catalog/product-search';
import { ProductGrid } from '@/components/catalog/product-grid';
import { CategoryFilters } from '@/components/catalog/category-filters';

interface CatalogPageProps {
  searchParams: {
    q?: string;
    category?: string;
    page?: string;
  };
}

export default function CatalogPage({ searchParams }: CatalogPageProps) {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Product Catalog</h1>

      <div className="flex gap-6">
        <aside className="w-64 flex-shrink-0">
          <Suspense fallback={<FiltersSkeleton />}>
            <CategoryFilters selectedCategory={searchParams.category} />
          </Suspense>
        </aside>

        <div className="flex-1 space-y-6">
          <ProductSearch initialQuery={searchParams.q} />

          <Suspense
            key={JSON.stringify(searchParams)}
            fallback={<ProductGridSkeleton />}
          >
            <ProductResults searchParams={searchParams} />
          </Suspense>
        </div>
      </div>
    </div>
  );
}

async function ProductResults({
  searchParams,
}: {
  searchParams: CatalogPageProps['searchParams'];
}) {
  const products = await searchProducts({
    query: searchParams.q,
    category: searchParams.category,
    page: parseInt(searchParams.page || '1'),
  });

  return (
    <ProductGrid
      products={products.data}
      pagination={products.pagination}
    />
  );
}
```

### Sidebar Navigation

```tsx
// components/buyer/sidebar.tsx
'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import {
  LayoutDashboard,
  Search,
  FileText,
  ShoppingCart,
  Users,
  Receipt,
  Settings,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useUIStore } from '@/stores/ui-store';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Catalog', href: '/catalog', icon: Search },
  { name: 'RFQs', href: '/rfqs', icon: FileText },
  { name: 'Orders', href: '/orders', icon: ShoppingCart },
  { name: 'Suppliers', href: '/suppliers', icon: Users },
  { name: 'Invoices', href: '/invoices', icon: Receipt },
];

export function BuyerSidebar() {
  const pathname = usePathname();
  const { sidebarOpen, toggleSidebar } = useUIStore();

  return (
    <aside
      className={cn(
        'bg-white border-r transition-all duration-300',
        sidebarOpen ? 'w-64' : 'w-16'
      )}
    >
      <div className="flex h-16 items-center justify-center border-b">
        {sidebarOpen ? (
          <span className="text-xl font-bold">Ship Chandlery</span>
        ) : (
          <span className="text-xl font-bold">SC</span>
        )}
      </div>

      <nav className="p-4 space-y-2">
        {navigation.map((item) => {
          const isActive = pathname === item.href ||
            (item.href !== '/' && pathname.startsWith(item.href));

          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg transition-colors',
                isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-gray-600 hover:bg-gray-100'
              )}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              {sidebarOpen && <span>{item.name}</span>}
            </Link>
          );
        })}
      </nav>

      <div className="absolute bottom-4 left-4">
        <Link href="/settings" className="flex items-center gap-3 text-gray-600">
          <Settings className="w-5 h-5" />
          {sidebarOpen && <span>Settings</span>}
        </Link>
      </div>
    </aside>
  );
}
```

### Dependencies
- ADR-UI-001: Next.js 14+ App Router
- ADR-UI-002: Component Library (shadcn/ui)
- ADR-UI-003: State Management Strategy
- ADR-UI-011: Search UX Pattern

### Migration Strategy
1. Set up buyer route group
2. Create layout and navigation
3. Build dashboard page
4. Implement catalog search
5. Create RFQ workflow
6. Build order management
7. Add real-time features

---

## Operational Considerations

### Core User Journeys

#### Primary User Journeys with Performance Targets

| Journey | Steps | Target Time | Performance Budget |
|---------|-------|-------------|-------------------|
| **Product Search to Cart** | Search → Filter → View → Add | < 5 seconds total | 200ms search, 100ms filter |
| **RFQ Creation** | New → Items → Suppliers → Publish | < 3 minutes | 500ms per step transition |
| **Quote Comparison** | View RFQ → Compare → Select → Award | < 2 minutes | 1s quote load, instant compare |
| **Order Tracking** | Dashboard → Orders → Detail → Track | < 10 seconds | 300ms list, 500ms detail |
| **Reorder from History** | Orders → Select → Copy → Modify → Submit | < 1 minute | 400ms order copy |

#### Journey Flow: RFQ Creation (Primary)

```
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: Basic Info        Step 2: Line Items                   │
│  ┌─────────────────┐       ┌─────────────────┐                 │
│  │ Title           │       │ Product Search  │──► Add Item     │
│  │ Description     │──────►│ Manual Entry    │                 │
│  │ Delivery Port   │       │ IMPA Lookup     │                 │
│  │ Deadline        │       │ Import CSV      │                 │
│  └─────────────────┘       └─────────────────┘                 │
│         │                          │                            │
│         ▼                          ▼                            │
│  Step 3: Suppliers         Step 4: Review                       │
│  ┌─────────────────┐       ┌─────────────────┐                 │
│  │ Search Suppliers│       │ Summary         │                 │
│  │ Favorites       │──────►│ Preview         │──► Publish      │
│  │ By Category     │       │ Terms           │                 │
│  │ Invite New      │       │ Attachments     │                 │
│  └─────────────────┘       └─────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

### Performance Targets

| Page/Action | TTFB | FCP | LCP | TTI | CLS |
|------------|------|-----|-----|-----|-----|
| Dashboard | < 300ms | < 1s | < 2s | < 3s | < 0.1 |
| Catalog search | < 200ms | < 800ms | < 1.5s | < 2s | < 0.05 |
| Product detail | < 250ms | < 1s | < 2s | < 2.5s | < 0.1 |
| RFQ list | < 300ms | < 1s | < 2s | < 3s | < 0.1 |
| RFQ detail | < 400ms | < 1.2s | < 2.5s | < 3.5s | < 0.1 |
| Quote comparison | < 500ms | < 1.5s | < 3s | < 4s | < 0.1 |
| Order list | < 300ms | < 1s | < 2s | < 3s | < 0.1 |

#### Performance Monitoring Implementation

```typescript
// lib/performance/web-vitals.ts
import { onCLS, onFID, onLCP, onTTFB, onFCP } from 'web-vitals';

const vitalsEndpoint = '/api/analytics/vitals';

function sendToAnalytics(metric) {
  const body = JSON.stringify({
    name: metric.name,
    value: metric.value,
    rating: metric.rating,
    delta: metric.delta,
    id: metric.id,
    page: window.location.pathname,
    userAgent: navigator.userAgent,
  });

  if (navigator.sendBeacon) {
    navigator.sendBeacon(vitalsEndpoint, body);
  } else {
    fetch(vitalsEndpoint, { body, method: 'POST', keepalive: true });
  }
}

// Initialize in app
export function initWebVitals() {
  onCLS(sendToAnalytics);
  onFID(sendToAnalytics);
  onLCP(sendToAnalytics);
  onTTFB(sendToAnalytics);
  onFCP(sendToAnalytics);
}
```

### Role-Based Access Control in UI

#### Buyer Portal Roles

| Role | Permissions | UI Restrictions |
|------|------------|-----------------|
| **Buyer Admin** | Full access | None |
| **Procurement Manager** | Create RFQs, approve orders, view all | Cannot manage users |
| **Procurement Officer** | Create RFQs, view own, limited approval | Orders > $10K need approval |
| **Viewer** | Read-only access | No create/edit buttons shown |

#### Permission-Based UI Implementation

```typescript
// lib/permissions/buyer-permissions.ts
export const BuyerPermissions = {
  // RFQ permissions
  RFQ_CREATE: 'rfq:create',
  RFQ_EDIT: 'rfq:edit',
  RFQ_DELETE: 'rfq:delete',
  RFQ_PUBLISH: 'rfq:publish',
  RFQ_AWARD: 'rfq:award',

  // Order permissions
  ORDER_CREATE: 'order:create',
  ORDER_APPROVE: 'order:approve',
  ORDER_CANCEL: 'order:cancel',

  // Spending limits
  APPROVE_UNDER_10K: 'approve:under_10k',
  APPROVE_UNDER_50K: 'approve:under_50k',
  APPROVE_UNLIMITED: 'approve:unlimited',

  // Admin
  USER_MANAGE: 'user:manage',
  SETTINGS_EDIT: 'settings:edit',
} as const;

// Role definitions
export const BuyerRoles = {
  ADMIN: [
    ...Object.values(BuyerPermissions),
  ],
  PROCUREMENT_MANAGER: [
    BuyerPermissions.RFQ_CREATE,
    BuyerPermissions.RFQ_EDIT,
    BuyerPermissions.RFQ_PUBLISH,
    BuyerPermissions.RFQ_AWARD,
    BuyerPermissions.ORDER_CREATE,
    BuyerPermissions.ORDER_APPROVE,
    BuyerPermissions.APPROVE_UNDER_50K,
  ],
  PROCUREMENT_OFFICER: [
    BuyerPermissions.RFQ_CREATE,
    BuyerPermissions.RFQ_EDIT,
    BuyerPermissions.ORDER_CREATE,
    BuyerPermissions.APPROVE_UNDER_10K,
  ],
  VIEWER: [],
};

// Permission hook
export function usePermission(permission: string): boolean {
  const { user } = useAuth();
  return user?.permissions?.includes(permission) ?? false;
}

// Permission gate component
export function Can({ permission, children, fallback = null }) {
  const hasPermission = usePermission(permission);
  return hasPermission ? children : fallback;
}

// Usage
<Can permission={BuyerPermissions.RFQ_CREATE}>
  <Button onClick={createRfq}>Create RFQ</Button>
</Can>
```

### Audit Visibility in UI

#### Audit Trail Display

```typescript
// components/audit/audit-trail.tsx
interface AuditEntry {
  id: string;
  action: string;
  entityType: string;
  entityId: string;
  userId: string;
  userName: string;
  timestamp: string;
  changes: Record<string, { old: any; new: any }>;
  ipAddress: string;
}

export function AuditTrail({ entityType, entityId }: AuditTrailProps) {
  const { data: entries } = useAuditLog(entityType, entityId);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <History className="h-5 w-5" />
          Activity History
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {entries?.map((entry) => (
            <div key={entry.id} className="flex gap-4 border-l-2 pl-4 pb-4">
              <Avatar className="h-8 w-8">
                <AvatarFallback>{entry.userName[0]}</AvatarFallback>
              </Avatar>
              <div className="flex-1">
                <p className="text-sm">
                  <span className="font-medium">{entry.userName}</span>
                  {' '}{formatAction(entry.action)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {formatDistanceToNow(new Date(entry.timestamp))} ago
                </p>
                {entry.changes && Object.keys(entry.changes).length > 0 && (
                  <AuditChanges changes={entry.changes} />
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
```

#### Audited Actions

| Entity | Audited Actions | Retention |
|--------|----------------|-----------|
| RFQ | Create, Edit, Publish, Close, Delete | 7 years |
| Quote | Submit, Update, Withdraw, Accept, Reject | 7 years |
| Order | Create, Approve, Cancel, Status Change | 7 years |
| User | Login, Logout, Permission Change | 2 years |
| Settings | Any modification | 2 years |

### Web/Mobile Parity Strategy

#### Feature Parity Matrix

| Feature | Web | Mobile | Parity Strategy |
|---------|-----|--------|-----------------|
| Product search | Full | Full | Shared search API, UI adapts |
| RFQ creation | Full wizard | Simplified flow | Mobile: fewer steps, essential fields |
| Quote comparison | Side-by-side table | Swipe cards | Different UI, same data |
| Order tracking | Full timeline | Simplified list | Mobile: key milestones only |
| Document upload | Drag & drop | Camera + picker | Platform-native approach |
| Notifications | In-app + email | Push + in-app | Mobile: push priority |
| Offline | Limited | Full | Mobile: SQLite sync |

#### Shared Code Strategy

```
packages/
├── shared/
│   ├── api/           # API client (axios/fetch)
│   ├── schemas/       # Zod validation schemas
│   ├── types/         # TypeScript interfaces
│   ├── utils/         # Business logic utilities
│   └── constants/     # Shared constants
│
├── ui-web/            # Web-specific components
└── ui-mobile/         # Mobile-specific components

# Sharing percentage target: 40% code shared
# - API layer: 90% shared
# - Business logic: 70% shared
# - UI components: 10% shared (design tokens only)
```

### Open Questions - Resolved

- **Q:** How will you ensure parity between web and mobile experiences?
  - **A:** We implement a tiered parity strategy:
    1. **API parity**: 100% - Same REST endpoints, same response schemas
    2. **Feature parity**: 90% core features - Mobile simplifies complex workflows (e.g., 4-step RFQ wizard becomes 2 steps)
    3. **Data parity**: 100% - Same data visible, different presentation
    4. **Offline parity**: Mobile leads - Mobile has full offline; web has limited draft support
    5. **Shared packages**: `@ship-chandlery/shared` contains API clients, types, validation schemas, business logic
    6. **Platform-native UX**: Each platform uses native patterns (web: tables, mobile: cards) while maintaining functional equivalence
    7. **Testing**: E2E tests verify critical flows work identically on both platforms

---

## References
- [Next.js Route Groups](https://nextjs.org/docs/app/building-your-application/routing/route-groups)
- [Dashboard Design Patterns](https://www.nngroup.com/articles/dashboard-design/)
