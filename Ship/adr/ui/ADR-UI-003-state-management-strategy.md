# ADR-UI-003: State Management Strategy

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Frontend

---

## Context

The platform requires a coherent state management strategy for handling server data, client state, and real-time updates.

### Business Context
State management needs:
- Server data caching and synchronization
- Form state management
- UI state (modals, filters, selections)
- Real-time updates (bidding, notifications)
- Offline support for mobile

### Technical Context
- Next.js 14 with React Server Components (ADR-UI-001)
- REST API backend (ADR-NF-007)
- WebSocket for real-time features
- TypeScript for type safety
- Mobile app sharing some logic

### Assumptions
- Server state is majority of application state
- Client-only state is minimal
- React Query handles server state well
- Zustand suitable for client state
- Real-time handled via WebSocket

---

## Decision Drivers

- Developer experience
- Performance (caching, deduplication)
- TypeScript support
- Bundle size
- React Server Components compatibility
- Testing ease

---

## Considered Options

### Option 1: React Query + Zustand
**Description:** React Query for server state, Zustand for client state.

**Pros:**
- Clear separation of concerns
- Excellent caching
- Small bundle size
- Simple Zustand API
- Great TypeScript support

**Cons:**
- Two libraries to learn
- Coordination between them

### Option 2: Redux Toolkit + RTK Query
**Description:** Redux with official toolkit and data fetching.

**Pros:**
- Single solution
- Powerful DevTools
- RTK Query for caching
- Large ecosystem

**Cons:**
- More boilerplate
- Larger bundle
- Overhead for simple cases

### Option 3: React Context + SWR
**Description:** Native Context with SWR for data fetching.

**Pros:**
- No additional dependencies
- SWR is lightweight
- Simple mental model

**Cons:**
- Context performance issues at scale
- Manual optimization needed
- Less powerful than React Query

---

## Decision

**Chosen Option:** React Query (TanStack Query) + Zustand

We will use React Query for server state management and caching, with Zustand for minimal client-side state.

### Rationale
React Query provides excellent caching, deduplication, and background updates. Its declarative approach works well with React Server Components. Zustand offers a minimal, TypeScript-friendly store for UI state without the boilerplate of Redux.

---

## Consequences

### Positive
- Automatic caching and deduplication
- Background data synchronization
- Optimistic updates support
- Minimal client state boilerplate
- Great DevTools for both

### Negative
- Two state systems to understand
- **Mitigation:** Clear guidelines on when to use each
- Potential for over-fetching
- **Mitigation:** Thoughtful query key design

### Risks
- Cache invalidation complexity: Consistent query key patterns
- State synchronization issues: Mutations with proper invalidation
- Memory leaks: Proper cleanup, garbage collection

---

## Implementation Notes

### React Query Configuration

```tsx
// lib/query-client.ts
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 30, // 30 minutes (formerly cacheTime)
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      refetchOnWindowFocus: process.env.NODE_ENV === 'production',
    },
    mutations: {
      retry: 1,
    },
  },
});
```

### Query Provider Setup

```tsx
// components/providers/query-provider.tsx
'use client';

import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { queryClient } from '@/lib/query-client';

export function QueryProvider({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
```

### Query Keys Organization

```tsx
// lib/query-keys.ts
export const queryKeys = {
  // Orders
  orders: {
    all: ['orders'] as const,
    lists: () => [...queryKeys.orders.all, 'list'] as const,
    list: (filters: OrderFilters) => [...queryKeys.orders.lists(), filters] as const,
    details: () => [...queryKeys.orders.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.orders.details(), id] as const,
  },

  // RFQs
  rfqs: {
    all: ['rfqs'] as const,
    lists: () => [...queryKeys.rfqs.all, 'list'] as const,
    list: (filters: RfqFilters) => [...queryKeys.rfqs.lists(), filters] as const,
    details: () => [...queryKeys.rfqs.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.rfqs.details(), id] as const,
    quotes: (rfqId: string) => [...queryKeys.rfqs.detail(rfqId), 'quotes'] as const,
  },

  // Products
  products: {
    all: ['products'] as const,
    search: (query: string) => [...queryKeys.products.all, 'search', query] as const,
    detail: (id: string) => [...queryKeys.products.all, id] as const,
    categories: () => [...queryKeys.products.all, 'categories'] as const,
  },

  // User
  user: {
    current: ['user', 'current'] as const,
    organization: ['user', 'organization'] as const,
  },
};
```

### Custom Query Hooks

