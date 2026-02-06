# ADR-UI-001: Next.js 14+ App Router

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Frontend

---

## Context

The platform requires a modern web framework for the buyer and supplier portals with good performance and developer experience.

### Business Context
Web application requirements:
- Fast page loads for better user experience
- SEO for public pages (landing, product catalog)
- Complex interactive dashboards
- Mobile-responsive design
- Multiple user portals (buyer, supplier, admin)

### Technical Context
- React ecosystem familiarity
- TypeScript for type safety
- Need for both static and dynamic content
- API integration with NestJS backend
- Real-time features for bidding

### Assumptions
- React remains the primary frontend library
- Server-side rendering beneficial for SEO
- Team familiar with React/TypeScript
- Vercel deployment not required (self-hosted)

---

## Decision Drivers

- Developer experience
- Performance (Core Web Vitals)
- SEO capabilities
- React Server Components support
- Deployment flexibility
- Community and ecosystem

---

## Considered Options

### Option 1: Next.js 14+ (App Router)
**Description:** React framework with App Router and RSC support.

**Pros:**
- React Server Components
- Built-in routing and layouts
- Streaming and Suspense
- Excellent TypeScript support
- Large ecosystem
- File-based routing

**Cons:**
- Learning curve for App Router
- Some patterns still evolving
- Vendor-influenced framework

### Option 2: Remix
**Description:** Full-stack React framework focused on web standards.

**Pros:**
- Web standards focused
- Excellent data loading
- Good error handling
- Progressive enhancement

**Cons:**
- Smaller ecosystem
- Less React Server Components
- Different mental model

### Option 3: Vite + React Router
**Description:** Build tool with separate routing.

**Pros:**
- Fast development
- Full control
- No framework lock-in
- Simple setup

**Cons:**
- More setup required
- No built-in SSR
- Manual optimization needed

---

## Decision

**Chosen Option:** Next.js 14+ with App Router

We will use Next.js 14+ with the App Router for the web frontend, leveraging React Server Components for improved performance.

### Rationale
Next.js provides the best balance of performance, developer experience, and ecosystem. The App Router enables streaming, Suspense, and React Server Components. File-based routing simplifies navigation. Strong TypeScript support aligns with our backend.

---

## Consequences

### Positive
- React Server Components for performance
- Streaming for better perceived performance
- Strong TypeScript integration
- Large component ecosystem
- Excellent documentation

### Negative
- App Router learning curve
- **Mitigation:** Training, starter templates
- Framework coupling
- **Mitigation:** Keep business logic in separate packages

### Risks
- Breaking changes in Next.js: Pin versions, test upgrades
- Performance issues: Monitoring, optimization
- Complexity: Start simple, add features incrementally

---

## Implementation Notes

### Project Structure

```
apps/web/
├── app/
│   ├── (auth)/
│   │   ├── login/
│   │   │   └── page.tsx
│   │   ├── register/
│   │   │   └── page.tsx
│   │   └── layout.tsx
│   ├── (dashboard)/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── orders/
│   │   │   ├── page.tsx
│   │   │   └── [id]/
│   │   │       └── page.tsx
│   │   ├── rfqs/
│   │   │   ├── page.tsx
│   │   │   ├── new/
│   │   │   │   └── page.tsx
│   │   │   └── [id]/
│   │   │       └── page.tsx
│   │   └── catalog/
│   │       └── page.tsx
│   ├── (marketing)/
│   │   ├── page.tsx
│   │   └── layout.tsx
│   ├── api/
│   │   └── [...route]/
│   │       └── route.ts
│   ├── layout.tsx
│   └── globals.css
├── components/
│   ├── ui/
│   ├── forms/
│   └── layouts/
├── lib/
│   ├── api/
│   ├── hooks/
│   └── utils/
├── next.config.js
└── tailwind.config.ts
```

### Root Layout

```tsx
// app/layout.tsx
import { Inter } from 'next/font/google';
import { Providers } from '@/components/providers';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata = {
  title: {
    default: 'Ship Chandlery',
    template: '%s | Ship Chandlery',
  },
  description: 'B2B Maritime Procurement Platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

### Dashboard Layout with Server Components

```tsx
// app/(dashboard)/layout.tsx
import { redirect } from 'next/navigation';
import { getSession } from '@/lib/auth';
import { Sidebar } from '@/components/layouts/sidebar';
import { Header } from '@/components/layouts/header';

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getSession();

  if (!session) {
    redirect('/login');
  }

  return (
    <div className="flex h-screen">
      <Sidebar user={session.user} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header user={session.user} />
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
```

### Server Component with Data Fetching

```tsx
// app/(dashboard)/orders/page.tsx
import { Suspense } from 'react';
import { getOrders } from '@/lib/api/orders';
import { OrdersTable } from '@/components/orders/orders-table';
import { OrdersTableSkeleton } from '@/components/orders/orders-table-skeleton';
import { PageHeader } from '@/components/ui/page-header';

interface OrdersPageProps {
  searchParams: {
    status?: string;
    page?: string;
    search?: string;
  };
}

export default function OrdersPage({ searchParams }: OrdersPageProps) {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Orders"
        description="View and manage your orders"
        actions={
          <Link href="/orders/new">
            <Button>Create Order</Button>
          </Link>
        }
      />

      <Suspense fallback={<OrdersTableSkeleton />}>
        <OrdersList searchParams={searchParams} />
      </Suspense>
    </div>
  );
}

