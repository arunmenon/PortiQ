# ADR-UI-008: Mobile Catalog Caching

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Frontend

---

## Context

The mobile app needs efficient caching of the product catalog (50K+ items) for offline access and fast search.

### Business Context
Catalog caching needs:
- Offline product browsing
- Fast search even without network
- IMPA code lookup
- Category filtering
- Minimal storage footprint
- Incremental updates

### Technical Context
- React Native with Expo (ADR-UI-006)
- SQLite for offline storage (ADR-UI-007)
- 50,000+ products in catalog
- Products change infrequently
- Search needs to be fast (<100ms)

### Assumptions
- Full catalog download acceptable (one-time)
- Incremental sync for updates
- SQLite FTS for search
- Products fit in reasonable storage (~50MB)

---

## Decision Drivers

- Offline search performance
- Storage efficiency
- Sync efficiency
- Battery impact
- User experience

---

## Decision

We will implement a tiered caching strategy with SQLite Full-Text Search (FTS5) for the product catalog, using incremental sync and background updates.

---

## Implementation Notes

### Caching Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Catalog Caching Architecture                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │                     Search Interface                        │     │
│  │                                                             │     │
│  │   useProductSearch(query)                                   │     │
│  │                                                             │     │
│  └───────────────────────────┬─────────────────────────────────┘     │
│                              │                                        │
│                              ▼                                        │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │                    SQLite + FTS5                            │     │
│  │                                                             │     │
│  │   products table      ◄──────►    products_fts (FTS5)      │     │
│  │   - id                           - name                     │     │
│  │   - impa_code                    - description              │     │
│  │   - name                         - impa_code                │     │
│  │   - data (JSON)                  - category                 │     │
│  │                                                             │     │
│  └───────────────────────────┬─────────────────────────────────┘     │
│                              │                                        │
│                              ▼                                        │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │                    Sync Service                             │     │
│  │                                                             │     │
│  │   Initial Load ──► Full catalog (~50MB)                    │     │
│  │   Updates ──► Incremental (since lastSync)                  │     │
│  │   Background ──► Daily refresh                              │     │
│  │                                                             │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Database Schema with FTS

```tsx
// lib/database/catalog-schema.ts
import { getDatabase } from './db';

export async function initCatalogSchema(): Promise<void> {
  const db = getDatabase();

  await db.execAsync(`
    -- Main products table
    CREATE TABLE IF NOT EXISTS products (
      id TEXT PRIMARY KEY,
      impa_code TEXT UNIQUE,
      name TEXT NOT NULL,
      description TEXT,
      category_id TEXT,
      category_name TEXT,
      unit TEXT,
      ihm_flag INTEGER DEFAULT 0,
      specifications TEXT,
      image_url TEXT,
      data TEXT,
      version INTEGER DEFAULT 1,
      synced_at INTEGER
    );

    CREATE INDEX IF NOT EXISTS idx_products_impa ON products(impa_code);
    CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);

    -- FTS5 virtual table for fast search
    CREATE VIRTUAL TABLE IF NOT EXISTS products_fts USING fts5(
      name,
      description,
      impa_code,
      category_name,
      specifications,
      content='products',
      content_rowid='rowid'
    );

    -- Triggers to keep FTS in sync
    CREATE TRIGGER IF NOT EXISTS products_ai AFTER INSERT ON products BEGIN
      INSERT INTO products_fts(rowid, name, description, impa_code, category_name, specifications)
      VALUES (new.rowid, new.name, new.description, new.impa_code, new.category_name, new.specifications);
    END;

    CREATE TRIGGER IF NOT EXISTS products_ad AFTER DELETE ON products BEGIN
      INSERT INTO products_fts(products_fts, rowid, name, description, impa_code, category_name, specifications)
      VALUES('delete', old.rowid, old.name, old.description, old.impa_code, old.category_name, old.specifications);
    END;

    CREATE TRIGGER IF NOT EXISTS products_au AFTER UPDATE ON products BEGIN
      INSERT INTO products_fts(products_fts, rowid, name, description, impa_code, category_name, specifications)
      VALUES('delete', old.rowid, old.name, old.description, old.impa_code, old.category_name, old.specifications);
      INSERT INTO products_fts(rowid, name, description, impa_code, category_name, specifications)
      VALUES (new.rowid, new.name, new.description, new.impa_code, new.category_name, new.specifications);
    END;

    -- Categories table
    CREATE TABLE IF NOT EXISTS categories (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      parent_id TEXT,
      product_count INTEGER DEFAULT 0,
      synced_at INTEGER
    );

    -- Catalog sync metadata
    CREATE TABLE IF NOT EXISTS catalog_sync (
      id INTEGER PRIMARY KEY CHECK (id = 1),
      last_full_sync INTEGER,
      last_incremental_sync INTEGER,
      product_count INTEGER,
      version TEXT
    );

    -- Initialize sync metadata
    INSERT OR IGNORE INTO catalog_sync (id) VALUES (1);
  `);
}
```