```tsx
// hooks/queries/use-orders.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ordersApi } from '@/lib/api/orders';
import { queryKeys } from '@/lib/query-keys';

interface UseOrdersOptions {
  status?: OrderStatus;
  page?: number;
  search?: string;
}

export function useOrders(options: UseOrdersOptions = {}) {
  return useQuery({
    queryKey: queryKeys.orders.list(options),
    queryFn: () => ordersApi.getOrders(options),
  });
}

export function useOrder(id: string) {
  return useQuery({
    queryKey: queryKeys.orders.detail(id),
    queryFn: () => ordersApi.getOrder(id),
    enabled: !!id,
  });
}

export function useCreateOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ordersApi.createOrder,
    onSuccess: (newOrder) => {
      // Invalidate order lists
      queryClient.invalidateQueries({ queryKey: queryKeys.orders.lists() });

      // Add new order to cache
      queryClient.setQueryData(
        queryKeys.orders.detail(newOrder.id),
        newOrder
      );
    },
  });
}

export function useUpdateOrderStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: OrderStatus }) =>
      ordersApi.updateOrderStatus(id, status),

    // Optimistic update
    onMutate: async ({ id, status }) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.orders.detail(id) });

      const previousOrder = queryClient.getQueryData<Order>(
        queryKeys.orders.detail(id)
      );

      queryClient.setQueryData(queryKeys.orders.detail(id), (old: Order) => ({
        ...old,
        status,
      }));

      return { previousOrder };
    },

    onError: (err, { id }, context) => {
      // Rollback on error
      if (context?.previousOrder) {
        queryClient.setQueryData(
          queryKeys.orders.detail(id),
          context.previousOrder
        );
      }
    },

    onSettled: (data, error, { id }) => {
      // Refetch to ensure consistency
      queryClient.invalidateQueries({ queryKey: queryKeys.orders.detail(id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.orders.lists() });
    },
  });
}
```

### Zustand Store for UI State

```tsx
// stores/ui-store.ts
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

interface UIState {
  // Sidebar state
  sidebarOpen: boolean;
  toggleSidebar: () => void;

  // Filters
  orderFilters: OrderFilters;
  setOrderFilters: (filters: Partial<OrderFilters>) => void;
  resetOrderFilters: () => void;

  // Modals
  activeModal: string | null;
  modalData: any;
  openModal: (modal: string, data?: any) => void;
  closeModal: () => void;

  // Selections
  selectedOrders: string[];
  toggleOrderSelection: (id: string) => void;
  selectAllOrders: (ids: string[]) => void;
  clearOrderSelection: () => void;
}

const defaultFilters: OrderFilters = {
  status: undefined,
  dateRange: undefined,
  search: '',
};

export const useUIStore = create<UIState>()(
  devtools(
    persist(
      (set) => ({
        // Sidebar
        sidebarOpen: true,
        toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

        // Filters
        orderFilters: defaultFilters,
        setOrderFilters: (filters) =>
          set((state) => ({
            orderFilters: { ...state.orderFilters, ...filters },
          })),
        resetOrderFilters: () => set({ orderFilters: defaultFilters }),

        // Modals
        activeModal: null,
        modalData: null,
        openModal: (modal, data) => set({ activeModal: modal, modalData: data }),
        closeModal: () => set({ activeModal: null, modalData: null }),

        // Selections
        selectedOrders: [],
        toggleOrderSelection: (id) =>
          set((state) => ({
            selectedOrders: state.selectedOrders.includes(id)
              ? state.selectedOrders.filter((i) => i !== id)
              : [...state.selectedOrders, id],
          })),
        selectAllOrders: (ids) => set({ selectedOrders: ids }),
        clearOrderSelection: () => set({ selectedOrders: [] }),
      }),
      {
        name: 'ui-storage',
        partialize: (state) => ({
          sidebarOpen: state.sidebarOpen,
        }),
      }
    ),
    { name: 'UIStore' }
  )
);
```

### Real-Time Store

```tsx
// stores/realtime-store.ts
import { create } from 'zustand';
import { io, Socket } from 'socket.io-client';
import { queryClient } from '@/lib/query-client';
import { queryKeys } from '@/lib/query-keys';

interface RealtimeState {
  socket: Socket | null;
  connected: boolean;
  notifications: Notification[];
  connect: (token: string) => void;
  disconnect: () => void;
  markNotificationRead: (id: string) => void;
}

export const useRealtimeStore = create<RealtimeState>((set, get) => ({
  socket: null,
  connected: false,
  notifications: [],

  connect: (token) => {
    const socket = io(process.env.NEXT_PUBLIC_WS_URL!, {
      auth: { token },
      transports: ['websocket'],
    });

    socket.on('connect', () => {
      set({ connected: true });
    });

    socket.on('disconnect', () => {
      set({ connected: false });
    });

    // Handle real-time events
    socket.on('notification', (notification: Notification) => {
      set((state) => ({
        notifications: [notification, ...state.notifications],
      }));
    });

    socket.on('order:updated', (order: Order) => {
      // Update React Query cache
      queryClient.setQueryData(queryKeys.orders.detail(order.id), order);
      queryClient.invalidateQueries({ queryKey: queryKeys.orders.lists() });
    });

    socket.on('rfq:quote_received', ({ rfqId, quote }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.rfqs.quotes(rfqId) });
    });

    socket.on('rfq:status_changed', ({ rfqId, status }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.rfqs.detail(rfqId) });
    });

    set({ socket });
  },

  disconnect: () => {
    const { socket } = get();
    if (socket) {
      socket.disconnect();
      set({ socket: null, connected: false });
    }
  },

  markNotificationRead: (id) => {
    set((state) => ({
      notifications: state.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n
      ),
    }));
  },
}));
```