// Server Component that fetches data
async function OrdersList({ searchParams }: { searchParams: OrdersPageProps['searchParams'] }) {
  const { status, page = '1', search } = searchParams;

  const orders = await getOrders({
    status,
    page: parseInt(page),
    search,
  });

  return <OrdersTable orders={orders.data} pagination={orders.pagination} />;
}
```

### Client Component with Interactivity

```tsx
// components/orders/orders-table.tsx
'use client';

import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Pagination } from '@/components/ui/pagination';

interface OrdersTableProps {
  orders: Order[];
  pagination: PaginationMeta;
}

export function OrdersTable({ orders, pagination }: OrdersTableProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [selected, setSelected] = useState<string[]>([]);

  const handlePageChange = (page: number) => {
    const params = new URLSearchParams(searchParams);
    params.set('page', page.toString());
    router.push(`/orders?${params.toString()}`);
  };

  return (
    <div className="space-y-4">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Order #</TableHead>
            <TableHead>Supplier</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Total</TableHead>
            <TableHead>Date</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {orders.map((order) => (
            <TableRow
              key={order.id}
              className="cursor-pointer"
              onClick={() => router.push(`/orders/${order.id}`)}
            >
              <TableCell>{order.orderNumber}</TableCell>
              <TableCell>{order.supplier.name}</TableCell>
              <TableCell>
                <Badge variant={getStatusVariant(order.status)}>
                  {order.status}
                </Badge>
              </TableCell>
              <TableCell>{formatCurrency(order.total)}</TableCell>
              <TableCell>{formatDate(order.createdAt)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <Pagination
        currentPage={pagination.page}
        totalPages={pagination.totalPages}
        onPageChange={handlePageChange}
      />
    </div>
  );
}
```

### Server Actions

```tsx
// app/(dashboard)/rfqs/new/actions.ts
'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { z } from 'zod';
import { createRfq } from '@/lib/api/rfqs';
import { getSession } from '@/lib/auth';

const createRfqSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  description: z.string().optional(),
  deadline: z.string().datetime(),
  lineItems: z.array(z.object({
    productId: z.string(),
    quantity: z.number().positive(),
    unit: z.string(),
  })).min(1, 'At least one line item is required'),
});

export async function createRfqAction(formData: FormData) {
  const session = await getSession();

  if (!session) {
    throw new Error('Unauthorized');
  }

  const rawData = {
    title: formData.get('title'),
    description: formData.get('description'),
    deadline: formData.get('deadline'),
    lineItems: JSON.parse(formData.get('lineItems') as string),
  };

  const validatedData = createRfqSchema.parse(rawData);

  const rfq = await createRfq({
    ...validatedData,
    buyerOrganizationId: session.user.organizationId,
  });

  revalidatePath('/rfqs');
  redirect(`/rfqs/${rfq.id}`);
}
```

### API Route Handler

```tsx
// app/api/products/search/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { searchProducts } from '@/lib/api/products';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const query = searchParams.get('q');
  const category = searchParams.get('category');
  const page = parseInt(searchParams.get('page') || '1');

  try {
    const results = await searchProducts({ query, category, page });
    return NextResponse.json(results);
  } catch (error) {
    console.error('Search error:', error);
    return NextResponse.json(
      { error: 'Search failed' },
      { status: 500 }
    );
  }
}
```

### Middleware for Auth

```tsx
// middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { verifyToken } from '@/lib/auth';

const publicPaths = ['/', '/login', '/register', '/api/auth'];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public paths
  if (publicPaths.some((path) => pathname.startsWith(path))) {
    return NextResponse.next();
  }

  // Check authentication
  const token = request.cookies.get('token')?.value;

  if (!token) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  try {
    const payload = await verifyToken(token);

    // Add user info to headers for downstream use
    const requestHeaders = new Headers(request.headers);
    requestHeaders.set('x-user-id', payload.sub);
    requestHeaders.set('x-organization-id', payload.orgId);

    return NextResponse.next({
      request: {
        headers: requestHeaders,
      },
    });
  } catch {
    return NextResponse.redirect(new URL('/login', request.url));
  }
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
```

### Next.js Configuration

```js
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverActions: true,
  },

  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'cdn.shipchandlery.com',
      },
    ],
  },

  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        ],
      },
    ];
  },

  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.API_URL}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