### Catalog Service

```tsx
// lib/catalog/catalog-service.ts
import { getDatabase } from '../database/db';
import { api } from '../api/client';
import * as FileSystem from 'expo-file-system';

class CatalogService {
  private db = getDatabase();
  private syncInProgress = false;

  async initialize(): Promise<void> {
    const syncInfo = await this.getSyncInfo();

    if (!syncInfo.last_full_sync) {
      // First time - need full sync
      await this.performFullSync();
    } else {
      // Check if incremental sync needed
      const hoursSinceSync = (Date.now() - syncInfo.last_incremental_sync) / (1000 * 60 * 60);
      if (hoursSinceSync > 24) {
        // Background incremental sync
        this.performIncrementalSync();
      }
    }
  }

  async performFullSync(): Promise<void> {
    if (this.syncInProgress) return;
    this.syncInProgress = true;

    try {
      console.log('Starting full catalog sync...');

      // Download catalog file
      const catalogUrl = await api.get('/catalog/download-url');
      const localPath = `${FileSystem.cacheDirectory}catalog.json`;

      await FileSystem.downloadAsync(catalogUrl.url, localPath);

      // Read and parse
      const content = await FileSystem.readAsStringAsync(localPath);
      const catalog = JSON.parse(content);

      // Batch insert
      await this.batchInsertProducts(catalog.products);

      // Update categories
      await this.updateCategories(catalog.categories);

      // Update sync metadata
      await this.db.runAsync(
        `UPDATE catalog_sync SET
         last_full_sync = ?,
         last_incremental_sync = ?,
         product_count = ?,
         version = ?
         WHERE id = 1`,
        [Date.now(), Date.now(), catalog.products.length, catalog.version]
      );

      // Cleanup
      await FileSystem.deleteAsync(localPath, { idempotent: true });

      console.log(`Full sync complete: ${catalog.products.length} products`);

    } finally {
      this.syncInProgress = false;
    }
  }

  async performIncrementalSync(): Promise<void> {
    if (this.syncInProgress) return;
    this.syncInProgress = true;

    try {
      const syncInfo = await this.getSyncInfo();
      const lastSync = syncInfo.last_incremental_sync;

      const updates = await api.get('/catalog/updates', {
        params: { since: lastSync },
      });

      if (updates.products.length > 0) {
        await this.batchInsertProducts(updates.products);
      }

      if (updates.deleted.length > 0) {
        await this.deleteProducts(updates.deleted);
      }

      await this.db.runAsync(
        'UPDATE catalog_sync SET last_incremental_sync = ? WHERE id = 1',
        [Date.now()]
      );

      console.log(`Incremental sync: ${updates.products.length} updated, ${updates.deleted.length} deleted`);

    } finally {
      this.syncInProgress = false;
    }
  }

  private async batchInsertProducts(products: Product[]): Promise<void> {
    const BATCH_SIZE = 500;

    for (let i = 0; i < products.length; i += BATCH_SIZE) {
      const batch = products.slice(i, i + BATCH_SIZE);

      await this.db.withTransactionAsync(async () => {
        for (const product of batch) {
          await this.db.runAsync(
            `INSERT OR REPLACE INTO products
             (id, impa_code, name, description, category_id, category_name, unit, ihm_flag, specifications, image_url, data, synced_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
            [
              product.id,
              product.impaCode,
              product.name,
              product.description,
              product.categoryId,
              product.categoryName,
              product.unit,
              product.ihmFlag ? 1 : 0,
              product.specifications,
              product.imageUrl,
              JSON.stringify(product),
              Date.now(),
            ]
          );
        }
      });
    }
  }

  private async deleteProducts(ids: string[]): Promise<void> {
    const placeholders = ids.map(() => '?').join(',');
    await this.db.runAsync(
      `DELETE FROM products WHERE id IN (${placeholders})`,
      ids
    );
  }

  private async updateCategories(categories: Category[]): Promise<void> {
    await this.db.withTransactionAsync(async () => {
      await this.db.runAsync('DELETE FROM categories');

      for (const category of categories) {
        await this.db.runAsync(
          `INSERT INTO categories (id, name, parent_id, product_count, synced_at)
           VALUES (?, ?, ?, ?, ?)`,
          [category.id, category.name, category.parentId, category.productCount, Date.now()]
        );
      }
    });
  }

  async getSyncInfo(): Promise<CatalogSyncInfo> {
    const row = await this.db.getFirstAsync('SELECT * FROM catalog_sync WHERE id = 1');
    return row as CatalogSyncInfo;
  }

  // Search methods
  async search(query: string, options: SearchOptions = {}): Promise<Product[]> {
    const { category, limit = 50, offset = 0 } = options;

    if (!query || query.length < 2) {
      return this.getProducts({ category, limit, offset });
    }

    // Use FTS for search
    let sql = `
      SELECT p.data
      FROM products p
      JOIN products_fts fts ON p.rowid = fts.rowid
      WHERE products_fts MATCH ?
    `;
    const params: any[] = [this.buildFtsQuery(query)];

    if (category) {
      sql += ' AND p.category_id = ?';
      params.push(category);
    }

    sql += ' ORDER BY rank LIMIT ? OFFSET ?';
    params.push(limit, offset);

    const rows = await this.db.getAllAsync(sql, params);
    return rows.map((row: any) => JSON.parse(row.data));
  }

  private buildFtsQuery(query: string): string {
    // Handle IMPA code search
    if (/^\d{6}$/.test(query)) {
      return `impa_code:${query}`;
    }

    // Tokenize and create prefix search
    const tokens = query
      .toLowerCase()
      .split(/\s+/)
      .filter((t) => t.length > 1)
      .map((t) => `${t}*`);

    return tokens.join(' AND ');
  }

  async getProducts(options: { category?: string; limit?: number; offset?: number } = {}): Promise<Product[]> {
    const { category, limit = 50, offset = 0 } = options;

    let sql = 'SELECT data FROM products';
    const params: any[] = [];

    if (category) {
      sql += ' WHERE category_id = ?';
      params.push(category);
    }

    sql += ' ORDER BY name LIMIT ? OFFSET ?';
    params.push(limit, offset);

    const rows = await this.db.getAllAsync(sql, params);
    return rows.map((row: any) => JSON.parse(row.data));
  }

  async getProduct(id: string): Promise<Product | null> {
    const row = await this.db.getFirstAsync(
      'SELECT data FROM products WHERE id = ?',
      [id]
    );
    return row ? JSON.parse((row as any).data) : null;
  }

  async getProductByImpa(impaCode: string): Promise<Product | null> {
    const row = await this.db.getFirstAsync(
      'SELECT data FROM products WHERE impa_code = ?',
      [impaCode]
    );
    return row ? JSON.parse((row as any).data) : null;
  }

  async getCategories(): Promise<Category[]> {
    return this.db.getAllAsync(
      'SELECT * FROM categories ORDER BY name'
    );
  }

  async getStorageInfo(): Promise<StorageInfo> {
    const productCount = await this.db.getFirstAsync(
      'SELECT COUNT(*) as count FROM products'
    );
    const dbPath = `${FileSystem.documentDirectory}SQLite/shipchandlery.db`;
    const dbInfo = await FileSystem.getInfoAsync(dbPath);

    return {
      productCount: (productCount as any).count,
      databaseSize: dbInfo.exists ? dbInfo.size : 0,
      lastSync: (await this.getSyncInfo()).last_incremental_sync,
    };
  }
}