### Infinite Query for Lists

```tsx
// hooks/queries/use-products-search.ts
import { useInfiniteQuery } from '@tanstack/react-query';
import { productsApi } from '@/lib/api/products';
import { queryKeys } from '@/lib/query-keys';

export function useProductsSearch(query: string) {
  return useInfiniteQuery({
    queryKey: queryKeys.products.search(query),
    queryFn: ({ pageParam = 1 }) => productsApi.search({ query, page: pageParam }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) =>
      lastPage.pagination.page < lastPage.pagination.totalPages
        ? lastPage.pagination.page + 1
        : undefined,
    enabled: query.length > 0,
  });
}

// Usage
function ProductSearchResults({ query }: { query: string }) {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useProductsSearch(query);

  const products = data?.pages.flatMap((page) => page.data) ?? [];

  return (
    <div>
      {products.map((product) => (
        <ProductCard key={product.id} product={product} />
      ))}

      {hasNextPage && (
        <Button
          onClick={() => fetchNextPage()}
          disabled={isFetchingNextPage}
        >
          {isFetchingNextPage ? 'Loading...' : 'Load More'}
        </Button>
      )}
    </div>
  );
}
```

### Prefetching for Navigation

```tsx
// components/orders/order-row.tsx
'use client';

import { useQueryClient } from '@tanstack/react-query';
import { ordersApi } from '@/lib/api/orders';
import { queryKeys } from '@/lib/query-keys';

export function OrderRow({ order }: { order: Order }) {
  const queryClient = useQueryClient();

  const handleMouseEnter = () => {
    // Prefetch order details on hover
    queryClient.prefetchQuery({
      queryKey: queryKeys.orders.detail(order.id),
      queryFn: () => ordersApi.getOrder(order.id),
      staleTime: 1000 * 60, // 1 minute
    });
  };

  return (
    <Link
      href={`/orders/${order.id}`}
      onMouseEnter={handleMouseEnter}
    >
      {/* Order row content */}
    </Link>
  );
}
```

### Dependencies
- ADR-UI-001: Next.js 14+ App Router
- ADR-NF-007: API Design Principles

### Migration Strategy
1. Install React Query and Zustand
2. Set up QueryClientProvider
3. Create query key organization
4. Build API client functions
5. Create custom query hooks
6. Set up Zustand stores
7. Add real-time integration

---

## Operational Considerations

### Server State vs Client State Boundaries

#### State Classification Matrix

| Data Category | State Type | Manager | Cache TTL | Example |
|--------------|-----------|---------|-----------|---------|
| API responses | Server | React Query | Varies | Orders, RFQs, Products |
| Form values | Client | React Hook Form | None | RFQ creation form |
| UI preferences | Client (persisted) | Zustand | Permanent | Sidebar state, theme |
| User session | Server | React Query | 15 min | Current user, org |
| Real-time data | Server (WebSocket) | Zustand + Query | None | Bid updates, notifications |
| Filter/sort state | Client (URL) | URL params | None | Catalog filters |
| Selection state | Client | Zustand | None | Selected items for bulk action |
| Modal/dialog state | Client | Zustand | None | Which modal is open |

#### Decision Tree for State Placement

```
Is the data from an API?
├── Yes → React Query (server state)
│   ├── Is it real-time? → WebSocket + Query invalidation
│   └── Is it user-specific? → Short staleTime (5min)
│
└── No → Is it UI state?
    ├── Yes → Does it need to persist across sessions?
    │   ├── Yes → Zustand with persist middleware
    │   └── No → Does it affect URL/navigation?
    │       ├── Yes → URL search params
    │       └── No → Zustand (non-persisted)
    │
    └── No → Is it form data?
        └── Yes → React Hook Form (local component state)
```

### Caching Policies by Data Type

| Data Type | staleTime | gcTime | refetchOnWindowFocus | Background Updates |
|-----------|-----------|--------|---------------------|-------------------|
| User profile | 5 min | 30 min | Yes | No |
| Product catalog | 1 hour | 24 hours | No | Yes (ISR) |
| Order list | 2 min | 15 min | Yes | Yes |
| RFQ detail | 30 sec | 5 min | Yes | Yes (real-time) |
| Quotes/Bids | 0 (always fresh) | 5 min | Yes | WebSocket |
| Static lookups (categories) | 24 hours | 7 days | No | No |
| Search results | 5 min | 30 min | No | No |

#### React Query Configuration

```typescript
// lib/query-client.ts
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,      // 5 minutes default
      gcTime: 1000 * 60 * 30,        // 30 minutes garbage collection
      retry: 3,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30000),
      refetchOnWindowFocus: process.env.NODE_ENV === 'production',
      refetchOnReconnect: true,
    },
    mutations: {
      retry: 1,
      onError: (error) => {
        // Global error handling
        if (error.response?.status === 401) {
          // Trigger re-auth
        }
      },
    },
  },
});

// Override per-query as needed
export const queryKeys = {
  rfqs: {
    detail: (id: string) => ({
      queryKey: ['rfqs', id],
      staleTime: 1000 * 30,  // 30 seconds for active bidding
    }),
  },
};
```

