# ADR-UI-007: Offline-First Mobile

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Frontend

---

## Context

The mobile app must function in environments with limited or no internet connectivity, common in maritime operations.

### Business Context
Offline requirements:
- Ships at sea have limited connectivity
- Port areas may have unreliable networks
- Procurement tasks need to continue offline
- Data must sync when connectivity returns
- Users expect app to work regardless of network

### Technical Context
- React Native with Expo (ADR-UI-006)
- REST API backend (ADR-NF-007)
- Local data storage needed
- Sync conflict resolution required
- Background sync capability

### Assumptions
- SQLite suitable for local storage
- Last-write-wins acceptable for most conflicts
- Critical operations need special handling
- Users will have connectivity periodically

---

## Decision Drivers

- Offline functionality
- Data consistency
- Sync reliability
- User experience
- Battery efficiency
- Storage efficiency

---

## Considered Options

### Option 1: SQLite with Custom Sync
**Description:** Local SQLite database with custom sync logic.

**Pros:**
- Full control over sync
- Efficient querying
- Mature SQLite support
- Works well with React Query

**Cons:**
- Custom sync implementation
- Conflict resolution complexity
- More development effort

### Option 2: WatermelonDB
**Description:** High-performance SQLite wrapper for React Native.

**Pros:**
- Lazy loading
- Sync primitives built-in
- Good performance
- Observable queries

**Cons:**
- Learning curve
- Schema migrations complexity
- Opinionated patterns

### Option 3: Realm
**Description:** Mobile-first database with sync.

**Pros:**
- Built-in sync
- Real-time capabilities
- Good performance

**Cons:**
- MongoDB dependency
- Vendor lock-in
- Complex setup

---

## Decision

**Chosen Option:** SQLite with Custom Sync (expo-sqlite + React Query)

We will use expo-sqlite for local storage with a custom sync layer that integrates with React Query for caching and state management.

### Rationale
SQLite provides reliable, well-understood local storage. Custom sync logic gives us control over conflict resolution specific to our business rules. Integration with React Query provides seamless online/offline state management. Expo's SQLite support is mature and well-maintained.

---

## Consequences

### Positive
- Works completely offline
- Full control over sync logic
- Efficient local queries
- Familiar React Query patterns

### Negative
- Custom sync implementation
- **Mitigation:** Well-defined sync patterns, thorough testing
- Conflict resolution complexity
- **Mitigation:** Clear business rules for conflicts

### Risks
- Data loss: Robust error handling, sync status visibility
- Sync conflicts: Clear conflict resolution rules
- Storage limits: Data cleanup, selective sync

---

## Implementation Notes

### Offline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Offline-First Architecture                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │                      React Components                       │     │
│  │                                                             │     │
│  │   useOrders()    useProducts()    useCreateOrder()         │     │
│  │                                                             │     │
│  └───────────────────────────┬─────────────────────────────────┘     │
│                              │                                        │
│                              ▼                                        │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │                      React Query                            │     │
│  │                                                             │     │
│  │   - Query caching                                           │     │
│  │   - Mutation queue                                          │     │
│  │   - Optimistic updates                                      │     │
│  │                                                             │     │
│  └───────────┬────────────────────────────────┬───────────────┘     │
│              │                                │                       │
│              ▼                                ▼                       │
│  ┌─────────────────────┐          ┌─────────────────────────┐       │
│  │     SQLite DB       │          │      Sync Service       │       │
│  │                     │◄────────▶│                         │       │
│  │  - Products         │          │  - Queue mutations      │       │
│  │  - Orders           │          │  - Resolve conflicts    │       │
│  │  - RFQs             │          │  - Track sync status    │       │
│  │  - Pending Actions  │          │                         │       │
│  └─────────────────────┘          └───────────┬─────────────┘       │
│                                               │                       │
│                                               ▼                       │
│                                   ┌─────────────────────────┐        │
│                                   │       REST API          │        │
│                                   │   (when online)         │        │
│                                   └─────────────────────────┘        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Database Setup