export const catalogService = new CatalogService();
```

### Search Hook

```tsx
// hooks/use-product-search.ts
import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { catalogService } from '@/lib/catalog/catalog-service';
import debounce from 'lodash/debounce';

export function useProductSearch(initialQuery = '') {
  const [query, setQuery] = useState(initialQuery);
  const [debouncedQuery, setDebouncedQuery] = useState(initialQuery);

  const debouncedSetQuery = useMemo(
    () => debounce((q: string) => setDebouncedQuery(q), 300),
    []
  );

  useEffect(() => {
    debouncedSetQuery(query);
    return () => debouncedSetQuery.cancel();
  }, [query]);

  const { data: results, isLoading } = useQuery({
    queryKey: ['product-search', debouncedQuery],
    queryFn: () => catalogService.search(debouncedQuery),
    enabled: true,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  return {
    query,
    setQuery,
    results: results || [],
    isLoading,
  };
}

export function useProduct(id: string) {
  return useQuery({
    queryKey: ['product', id],
    queryFn: () => catalogService.getProduct(id),
    enabled: !!id,
  });
}

export function useProductByImpa(impaCode: string) {
  return useQuery({
    queryKey: ['product-impa', impaCode],
    queryFn: () => catalogService.getProductByImpa(impaCode),
    enabled: !!impaCode && /^\d{6}$/.test(impaCode),
  });
}

export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: () => catalogService.getCategories(),
    staleTime: 1000 * 60 * 60, // 1 hour
  });
}
```

### Product Search Screen

```tsx
// app/(buyer)/catalog/index.tsx
import { View, FlatList, ActivityIndicator } from 'react-native';
import { useState } from 'react';
import { useProductSearch, useCategories } from '@/hooks/use-product-search';
import { SearchInput } from '@/components/ui/search-input';
import { CategoryPicker } from '@/components/catalog/category-picker';
import { ProductCard } from '@/components/catalog/product-card';
import { EmptyState } from '@/components/ui/empty-state';