### Persistence & Offline Sync

#### Web Persistence Strategy

| Data | Storage | Sync Strategy |
|------|---------|--------------|
| Auth tokens | Secure HTTP-only cookies | Server-managed |
| UI preferences | localStorage via Zustand | No sync needed |
| Draft RFQs | IndexedDB | Sync on submit |
| Cached queries | React Query (memory) | Refetch on reconnect |
| Offline queue | IndexedDB | Process on reconnect |

#### Mobile Persistence Strategy

| Data | Storage | Sync Strategy |
|------|---------|--------------|
| Auth tokens | expo-secure-store | Server-managed |
| User preferences | AsyncStorage via Zustand | No sync needed |
| Product catalog | SQLite | Background sync daily |
| Pending orders | SQLite | Sync queue on connect |
| Draft forms | SQLite | Sync on submit |

### Conflict Resolution Rules

#### Resolution Strategy by Entity

| Entity | Conflict Strategy | Rationale |
|--------|------------------|-----------|
| Orders | Server wins | Financial integrity |
| RFQ status | Server wins | Multi-party coordination |
| User preferences | Client wins (merge) | Local personalization |
| Draft RFQs | Last-write-wins + merge | User control |
| Product data | Server wins | Catalog is source of truth |
| Inventory updates | Server wins + notify | Real-time accuracy |

#### Conflict Detection & Handling

```typescript
// Optimistic update with conflict detection
export function useUpdateOrderStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, status, expectedVersion }) => {
      const response = await api.patch(`/orders/${id}/status`, {
        status,
        version: expectedVersion, // Optimistic locking
      });
      return response.data;
    },

    onMutate: async ({ id, status }) => {
      await queryClient.cancelQueries({ queryKey: ['orders', id] });
      const previous = queryClient.getQueryData(['orders', id]);

      // Optimistic update
      queryClient.setQueryData(['orders', id], (old) => ({
        ...old,
        status,
        _optimistic: true,
      }));

      return { previous };
    },

    onError: (error, { id }, context) => {
      // Rollback on error
      queryClient.setQueryData(['orders', id], context.previous);

      if (error.response?.status === 409) {
        // Conflict detected - show user the server version
        toast.error('Order was modified by another user. Please refresh.');
        queryClient.invalidateQueries({ queryKey: ['orders', id] });
      }
    },

    onSettled: (data, error, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['orders', id] });
    },
  });
}
```

### Cross-Tab & Session Sync

#### Implementation Approach

```typescript
// lib/cross-tab-sync.ts
import { BroadcastChannel } from 'broadcast-channel';

const channel = new BroadcastChannel('ship-chandlery-sync');

// Zustand middleware for cross-tab sync
export const crossTabSync = (config) => (set, get, api) =>
  config(
    (...args) => {
      set(...args);
      // Broadcast state changes to other tabs
      channel.postMessage({
        type: 'STATE_CHANGE',
        state: get(),
        timestamp: Date.now(),
      });
    },
    get,
    api
  );

// Listen for changes from other tabs
channel.onmessage = (message) => {
  if (message.type === 'STATE_CHANGE') {
    // Update local state from other tab
    useUIStore.setState(message.state);
  }

  if (message.type === 'LOGOUT') {
    // Sync logout across tabs
    useAuthStore.getState().logout();
  }

  if (message.type === 'CACHE_INVALIDATE') {
    // Invalidate React Query cache
    queryClient.invalidateQueries({ queryKey: message.queryKey });
  }
};

// Usage in store
export const useUIStore = create(
  crossTabSync(
    persist(
      (set) => ({
        sidebarOpen: true,
        toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      }),
      { name: 'ui-storage' }
    )
  )
);
```

#### Sync Events

| Event | Broadcast | Action |
|-------|-----------|--------|
| User logout | All tabs | Force logout |
| Order status change | All tabs | Invalidate orders query |
| New notification | All tabs | Update notification count |
| Theme change | All tabs | Update UI theme |
| Cart update | All tabs | Sync cart state |

### Open Questions - Resolved

- **Q:** What is the approach for cross-tab or session sync?
  - **A:** We implement cross-tab synchronization using the BroadcastChannel API:
    1. **State sync**: UI preferences (sidebar, theme) sync via Zustand middleware that broadcasts changes
    2. **Auth sync**: Logout events broadcast to all tabs for immediate session termination
    3. **Cache sync**: React Query cache invalidation broadcasts for real-time data consistency
    4. **Conflict handling**: Last-write-wins for preferences; server-wins for business data
    5. **Offline recovery**: IndexedDB queues actions; processes on reconnect with conflict detection
    6. **Implementation**: Custom Zustand middleware wraps state changes with BroadcastChannel postMessage