```tsx
// lib/database/db.ts
import * as SQLite from 'expo-sqlite';

let db: SQLite.SQLiteDatabase;

export async function initDatabase(): Promise<void> {
  db = await SQLite.openDatabaseAsync('shipchandlery.db');

  await db.execAsync(`
    PRAGMA journal_mode = WAL;
    PRAGMA foreign_keys = ON;

    -- Products cache
    CREATE TABLE IF NOT EXISTS products (
      id TEXT PRIMARY KEY,
      impa_code TEXT,
      name TEXT NOT NULL,
      description TEXT,
      category TEXT,
      unit TEXT,
      data TEXT,
      synced_at INTEGER,
      updated_at INTEGER
    );

    CREATE INDEX IF NOT EXISTS idx_products_impa ON products(impa_code);
    CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);

    -- Orders (local and synced)
    CREATE TABLE IF NOT EXISTS orders (
      id TEXT PRIMARY KEY,
      local_id TEXT UNIQUE,
      order_number TEXT,
      status TEXT,
      supplier_id TEXT,
      total REAL,
      data TEXT,
      synced INTEGER DEFAULT 0,
      synced_at INTEGER,
      created_at INTEGER,
      updated_at INTEGER
    );

    -- Pending actions queue
    CREATE TABLE IF NOT EXISTS pending_actions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      action_type TEXT NOT NULL,
      entity_type TEXT NOT NULL,
      entity_id TEXT,
      payload TEXT NOT NULL,
      created_at INTEGER NOT NULL,
      retry_count INTEGER DEFAULT 0,
      last_error TEXT
    );

    -- Sync metadata
    CREATE TABLE IF NOT EXISTS sync_meta (
      key TEXT PRIMARY KEY,
      value TEXT,
      updated_at INTEGER
    );
  `);
}

export function getDatabase(): SQLite.SQLiteDatabase {
  if (!db) {
    throw new Error('Database not initialized');
  }
  return db;
}
```

### Offline Storage Service