export default function CatalogScreen() {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const { query, setQuery, results, isLoading } = useProductSearch();
  const { data: categories } = useCategories();

  const filteredResults = selectedCategory
    ? results.filter((p) => p.categoryId === selectedCategory)
    : results;

  return (
    <View style={styles.container}>
      <SearchInput
        value={query}
        onChangeText={setQuery}
        placeholder="Search by name or IMPA code..."
        autoFocus
      />

      <CategoryPicker
        categories={categories || []}
        selected={selectedCategory}
        onSelect={setSelectedCategory}
      />

      {isLoading ? (
        <ActivityIndicator size="large" style={styles.loader} />
      ) : filteredResults.length === 0 ? (
        <EmptyState
          icon="search"
          title="No products found"
          description={query ? `No results for "${query}"` : 'Start typing to search'}
        />
      ) : (
        <FlatList
          data={filteredResults}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <ProductCard product={item} />}
          contentContainerStyle={styles.list}
          initialNumToRender={10}
          maxToRenderPerBatch={20}
          windowSize={5}
        />
      )}
    </View>
  );
}
```

### Background Sync

```tsx
// lib/catalog/background-sync.ts
import * as BackgroundFetch from 'expo-background-fetch';
import * as TaskManager from 'expo-task-manager';
import { catalogService } from './catalog-service';

const CATALOG_SYNC_TASK = 'catalog-background-sync';

TaskManager.defineTask(CATALOG_SYNC_TASK, async () => {
  try {
    await catalogService.performIncrementalSync();
    return BackgroundFetch.BackgroundFetchResult.NewData;
  } catch (error) {
    console.error('Background sync failed:', error);
    return BackgroundFetch.BackgroundFetchResult.Failed;
  }
});