---

## AI Conversation State Management

The PortiQ AI-native UX introduces new state domains for managing conversation threads, AI context, voice input, and proactive suggestions. This section extends the existing React Query + Zustand architecture to support AI-powered interactions.

### AI State Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI State Domains                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Conversation   │  │    Context      │  │   Voice Input   │ │
│  │     State       │  │     State       │  │     State       │ │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤ │
│  │ • messages[]    │  │ • activeVessel  │  │ • isListening   │ │
│  │ • isStreaming   │  │ • currentRFQ    │  │ • transcript    │ │
│  │ • pendingInput  │  │ • comparison    │  │ • confidence    │ │
│  │ • threadId      │  │ • panelType     │  │ • error         │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Pending Actions │  │   Suggestions   │  │   AI Metadata   │ │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤ │
│  │ • actions[]     │  │ • proactive[]   │  │ • modelVersion  │ │
│  │ • confirmQueue  │  │ • dismissed[]   │  │ • latency       │ │
│  │ • timeouts      │  │ • preferences   │  │ • tokenUsage    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### AI State Types

```typescript
// types/ai-state.ts

// Message types in conversation
interface AIMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  metadata?: {
    confidence?: number;
    sources?: string[];
    actions?: AIAction[];
    isStreaming?: boolean;
  };
}

// Actions the AI can propose
interface AIAction {
  id: string;
  type: 'confirm' | 'adjust' | 'question' | 'navigate' | 'execute';
  label: string;
  description?: string;
  payload: Record<string, unknown>;
  confidence: number;
  expiresAt?: Date;
  status: 'pending' | 'accepted' | 'rejected' | 'expired';
}

// Context panel state
interface ContextPanelState {
  type: 'vessel' | 'rfq' | 'comparison' | 'order' | null;
  data: VesselContext | RFQContext | ComparisonContext | OrderContext | null;
  collapsed: boolean;
}

interface VesselContext {
  id: string;
  name: string;
  imo: string;
  type: string;
  flag: string;
  lastPort?: string;
  nextPort?: string;
  eta?: Date;
}

interface RFQContext {
  id: string;
  status: string;
  items: Array<{
    product: string;
    quantity: number;
    unit: string;
  }>;
  deliveryPort: string;
  requiredBy: Date;
  quotesReceived: number;
}

interface ComparisonContext {
  rfqId: string;
  quotes: Array<{
    supplierId: string;
    supplierName: string;
    totalPrice: number;
    tco: number;
    deliveryDate: Date;
    matchScore: number;
  }>;
  recommendation?: {
    supplierId: string;
    reasoning: string;
    confidence: number;
  };
}

// Voice input state
interface VoiceInputState {
  isListening: boolean;
  isProcessing: boolean;
  transcript: string;
  interimTranscript: string;
  confidence: number;
  error: Error | null;
  language: string;
}

// Proactive suggestions
interface ProactiveSuggestion {
  id: string;
  type: 'restock' | 'anomaly' | 'opportunity' | 'reminder';
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  action?: AIAction;
  createdAt: Date;
  expiresAt?: Date;
  dismissed: boolean;
}

// Complete AI state interface
interface AIState {
  // Conversation
  conversation: {
    messages: AIMessage[];
    threadId: string | null;
    isStreaming: boolean;
    streamingContent: string;
    error: Error | null;
  };

  // Context
  context: ContextPanelState;

  // Pending actions
  pendingActions: AIAction[];
  confirmationQueue: AIAction[];

  // Voice
  voiceInput: VoiceInputState;

  // Suggestions
  suggestions: ProactiveSuggestion[];
  dismissedSuggestionIds: string[];

  // Metadata
  metadata: {
    lastInteraction: Date | null;
    sessionTokens: number;
    averageLatency: number;
  };
}
```

### PortiQ Conversation Store