```tsx
// lib/storage/offline-storage.ts
import { getDatabase } from '../database/db';

export class OfflineStorage {
  private db = getDatabase();

  // Products
  async saveProducts(products: Product[]): Promise<void> {
    const now = Date.now();

    await this.db.withTransactionAsync(async () => {
      for (const product of products) {
        await this.db.runAsync(
          `INSERT OR REPLACE INTO products
           (id, impa_code, name, description, category, unit, data, synced_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
          [
            product.id,
            product.impaCode,
            product.name,
            product.description,
            product.category,
            product.unit,
            JSON.stringify(product),
            now,
            now,
          ]
        );
      }
    });
  }

  async getProducts(options: { category?: string; search?: string } = {}): Promise<Product[]> {
    let query = 'SELECT data FROM products WHERE 1=1';
    const params: any[] = [];

    if (options.category) {
      query += ' AND category = ?';
      params.push(options.category);
    }

    if (options.search) {
      query += ' AND (name LIKE ? OR impa_code LIKE ?)';
      params.push(`%${options.search}%`, `%${options.search}%`);
    }

    query += ' ORDER BY name';

    const rows = await this.db.getAllAsync(query, params);
    return rows.map((row: any) => JSON.parse(row.data));
  }

  async getProduct(id: string): Promise<Product | null> {
    const row = await this.db.getFirstAsync(
      'SELECT data FROM products WHERE id = ?',
      [id]
    );
    return row ? JSON.parse((row as any).data) : null;
  }

  // Orders
  async saveOrder(order: Order, synced: boolean = false): Promise<void> {
    const now = Date.now();

    await this.db.runAsync(
      `INSERT OR REPLACE INTO orders
       (id, local_id, order_number, status, supplier_id, total, data, synced, synced_at, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        order.id,
        order.localId,
        order.orderNumber,
        order.status,
        order.supplierId,
        order.total,
        JSON.stringify(order),
        synced ? 1 : 0,
        synced ? now : null,
        order.createdAt || now,
        now,
      ]
    );
  }

  async getOrders(): Promise<Order[]> {
    const rows = await this.db.getAllAsync(
      'SELECT data FROM orders ORDER BY created_at DESC'
    );
    return rows.map((row: any) => JSON.parse(row.data));
  }

  async getPendingOrders(): Promise<Order[]> {
    const rows = await this.db.getAllAsync(
      'SELECT data FROM orders WHERE synced = 0'
    );
    return rows.map((row: any) => JSON.parse(row.data));
  }

  // Pending actions
  async queueAction(
    actionType: string,
    entityType: string,
    entityId: string | null,
    payload: any
  ): Promise<number> {
    const result = await this.db.runAsync(
      `INSERT INTO pending_actions (action_type, entity_type, entity_id, payload, created_at)
       VALUES (?, ?, ?, ?, ?)`,
      [actionType, entityType, entityId, JSON.stringify(payload), Date.now()]
    );
    return result.lastInsertRowId;
  }

  async getPendingActions(): Promise<PendingAction[]> {
    return this.db.getAllAsync(
      'SELECT * FROM pending_actions ORDER BY created_at ASC'
    );
  }

  async removePendingAction(id: number): Promise<void> {
    await this.db.runAsync('DELETE FROM pending_actions WHERE id = ?', [id]);
  }

  async updateActionRetry(id: number, error: string): Promise<void> {
    await this.db.runAsync(
      'UPDATE pending_actions SET retry_count = retry_count + 1, last_error = ? WHERE id = ?',
      [error, id]
    );
  }
}

export const offlineStorage = new OfflineStorage();
```

### Sync Service

```tsx
// lib/sync/sync-service.ts
import NetInfo from '@react-native-community/netinfo';
import { offlineStorage } from '../storage/offline-storage';
import { api } from '../api/client';

class SyncService {
  private isSyncing = false;
  private syncListeners: ((status: SyncStatus) => void)[] = [];

  constructor() {
    // Listen for network changes
    NetInfo.addEventListener((state) => {
      if (state.isConnected && !this.isSyncing) {
        this.sync();
      }
    });
  }

  async sync(): Promise<SyncResult> {
    if (this.isSyncing) {
      return { success: false, message: 'Sync already in progress' };
    }

    const netInfo = await NetInfo.fetch();
    if (!netInfo.isConnected) {
      return { success: false, message: 'No network connection' };
    }

    this.isSyncing = true;
    this.notifyListeners({ status: 'syncing' });

    try {
      // 1. Push pending actions
      await this.pushPendingActions();

      // 2. Pull latest data
      await this.pullLatestData();

      this.notifyListeners({ status: 'synced', lastSyncedAt: new Date() });
      return { success: true };

    } catch (error) {
      this.notifyListeners({ status: 'error', error: error.message });
      return { success: false, message: error.message };

    } finally {
      this.isSyncing = false;
    }
  }

  private async pushPendingActions(): Promise<void> {
    const actions = await offlineStorage.getPendingActions();

    for (const action of actions) {
      try {
        await this.executePendingAction(action);
        await offlineStorage.removePendingAction(action.id);
      } catch (error) {
        if (this.isRetryableError(error)) {
          await offlineStorage.updateActionRetry(action.id, error.message);
        } else {
          // Non-retryable error - log and remove
          console.error('Non-retryable action error:', error);
          await offlineStorage.removePendingAction(action.id);
        }
      }
    }
  }

  private async executePendingAction(action: PendingAction): Promise<void> {
    const payload = JSON.parse(action.payload);

    switch (action.action_type) {
      case 'CREATE_ORDER':
        const order = await api.post('/orders', payload);
        // Update local order with server ID
        await offlineStorage.saveOrder(
          { ...payload, id: order.id, localId: payload.localId },
          true
        );
        break;

      case 'UPDATE_ORDER_STATUS':
        await api.patch(`/orders/${action.entity_id}/status`, payload);
        break;

      case 'CREATE_QUOTE':
        await api.post(`/rfqs/${payload.rfqId}/quotes`, payload);
        break;

      default:
        throw new Error(`Unknown action type: ${action.action_type}`);
    }
  }

  private async pullLatestData(): Promise<void> {
    const lastSync = await this.getLastSyncTime();

    // Pull products (incremental)
    const products = await api.get('/products', {
      params: { updatedSince: lastSync },
    });
    await offlineStorage.saveProducts(products.data);

    // Pull orders
    const orders = await api.get('/orders');
    for (const order of orders.data) {
      await offlineStorage.saveOrder(order, true);
    }

    await this.setLastSyncTime(Date.now());
  }

  private isRetryableError(error: any): boolean {
    return error.response?.status >= 500 || error.code === 'NETWORK_ERROR';
  }

  private async getLastSyncTime(): Promise<number | null> {
    const db = getDatabase();
    const row = await db.getFirstAsync(
      "SELECT value FROM sync_meta WHERE key = 'last_sync'"
    );
    return row ? parseInt((row as any).value) : null;
  }

  private async setLastSyncTime(time: number): Promise<void> {
    const db = getDatabase();
    await db.runAsync(
      `INSERT OR REPLACE INTO sync_meta (key, value, updated_at)
       VALUES ('last_sync', ?, ?)`,
      [time.toString(), Date.now()]
    );
  }

  subscribe(listener: (status: SyncStatus) => void): () => void {
    this.syncListeners.push(listener);
    return () => {
      this.syncListeners = this.syncListeners.filter((l) => l !== listener);
    };
  }

  private notifyListeners(status: SyncStatus): void {
    this.syncListeners.forEach((listener) => listener(status));
  }
}

export const syncService = new SyncService();
```

### Offline-Aware Hooks

```tsx
// hooks/use-offline-orders.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNetInfo } from '@react-native-community/netinfo';
import { offlineStorage } from '@/lib/storage/offline-storage';
import { syncService } from '@/lib/sync/sync-service';
import { api } from '@/lib/api/client';
import { v4 as uuidv4 } from 'uuid';

export function useOrders() {
  const netInfo = useNetInfo();
  const isOnline = netInfo.isConnected;

  return useQuery({
    queryKey: ['orders'],
    queryFn: async () => {
      if (isOnline) {
        try {
          const response = await api.get('/orders');
          // Cache to local storage
          for (const order of response.data) {
            await offlineStorage.saveOrder(order, true);
          }
          return response.data;
        } catch (error) {
          // Fall back to local
          return offlineStorage.getOrders();
        }
      }
      return offlineStorage.getOrders();
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useCreateOrder() {
  const queryClient = useQueryClient();
  const netInfo = useNetInfo();

  return useMutation({
    mutationFn: async (orderData: CreateOrderInput) => {
      const localId = uuidv4();
      const localOrder: Order = {
        ...orderData,
        id: localId,
        localId,
        status: 'PENDING',
        createdAt: new Date().toISOString(),
        synced: false,
      };

      // Save locally
      await offlineStorage.saveOrder(localOrder, false);

      if (netInfo.isConnected) {
        try {
          // Try to sync immediately
          const response = await api.post('/orders', orderData);
          await offlineStorage.saveOrder(
            { ...response.data, localId },
            true
          );
          return response.data;
        } catch (error) {
          // Queue for later sync
          await offlineStorage.queueAction(
            'CREATE_ORDER',
            'order',
            localId,
            { ...orderData, localId }
          );
          return localOrder;
        }
      } else {
        // Queue for later sync
        await offlineStorage.queueAction(
          'CREATE_ORDER',
          'order',
          localId,
          { ...orderData, localId }
        );
        return localOrder;
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    },
  });
}
```

### Sync Status Component

```tsx
// components/sync-status.tsx
import { View, Text, Pressable } from 'react-native';
import { useNetInfo } from '@react-native-community/netinfo';
import { useSyncStatus } from '@/hooks/use-sync-status';
import { syncService } from '@/lib/sync/sync-service';
import { Cloud, CloudOff, RefreshCw } from 'lucide-react-native';

export function SyncStatus() {
  const netInfo = useNetInfo();
  const { status, pendingCount, lastSyncedAt } = useSyncStatus();

  const handleSync = () => {
    syncService.sync();
  };

  return (
    <Pressable onPress={handleSync} style={styles.container}>
      {netInfo.isConnected ? (
        <Cloud size={16} color={status === 'synced' ? '#22c55e' : '#f59e0b'} />
      ) : (
        <CloudOff size={16} color="#ef4444" />
      )}

      <View style={styles.textContainer}>
        {!netInfo.isConnected ? (
          <Text style={styles.offlineText}>Offline</Text>
        ) : status === 'syncing' ? (
          <View style={styles.syncingContainer}>
            <RefreshCw size={12} color="#6b7280" />
            <Text style={styles.text}>Syncing...</Text>
          </View>
        ) : pendingCount > 0 ? (
          <Text style={styles.pendingText}>
            {pendingCount} pending
          </Text>
        ) : (
          <Text style={styles.text}>
            Synced {formatRelativeTime(lastSyncedAt)}
          </Text>
        )}
      </View>
    </Pressable>
  );
}
```

### Dependencies
- ADR-UI-006: React Native with Expo
- ADR-UI-008: Mobile Catalog Caching
- ADR-UI-003: State Management Strategy

### Migration Strategy
1. Set up SQLite database schema
2. Implement offline storage service
3. Create sync service
4. Build offline-aware hooks
5. Add sync status UI
6. Test offline scenarios
7. Handle edge cases and conflicts

---

## Operational Considerations

### Sync Strategy

#### Sync Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Sync State Machine                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────┐    Network Available    ┌─────────────┐            │
│  │ OFFLINE │ ───────────────────────► │  SYNCING    │            │
│  └────┬────┘                          └──────┬──────┘            │
│       │                                      │                   │
│       │ Queue actions                        │ Process queue     │
│       │                                      │                   │
│       ▼                                      ▼                   │
│  ┌─────────────┐                       ┌─────────────┐          │
│  │ PENDING     │                       │  ONLINE     │          │
│  │ QUEUE       │ ◄──── Conflict ────── │  (IDLE)     │          │
│  └─────────────┘                       └─────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Sync Timing Rules

| Trigger | Action | Priority |
|---------|--------|----------|
| App foreground | Sync pending queue | High |
| Network restored | Sync pending queue | High |
| Background fetch | Incremental catalog sync | Low |
| User pull-to-refresh | Full sync for current view | High |
| Every 15 minutes (online) | Heartbeat sync | Low |
| User logout | Clear local data | Immediate |

#### Sync Queue Implementation

```typescript
// lib/sync/sync-queue.ts
interface SyncQueueItem {
  id: string;
  type: 'CREATE' | 'UPDATE' | 'DELETE';
  entity: 'order' | 'rfq_response' | 'quote';
  payload: any;
  createdAt: number;
  retryCount: number;
  lastError?: string;
}

class SyncQueue {
  private db = getDatabase();

  async enqueue(item: Omit<SyncQueueItem, 'id' | 'createdAt' | 'retryCount'>) {
    await this.db.runAsync(
      `INSERT INTO sync_queue (id, type, entity, payload, created_at, retry_count)
       VALUES (?, ?, ?, ?, ?, ?)`,
      [uuid(), item.type, item.entity, JSON.stringify(item.payload), Date.now(), 0]
    );
  }

  async processQueue(): Promise<SyncResult> {
    const items = await this.db.getAllAsync(
      'SELECT * FROM sync_queue ORDER BY created_at ASC LIMIT 50'
    );

    const results = { success: 0, failed: 0, conflicts: 0 };

    for (const item of items) {
      try {
        await this.processItem(item);
        await this.removeItem(item.id);
        results.success++;
      } catch (error) {
        if (error.status === 409) {
          results.conflicts++;
          await this.handleConflict(item, error.serverData);
        } else {
          results.failed++;
          await this.incrementRetry(item.id, error.message);
        }
      }
    }

    return results;
  }
}
```

### Conflict Resolution

#### Resolution Strategy by Entity

| Entity | Strategy | User Action Required |
|--------|----------|---------------------|
| Draft RFQ response | Last-write-wins | No (auto-merge) |
| Submitted quote | Server wins | Yes (notify user) |
| Order modifications | Server wins | Yes (review changes) |
| User preferences | Client wins | No |
| Product favorites | Merge (union) | No |
| Cart items | Client wins | No |

#### Conflict Detection Implementation

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

    onError: (error, { id }, context) => {
      // Rollback on error
      queryClient.setQueryData(['orders', id], context.previous);

      if (error.response?.status === 409) {
        // Conflict detected
        toast.error('Order was modified. Please refresh.');
        queryClient.invalidateQueries({ queryKey: ['orders', id] });
      }
    },
  });
}
```

### Storage Limits

#### Storage Budget

| Data Category | Max Size | Eviction Policy |
|--------------|----------|-----------------|
| Product catalog | 50 MB | Version-based replacement |
| Product images | 100 MB | LRU (oldest access first) |
| Order history | 20 MB | Oldest orders first (keep 6 months) |
| Pending sync queue | 10 MB | Fail if exceeded |
| User preferences | 1 MB | None (always kept) |
| Draft forms | 5 MB | Oldest drafts first |
| **Total budget** | **200 MB** | |

#### Storage Monitoring

```typescript
class StorageManager {
  private limits = {
    catalog: 50 * 1024 * 1024,
    images: 100 * 1024 * 1024,
    syncQueue: 10 * 1024 * 1024,
    total: 200 * 1024 * 1024,
  };