```

### Dependencies
- ADR-UI-002: Component Library (shadcn/ui)
- ADR-UI-003: State Management Strategy
- ADR-NF-007: API Design Principles

### Migration Strategy
1. Set up Next.js 14 project with App Router
2. Configure TypeScript and ESLint
3. Set up Tailwind CSS
4. Create base layouts
5. Implement authentication flow
6. Build core pages
7. Add real-time features

---

## Operational Considerations

### Rendering Strategy by Route Type

| Route Category | Rendering Mode | Cache Strategy | Revalidation |
|----------------|---------------|----------------|--------------|
| Marketing pages (`/`, `/about`, `/pricing`) | SSG (Static) | Full page cache | On deploy or 24h |
| Product catalog (`/catalog/*`) | ISR | `revalidate: 3600` (1h) | On-demand via webhook |
| Product detail (`/catalog/[id]`) | ISR | `revalidate: 1800` (30m) | On-demand on update |
| Dashboard (`/(dashboard)/*`) | Dynamic SSR | No cache | Real-time |
| RFQ detail (`/rfqs/[id]`) | Dynamic SSR | No cache | Real-time bidding |
| User profile/settings | Dynamic SSR | No cache | Per-request |
| API routes (`/api/*`) | Edge/Node | Varies | Per-endpoint |

### Route Segment Configuration

```typescript
// Example segment configs for different route types

// app/(marketing)/page.tsx - Static generation
export const dynamic = 'force-static';
export const revalidate = 86400; // 24 hours

// app/(dashboard)/page.tsx - Always dynamic
export const dynamic = 'force-dynamic';
export const fetchCache = 'force-no-store';

// app/catalog/[productId]/page.tsx - ISR with on-demand
export const revalidate = 1800; // 30 minutes base
export async function generateStaticParams() {
  const topProducts = await getTopProducts(1000);
  return topProducts.map(p => ({ productId: p.id }));
}
```

### Caching Policies

| Data Type | Cache Location | TTL | Invalidation Trigger |
|-----------|---------------|-----|---------------------|
| Product catalog | CDN + Server | 1 hour | Catalog sync webhook |
| Product prices | Server only | 5 minutes | Price update event |
| User session | Server memory | 15 minutes | Logout/token refresh |
| Search results | Client (React Query) | 5 minutes | New search |
| RFQ data | No cache | N/A | Always fresh |
| Static assets | CDN | 1 year | Build hash change |

### Server Actions Guidelines

```typescript
// Server Action best practices

// 1. Always validate input with Zod
const schema = z.object({
  rfqId: z.string().uuid(),
  status: z.enum(['DRAFT', 'PUBLISHED', 'CLOSED']),
});

// 2. Include proper error handling
export async function updateRfqStatus(formData: FormData) {
  'use server';

  try {
    const session = await getSession();
    if (!session) throw new Error('Unauthorized');

    const data = schema.parse(Object.fromEntries(formData));

    // Verify ownership/permissions
    const rfq = await getRfq(data.rfqId);
    if (rfq.buyerId !== session.user.organizationId) {
      throw new Error('Forbidden');
    }

    await updateRfq(data.rfqId, { status: data.status });
    revalidatePath(`/rfqs/${data.rfqId}`);

  } catch (error) {
    if (error instanceof z.ZodError) {
      return { error: 'Validation failed', details: error.errors };
    }
    return { error: 'Update failed' };
  }
}

// 3. Use for mutations only, not data fetching
// 4. Keep actions small and focused
// 5. Always revalidate affected paths
```

### Runtime Constraints

| Runtime | Use Case | Constraints |
|---------|----------|-------------|
| Node.js (default) | Dashboard, complex data processing | Full Node.js APIs, 60s timeout |
| Edge | Auth middleware, redirects, simple API | Limited APIs, 30s timeout, no fs |

```typescript
// Middleware uses Edge runtime by default
// middleware.ts
export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};

// For API routes requiring full Node.js
// app/api/reports/route.ts
export const runtime = 'nodejs'; // Explicit Node.js for PDF generation
```

### Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| TTFB (marketing) | < 200ms | Vercel Analytics |
| TTFB (dashboard) | < 500ms | Custom monitoring |
| LCP | < 2.5s | Core Web Vitals |
| FID | < 100ms | Core Web Vitals |
| CLS | < 0.1 | Core Web Vitals |

### Open Questions - Resolved

- **Q:** What is the fallback plan if a key App Router feature changes or is deprecated?
  - **A:** We implement the following mitigation strategy:
    1. **Version pinning**: Lock Next.js to specific minor versions (e.g., `~14.2.0`) and upgrade deliberately
    2. **Abstraction layer**: Wrap Next.js-specific APIs (routing, caching) in thin adapter modules
    3. **Feature flags**: Use feature flags for new App Router features during evaluation period
    4. **Canary testing**: Run canary deployments with Next.js beta versions in staging
    5. **Migration budget**: Allocate 10% of sprint capacity for framework maintenance
    6. **Alternative evaluation**: Annually review alternatives (Remix, Vite SSR) for contingency planning

---

## References
- [Next.js Documentation](https://nextjs.org/docs)
- [React Server Components](https://react.dev/blog/2023/03/22/react-labs-what-we-have-been-working-on-march-2023#react-server-components)
- [App Router Migration Guide](https://nextjs.org/docs/app/building-your-application/upgrading/app-router-migration)