```typescript
// stores/portiq-store.ts
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { queryClient } from '@/lib/query-client';
import { portiqApi } from '@/lib/api/portiq';

interface PortiQStoreState extends AIState {
  // Actions - Conversation
  sendMessage: (content: string) => Promise<void>;
  appendStreamChunk: (chunk: string) => void;
  finalizeStream: (message: AIMessage) => void;
  clearConversation: () => void;

  // Actions - Context
  setContext: (context: ContextPanelState) => void;
  clearContext: () => void;
  toggleContextCollapse: () => void;

  // Actions - Pending Actions
  addPendingAction: (action: AIAction) => void;
  confirmAction: (actionId: string) => Promise<void>;
  rejectAction: (actionId: string) => void;
  expireActions: () => void;

  // Actions - Voice
  setVoiceState: (state: Partial<VoiceInputState>) => void;

  // Actions - Suggestions
  addSuggestion: (suggestion: ProactiveSuggestion) => void;
  dismissSuggestion: (id: string) => void;
  actOnSuggestion: (id: string) => Promise<void>;
}

export const usePortiQStore = create<PortiQStoreState>()(
  devtools(
    persist(
      immer((set, get) => ({
        // Initial state
        conversation: {
          messages: [],
          threadId: null,
          isStreaming: false,
          streamingContent: '',
          error: null,
        },
        context: {
          type: null,
          data: null,
          collapsed: false,
        },
        pendingActions: [],
        confirmationQueue: [],
        voiceInput: {
          isListening: false,
          isProcessing: false,
          transcript: '',
          interimTranscript: '',
          confidence: 0,
          error: null,
          language: 'en-US',
        },
        suggestions: [],
        dismissedSuggestionIds: [],
        metadata: {
          lastInteraction: null,
          sessionTokens: 0,
          averageLatency: 0,
        },

        // Conversation actions
        sendMessage: async (content: string) => {
          const startTime = Date.now();

          // Add user message
          const userMessage: AIMessage = {
            id: crypto.randomUUID(),
            role: 'user',
            content,
            timestamp: new Date(),
          };

          set((state) => {
            state.conversation.messages.push(userMessage);
            state.conversation.isStreaming = true;
            state.conversation.error = null;
          });

          try {
            // Stream response from PortiQ API
            const stream = await portiqApi.chat({
              message: content,
              threadId: get().conversation.threadId,
              context: get().context.data,
            });

            let fullContent = '';

            for await (const chunk of stream) {
              fullContent += chunk.content;
              set((state) => {
                state.conversation.streamingContent = fullContent;
              });

              // Handle any actions in the chunk
              if (chunk.actions) {
                chunk.actions.forEach((action: AIAction) => {
                  get().addPendingAction(action);
                });
              }

              // Handle context updates
              if (chunk.contextUpdate) {
                set((state) => {
                  state.context = {
                    ...state.context,
                    ...chunk.contextUpdate,
                  };
                });
              }
            }

            // Finalize the message
            const assistantMessage: AIMessage = {
              id: crypto.randomUUID(),
              role: 'assistant',
              content: fullContent,
              timestamp: new Date(),
              metadata: {
                confidence: stream.confidence,
                sources: stream.sources,
              },
            };

            set((state) => {
              state.conversation.messages.push(assistantMessage);
              state.conversation.isStreaming = false;
              state.conversation.streamingContent = '';
              state.conversation.threadId = stream.threadId;
              state.metadata.lastInteraction = new Date();
              state.metadata.sessionTokens += stream.tokenUsage ?? 0;

              // Update average latency
              const latency = Date.now() - startTime;
              const prevAvg = state.metadata.averageLatency;
              const msgCount = state.conversation.messages.length;
              state.metadata.averageLatency =
                (prevAvg * (msgCount - 1) + latency) / msgCount;
            });

          } catch (error) {
            set((state) => {
              state.conversation.isStreaming = false;
              state.conversation.error = error as Error;
            });
            throw error;
          }
        },

        appendStreamChunk: (chunk: string) => {
          set((state) => {
            state.conversation.streamingContent += chunk;
          });
        },

        finalizeStream: (message: AIMessage) => {
          set((state) => {
            state.conversation.messages.push(message);
            state.conversation.isStreaming = false;
            state.conversation.streamingContent = '';
          });
        },

        clearConversation: () => {
          set((state) => {
            state.conversation.messages = [];
            state.conversation.threadId = null;
            state.conversation.streamingContent = '';
            state.conversation.error = null;
            state.pendingActions = [];
            state.confirmationQueue = [];
          });
        },

        // Context actions
        setContext: (context: ContextPanelState) => {
          set((state) => {
            state.context = context;
          });
        },

        clearContext: () => {
          set((state) => {
            state.context = { type: null, data: null, collapsed: false };
          });
        },

        toggleContextCollapse: () => {
          set((state) => {
            state.context.collapsed = !state.context.collapsed;
          });
        },

        // Pending action handlers
        addPendingAction: (action: AIAction) => {
          set((state) => {
            // Check if this is a high-confidence action that needs confirmation
            if (action.type === 'confirm' && action.confidence >= 0.9) {
              state.confirmationQueue.push(action);
            } else {
              state.pendingActions.push(action);
            }
          });
        },

        confirmAction: async (actionId: string) => {
          const action = get().pendingActions.find((a) => a.id === actionId)
            || get().confirmationQueue.find((a) => a.id === actionId);

          if (!action) return;

          try {
            // Execute the action via API
            await portiqApi.executeAction(action);

            // Update action status
            set((state) => {
              const pending = state.pendingActions.find((a) => a.id === actionId);
              const queued = state.confirmationQueue.find((a) => a.id === actionId);

              if (pending) pending.status = 'accepted';
              if (queued) queued.status = 'accepted';
            });

            // Invalidate relevant queries based on action type
            if (action.type === 'execute' && action.payload.entityType) {
              queryClient.invalidateQueries({
                queryKey: [action.payload.entityType],
              });
            }

          } catch (error) {
            set((state) => {
              const pending = state.pendingActions.find((a) => a.id === actionId);
              const queued = state.confirmationQueue.find((a) => a.id === actionId);

              if (pending) pending.status = 'rejected';
              if (queued) queued.status = 'rejected';
            });
            throw error;
          }
        },

        rejectAction: (actionId: string) => {
          set((state) => {
            const pending = state.pendingActions.find((a) => a.id === actionId);
            const queued = state.confirmationQueue.find((a) => a.id === actionId);

            if (pending) pending.status = 'rejected';
            if (queued) queued.status = 'rejected';
          });
        },

        expireActions: () => {
          const now = new Date();
          set((state) => {
            state.pendingActions
              .filter((a) => a.expiresAt && a.expiresAt < now && a.status === 'pending')
              .forEach((a) => { a.status = 'expired'; });

            state.confirmationQueue
              .filter((a) => a.expiresAt && a.expiresAt < now && a.status === 'pending')
              .forEach((a) => { a.status = 'expired'; });
          });
        },

        // Voice actions
        setVoiceState: (voiceState: Partial<VoiceInputState>) => {
          set((state) => {
            Object.assign(state.voiceInput, voiceState);
          });
        },

        // Suggestion actions
        addSuggestion: (suggestion: ProactiveSuggestion) => {
          set((state) => {
            // Don't add if already dismissed
            if (state.dismissedSuggestionIds.includes(suggestion.id)) {
              return;
            }
            // Add to front, limit to 10 suggestions
            state.suggestions = [suggestion, ...state.suggestions].slice(0, 10);
          });
        },

        dismissSuggestion: (id: string) => {
          set((state) => {
            state.suggestions = state.suggestions.filter((s) => s.id !== id);
            state.dismissedSuggestionIds.push(id);
          });
        },

        actOnSuggestion: async (id: string) => {
          const suggestion = get().suggestions.find((s) => s.id === id);
          if (!suggestion?.action) return;

          await get().confirmAction(suggestion.action.id);
          get().dismissSuggestion(id);
        },
      })),
      {
        name: 'portiq-storage',
        partialize: (state) => ({
          // Only persist certain parts of state
          conversation: {
            threadId: state.conversation.threadId,
            // Don't persist full message history - reload from server
          },
          dismissedSuggestionIds: state.dismissedSuggestionIds,
          voiceInput: {
            language: state.voiceInput.language,
          },
        }),
      }
    ),
    { name: 'PortiQStore' }
  )
);
```