  async checkStorage(): Promise<StorageStatus> {
    const usage = await this.getUsage();
    return {
      total: usage.total,
      limit: this.limits.total,
      percentUsed: (usage.total / this.limits.total) * 100,
      warnings: this.getWarnings(usage),
    };
  }

  private getWarnings(usage: StorageUsage): string[] {
    const warnings: string[] = [];
    if (usage.total > this.limits.total * 0.9) {
      warnings.push('Storage nearly full. Consider clearing cache.');
    }
    return warnings;
  }
}
```

### Offline Data Security

#### Encryption Strategy

| Data Type | Encryption | Key Storage | Notes |
|-----------|-----------|-------------|-------|
| Auth tokens | Yes (AES-256) | Secure Enclave | expo-secure-store |
| User credentials | Never stored | N/A | Re-authenticate on expiry |
| Product catalog | No | N/A | Public data |
| Order data | Yes (AES-256) | Secure Enclave | Contains PII |
| Sync queue | Yes (AES-256) | Secure Enclave | May contain sensitive data |
| Draft forms | Yes (AES-256) | Secure Enclave | May contain pricing |

#### Security Implementation

```typescript
// lib/security/encrypted-storage.ts
import * as SecureStore from 'expo-secure-store';

class EncryptedStorage {
  private keyId = 'app-encryption-key';