export async function registerBackgroundSync(): Promise<void> {
  const status = await BackgroundFetch.getStatusAsync();

  if (status === BackgroundFetch.BackgroundFetchStatus.Available) {
    await BackgroundFetch.registerTaskAsync(CATALOG_SYNC_TASK, {
      minimumInterval: 60 * 60 * 24, // 24 hours
      stopOnTerminate: false,
      startOnBoot: true,
    });
  }
}
```

### Dependencies
- ADR-UI-006: React Native with Expo
- ADR-UI-007: Offline-First Mobile
- ADR-FN-001: IMPA/ISSA Code as Primary Identifier

### Migration Strategy
1. Create catalog database schema with FTS
2. Implement catalog service
3. Build initial sync flow
4. Add incremental sync
5. Create search hooks
6. Build search UI
7. Set up background sync
8. Test with full catalog

---

## Operational Considerations

### Cache Invalidation Strategy

#### Catalog Version Management

```typescript
// Catalog versioning schema
interface CatalogVersion {
  version: string;           // Semantic version (e.g., "2025.01.15.001")
  publishedAt: string;       // ISO timestamp
  productCount: number;      // Total products in this version
  checksum: string;          // SHA-256 of catalog data
  deltaAvailable: boolean;   // Whether incremental update exists
  deltaFromVersion?: string; // Minimum version for delta update
}

// Version check on app launch
async function checkCatalogVersion(): Promise<CatalogUpdateInfo> {
  const localVersion = await getCatalogVersion();
  const serverVersion = await api.get('/catalog/version');

  if (!localVersion) {
    return { action: 'FULL_DOWNLOAD', reason: 'No local catalog' };
  }

  if (localVersion.version === serverVersion.version) {
    return { action: 'NONE', reason: 'Already up to date' };
  }

  if (serverVersion.deltaAvailable &&
      localVersion.version >= serverVersion.deltaFromVersion) {
    return { action: 'DELTA_UPDATE', reason: 'Incremental update available' };
  }

  return { action: 'FULL_DOWNLOAD', reason: 'Version too old for delta' };
}
```

#### Invalidation Triggers

| Trigger | Action | User Notification |
|---------|--------|------------------|
| App launch (online) | Version check | None (background) |
| Manual refresh | Force re-check | Progress indicator |
| Push notification | Immediate sync | Badge + optional toast |
| Background fetch (24h) | Version check | None |
| Catalog age > 30 days | Force full sync | Modal prompt |

#### Incremental Sync API

```typescript
// Server endpoint: GET /catalog/updates?since={version}
interface CatalogDelta {
  fromVersion: string;
  toVersion: string;
  added: Product[];          // New products
  updated: Product[];        // Modified products
  deleted: string[];         // Removed product IDs
  checksum: string;          // Verification hash
}