### AI Query Hooks

```typescript
// hooks/queries/use-portiq.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { portiqApi } from '@/lib/api/portiq';
import { usePortiQStore } from '@/stores/portiq-store';

// Query keys for AI-related data
export const aiQueryKeys = {
  suggestions: ['ai', 'suggestions'] as const,
  conversationHistory: (threadId: string) => ['ai', 'conversation', threadId] as const,
  vesselContext: (vesselId: string) => ['ai', 'context', 'vessel', vesselId] as const,
  rfqContext: (rfqId: string) => ['ai', 'context', 'rfq', rfqId] as const,
};

// Fetch proactive suggestions
export function useProactiveSuggestions() {
  const addSuggestion = usePortiQStore((state) => state.addSuggestion);

  return useQuery({
    queryKey: aiQueryKeys.suggestions,
    queryFn: async () => {
      const suggestions = await portiqApi.getProactiveSuggestions();
      // Add each suggestion to the store
      suggestions.forEach(addSuggestion);
      return suggestions;
    },
    refetchInterval: 1000 * 60 * 5, // Refresh every 5 minutes
    staleTime: 1000 * 60 * 2,
  });
}

// Load conversation history when resuming a thread
export function useConversationHistory(threadId: string | null) {
  const { conversation } = usePortiQStore();

  return useQuery({
    queryKey: aiQueryKeys.conversationHistory(threadId!),
    queryFn: () => portiqApi.getConversationHistory(threadId!),
    enabled: !!threadId && conversation.messages.length === 0,
    staleTime: Infinity, // Don't refetch once loaded
  });
}

// Mutation for executing AI actions
export function useExecuteAIAction() {
  const queryClient = useQueryClient();
  const { confirmAction } = usePortiQStore();

  return useMutation({
    mutationFn: confirmAction,
    onSuccess: (_, actionId) => {
      // The store handles cache invalidation based on action type
    },
  });
}

// Hook to load context data
export function useAIContext(type: 'vessel' | 'rfq', id: string) {
  const setContext = usePortiQStore((state) => state.setContext);

  const query = useQuery({
    queryKey: type === 'vessel'
      ? aiQueryKeys.vesselContext(id)
      : aiQueryKeys.rfqContext(id),
    queryFn: () => type === 'vessel'
      ? portiqApi.getVesselContext(id)
      : portiqApi.getRFQContext(id),
    enabled: !!id,
  });

  // Update store when data loads
  useEffect(() => {
    if (query.data) {
      setContext({
        type,
        data: query.data,
        collapsed: false,
      });
    }
  }, [query.data, type, setContext]);

  return query;
}
```

### WebSocket Integration for Streaming