  async initialize() {
    let key = await SecureStore.getItemAsync(this.keyId);
    if (!key) {
      key = await generateEncryptionKey();
      await SecureStore.setItemAsync(this.keyId, key);
    }
  }

  async encryptAndStore(key: string, data: any): Promise<void> {
    const encryptionKey = await SecureStore.getItemAsync(this.keyId);
    const encrypted = await encrypt(JSON.stringify(data), encryptionKey);
    await AsyncStorage.setItem(key, encrypted);
  }

  // Wipe all encrypted data on logout
  async wipeSecureData(): Promise<void> {
    await SecureStore.deleteItemAsync(this.keyId);
    const keys = await AsyncStorage.getAllKeys();
    const encryptedKeys = keys.filter(k => k.startsWith('encrypted_'));
    await AsyncStorage.multiRemove(encryptedKeys);
  }
}
```

#### Data Expiration Policies

| Data Type | Offline Expiry | Action on Expiry |
|-----------|---------------|------------------|
| Auth tokens | 7 days | Force re-login |
| Order data | 30 days | Remove, re-fetch on connect |
| Sync queue items | 14 days | Discard with warning |
| Product catalog | 30 days | Force refresh on connect |
| Cached images | 14 days | Remove from cache |

#### Device Policies

| Policy | Implementation | Enforcement |
|--------|---------------|-------------|
| Biometric lock | Optional in settings | expo-local-authentication |
| Auto-logout | 24h inactive | Background timer |
| Secure wipe | On repeated auth failures | Clear all local data |
| Screenshot prevention | iOS/Android flags | Sensitive screens only |

### Open Questions - Resolved

- **Q:** What is the expected offline duration and data scope?
  - **A:** We support the following offline scenarios:
    1. **Duration**: Up to 7 days fully offline (auth token expiry limit)
    2. **Data scope**:
       - Full product catalog (50K items, ~50MB)
       - Last 6 months of order history (~500 orders)
       - Up to 10 pending RFQ responses in draft
       - All user preferences and favorites
    3. **Sync queue**: Max 14 days of pending actions before expiry warning
    4. **Partial connectivity**: Works with intermittent connections (auto-resume sync)
    5. **User notification**: Clear UI indicators for offline status, pending sync count, and last sync time
    6. **Critical actions**: Users warned before taking actions that require eventual connectivity (e.g., submitting quotes)

---

## References
- [Offline First Design Patterns](https://offlinefirst.org/)
- [expo-sqlite Documentation](https://docs.expo.dev/versions/latest/sdk/sqlite/)
- [React Query Offline Support](https://tanstack.com/query/latest/docs/react/guides/offline)