// Client-side delta application
async function applyDelta(delta: CatalogDelta): Promise<void> {
  const db = getDatabase();

  await db.withTransactionAsync(async () => {
    // Apply deletions first
    if (delta.deleted.length > 0) {
      const placeholders = delta.deleted.map(() => '?').join(',');
      await db.runAsync(
        `DELETE FROM products WHERE id IN (${placeholders})`,
        delta.deleted
      );
    }

    // Apply updates/additions
    for (const product of [...delta.added, ...delta.updated]) {
      await db.runAsync(
        `INSERT OR REPLACE INTO products
         (id, impa_code, name, description, category_id, ..., synced_at)
         VALUES (?, ?, ?, ?, ?, ..., ?)`,
        [product.id, product.impaCode, ..., Date.now()]
      );
    }

    // Update FTS index
    await db.runAsync('INSERT INTO products_fts(products_fts) VALUES("rebuild")');

    // Update version metadata
    await db.runAsync(
      `UPDATE catalog_sync SET version = ?, last_incremental_sync = ? WHERE id = 1`,
      [delta.toVersion, Date.now()]
    );
  });

  // Verify integrity
  const localChecksum = await computeCatalogChecksum();
  if (localChecksum !== delta.checksum) {
    throw new Error('Catalog integrity check failed - triggering full sync');
  }
}
```

### Storage Budget

#### Allocation by Category

| Category | Budget | Typical Size | Notes |
|----------|--------|--------------|-------|
| Product catalog (SQLite) | 50 MB | 45 MB | 50K products |
| FTS index | 15 MB | 12 MB | Full-text search |
| Product images (cached) | 100 MB | Variable | LRU eviction |
| Category icons | 5 MB | 3 MB | Static, rarely changes |
| Search history | 1 MB | < 100 KB | Local only |
| **Total catalog storage** | **170 MB** | | |

#### Storage Monitoring Dashboard

```typescript
// components/settings/storage-info.tsx
export function StorageInfo() {
  const { data: storage } = useStorageInfo();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Catalog Storage</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <StorageBar
            label="Product Database"
            used={storage.catalogSize}
            budget={50 * 1024 * 1024}
          />
          <StorageBar
            label="Search Index"
            used={storage.ftsSize}
            budget={15 * 1024 * 1024}
          />
          <StorageBar
            label="Cached Images"
            used={storage.imageCache}
            budget={100 * 1024 * 1024}
          />
          <Separator />
          <div className="flex justify-between">
            <span>Total: {formatBytes(storage.total)}</span>
            <span>Products: {storage.productCount.toLocaleString()}</span>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onPress={clearImageCache}>
              Clear Image Cache
            </Button>
            <Button variant="outline" onPress={rebuildIndex}>
              Rebuild Search Index
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

### Eviction Policy

#### Image Cache Eviction (LRU)

```typescript
// lib/cache/image-cache.ts
const IMAGE_CACHE_LIMIT = 100 * 1024 * 1024; // 100 MB

class ImageCache {
  private accessLog = new Map<string, number>(); // path -> lastAccess

  async cacheImage(url: string): Promise<string> {
    const filename = hashUrl(url);
    const localPath = `${FileSystem.cacheDirectory}images/${filename}`;

    // Check if already cached
    const info = await FileSystem.getInfoAsync(localPath);
    if (info.exists) {
      this.recordAccess(localPath);
      return localPath;
    }

    // Ensure space available
    await this.ensureSpace(1024 * 1024); // Reserve 1MB for new image

    // Download and cache
    await FileSystem.downloadAsync(url, localPath);
    this.recordAccess(localPath);

    return localPath;
  }

  private async ensureSpace(needed: number): Promise<void> {
    const usage = await this.getCacheSize();

    if (usage + needed > IMAGE_CACHE_LIMIT) {
      const toFree = (usage + needed) - (IMAGE_CACHE_LIMIT * 0.8); // Free to 80%
      await this.evictOldest(toFree);
    }
  }

  private async evictOldest(bytesToFree: number): Promise<void> {
    const files = await FileSystem.readDirectoryAsync(
      `${FileSystem.cacheDirectory}images/`
    );

    // Sort by last access time (oldest first)
    const sorted = files
      .map(f => ({ path: f, lastAccess: this.accessLog.get(f) || 0 }))
      .sort((a, b) => a.lastAccess - b.lastAccess);

    let freed = 0;
    for (const file of sorted) {
      if (freed >= bytesToFree) break;

      const info = await FileSystem.getInfoAsync(file.path);
      if (info.exists && info.size) {
        await FileSystem.deleteAsync(file.path);
        freed += info.size;
        this.accessLog.delete(file.path);
      }
    }
  }
}
```

### Prefetching Rules

#### Prefetch Strategy

| Context | Prefetch Action | Priority |
|---------|-----------------|----------|
| App launch | Top 100 product images | High |
| Category browse | Category product images | Medium |
| Search results | First 20 result images | Medium |
| Product view | Related product images | Low |
| Low connectivity | Disable prefetch | N/A |
| Battery saver mode | Disable prefetch | N/A |

#### Implementation

```typescript
// lib/cache/prefetch-manager.ts
class PrefetchManager {
  private queue: PrefetchItem[] = [];
  private isProcessing = false;

  async prefetchCategoryImages(categoryId: string): Promise<void> {
    const products = await catalogService.getProducts({ category: categoryId, limit: 50 });

    const items = products
      .filter(p => p.imageUrl)
      .map(p => ({
        url: p.imageUrl,
        priority: 'medium' as const,
        context: `category:${categoryId}`,
      }));

    this.enqueue(items);
  }

  async prefetchSearchResults(query: string, products: Product[]): Promise<void> {
    // Only prefetch first 20 images
    const items = products
      .slice(0, 20)
      .filter(p => p.imageUrl)
      .map(p => ({
        url: p.imageUrl,
        priority: 'medium' as const,
        context: `search:${query}`,
      }));

    this.enqueue(items);
  }

  private shouldPrefetch(): boolean {
    const netInfo = NetInfo.fetch();
    const batteryState = Battery.getBatteryStateAsync();

    // Don't prefetch on cellular with low signal
    if (netInfo.type === 'cellular' && netInfo.details?.cellularGeneration === '2g') {
      return false;
    }

    // Don't prefetch in battery saver mode
    if (batteryState.batteryState === Battery.BatteryState.LOW) {
      return false;
    }

    return true;
  }
}
```

### Pricing and Availability Integration

#### Data Separation Strategy

| Data Type | Cache Location | TTL | Update Trigger |
|-----------|---------------|-----|----------------|
| Product metadata | SQLite (catalog) | 30 days | Catalog version change |
| Product images | File cache | 14 days | LRU eviction |
| **Prices** | **React Query only** | **5 min** | **API call** |
| **Availability** | **React Query only** | **1 min** | **API call** |

#### Real-time Price/Availability Fetch

```typescript
// hooks/use-product-pricing.ts
export function useProductPricing(productId: string, supplierId?: string) {
  return useQuery({
    queryKey: ['pricing', productId, supplierId],
    queryFn: () => api.get(`/products/${productId}/pricing`, {
      params: { supplierId },
    }),
    staleTime: 1000 * 60 * 5,    // 5 minutes
    gcTime: 1000 * 60 * 15,      // 15 minutes
    enabled: !!productId,
    // Don't retry on network error (show cached catalog data instead)
    retry: (failureCount, error) => {
      if (error.code === 'NETWORK_ERROR') return false;
      return failureCount < 2;
    },
  });
}

// Product detail combines cached catalog + fresh pricing
export function ProductDetail({ productId }: ProductDetailProps) {
  // From SQLite cache (instant)
  const { data: product } = useProduct(productId);

  // From API (may be loading)
  const { data: pricing, isLoading: pricingLoading } = useProductPricing(productId);

  return (
    <View>
      {/* Catalog data always available */}
      <Text>{product.name}</Text>
      <Text>{product.description}</Text>

      {/* Pricing with loading state */}
      {pricingLoading ? (
        <PricingSkeleton />
      ) : pricing ? (
        <PricingDisplay pricing={pricing} />
      ) : (
        <Text>Pricing unavailable offline</Text>
      )}
    </View>
  );
}
```

### Open Questions - Resolved

- **Q:** How will caching interact with pricing or availability changes?
  - **A:** We implement a strict separation between cached and real-time data:
    1. **Catalog data (cached)**: Product name, description, IMPA code, specifications, images - stored in SQLite, updated via versioned catalog sync
    2. **Pricing data (real-time)**: Never cached to SQLite; fetched via API with 5-minute React Query cache
    3. **Availability data (real-time)**: Never cached to SQLite; fetched via API with 1-minute cache
    4. **Offline behavior**: Catalog browsing works offline; pricing shows "unavailable offline" indicator
    5. **UI separation**: Clear visual distinction between cached product info and real-time pricing
    6. **Supplier-specific pricing**: Fetched on-demand when supplier is selected, never pre-cached

---

## References
- [SQLite FTS5](https://www.sqlite.org/fts5.html)
- [expo-sqlite Documentation](https://docs.expo.dev/versions/latest/sdk/sqlite/)
- [React Native Performance](https://reactnative.dev/docs/performance)