```typescript
// lib/portiq-socket.ts
import { usePortiQStore } from '@/stores/portiq-store';
import { queryClient } from '@/lib/query-client';

class PortiQSocket {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  connect(token: string) {
    this.ws = new WebSocket(`${process.env.NEXT_PUBLIC_WS_URL}/portiq`);

    this.ws.onopen = () => {
      this.ws?.send(JSON.stringify({ type: 'auth', token }));
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.ws.onclose = () => {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        setTimeout(() => {
          this.reconnectAttempts++;
          this.connect(token);
        }, Math.pow(2, this.reconnectAttempts) * 1000);
      }
    };
  }

  private handleMessage(message: PortiQWSMessage) {
    const store = usePortiQStore.getState();

    switch (message.type) {
      case 'stream_chunk':
        store.appendStreamChunk(message.content);
        break;

      case 'stream_complete':
        store.finalizeStream(message.message);
        break;

      case 'proactive_suggestion':
        store.addSuggestion(message.suggestion);
        break;

      case 'context_update':
        store.setContext(message.context);
        break;

      case 'action_required':
        store.addPendingAction(message.action);
        break;

      case 'entity_update':
        // Invalidate relevant React Query cache
        queryClient.invalidateQueries({
          queryKey: [message.entityType, message.entityId],
        });
        break;
    }
  }

  send(message: object) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  disconnect() {
    this.ws?.close();
    this.ws = null;
  }
}

export const portiqSocket = new PortiQSocket();
```

### State Persistence for Offline Support

```typescript
// lib/ai-persistence.ts
import { openDB, IDBPDatabase } from 'idb';
import { AIMessage, ProactiveSuggestion } from '@/types/ai-state';

interface AIDatabase {
  conversations: {
    key: string;
    value: {
      threadId: string;
      messages: AIMessage[];
      updatedAt: Date;
    };
  };
  pendingActions: {
    key: string;
    value: AIAction;
    indexes: { byStatus: string };
  };
  offlineQueue: {
    key: string;
    value: {
      id: string;
      type: 'message' | 'action';
      payload: unknown;
      createdAt: Date;
    };
  };
}

let db: IDBPDatabase<AIDatabase>;

export async function initAIDatabase() {
  db = await openDB<AIDatabase>('portiq-ai', 1, {
    upgrade(database) {
      // Conversations store
      database.createObjectStore('conversations', { keyPath: 'threadId' });

      // Pending actions store
      const actionsStore = database.createObjectStore('pendingActions', { keyPath: 'id' });
      actionsStore.createIndex('byStatus', 'status');

      // Offline queue for sync
      database.createObjectStore('offlineQueue', { keyPath: 'id' });
    },
  });
}

export async function saveConversation(threadId: string, messages: AIMessage[]) {
  await db.put('conversations', {
    threadId,
    messages,
    updatedAt: new Date(),
  });
}

export async function loadConversation(threadId: string) {
  return db.get('conversations', threadId);
}

export async function queueOfflineMessage(content: string) {
  await db.add('offlineQueue', {
    id: crypto.randomUUID(),
    type: 'message',
    payload: { content },
    createdAt: new Date(),
  });
}

export async function processOfflineQueue() {
  const items = await db.getAll('offlineQueue');

  for (const item of items) {
    try {
      if (item.type === 'message') {
        await usePortiQStore.getState().sendMessage(item.payload.content as string);
      }
      await db.delete('offlineQueue', item.id);
    } catch (error) {
      console.error('Failed to process offline item:', error);
    }
  }
}
```

### State Flow Diagram

```
User Input (Text/Voice)
         │
         ▼
┌─────────────────┐
│  PortiQ Store   │──────────────────────────────┐
│  sendMessage()  │                              │
└────────┬────────┘                              │
         │                                       │
         ▼                                       ▼
┌─────────────────┐                    ┌─────────────────┐
│  Add User Msg   │                    │  Set Streaming  │
│  to messages[]  │                    │  = true         │
└────────┬────────┘                    └─────────────────┘
         │
         ▼
┌─────────────────┐
│  PortiQ API     │◄──── WebSocket Stream
│  chat()         │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌───────────┐
│Chunks │ │ Actions   │
│append │ │ add to    │
│stream │ │ pending   │
└───┬───┘ └─────┬─────┘
    │           │
    ▼           ▼
┌─────────────────────┐
│  Finalize Message   │
│  + Context Update   │
│  + Query Invalidate │
└─────────────────────┘
```

---

## References
- [TanStack Query Documentation](https://tanstack.com/query/latest)
- [Zustand Documentation](https://github.com/pmndrs/zustand)
- [React Query Devtools](https://tanstack.com/query/latest/docs/react/devtools)
- [ADR-UI-013: PortiQ Buyer Experience](./ADR-UI-013-portiq-buyer-experience.md)
- [ADR-UI-015: Command Bar & Voice Input](./ADR-UI-015-command-bar-voice-input.md)
- [ADR-UI-016: Proactive Intelligence](./ADR-UI-016-proactive-intelligence.md)
