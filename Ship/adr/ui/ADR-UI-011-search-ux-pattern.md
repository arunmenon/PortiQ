# ADR-UI-011: Search UX Pattern

**Status:** Superseded
**Superseded By:** ADR-UI-015
**Date:** 2025-01-20 (original) | 2026-02-06 (superseded)
**Reason:** PortiQ AI-native UX specification replaces traditional search with unified Command Bar and voice input. See ADR-UI-015 for the new architecture.
**Technical Area:** Frontend

---

> **This ADR has been superseded.** The PortiQ UX Design introduces a Command Bar with natural language understanding and voice input that replaces traditional faceted search. Please refer to [ADR-UI-015](./ADR-UI-015-command-bar-voice-input.md) for current architecture.

---

## Context (Historical)

The platform needs a powerful search experience to help users quickly find products from a catalog of 50,000+ IMPA items, as well as search RFQs, orders, and suppliers.

### Business Context
Search requirements:
- 50,000+ products with IMPA codes
- Technical marine terminology
- Multi-language product names
- Port and vessel name searches
- Time-sensitive procurement scenarios
- Mobile-first field usage

### Technical Context
- Meilisearch backend (ADR-NF-003)
- PostgreSQL full-text for structured data
- pgvector for semantic search (ADR-NF-002)
- Next.js frontend (ADR-UI-001)
- React Native mobile (ADR-UI-006)
- Offline catalog (ADR-UI-008)

### Assumptions
- Users know IMPA codes or partial names
- Typo-tolerance critical for field entry
- Faceted filtering reduces results quickly
- Recent/saved searches improve efficiency

---

## Decision Drivers

- Search speed (< 50ms response)
- Typo tolerance for maritime terms
- Faceted filtering UX
- Mobile usability
- Offline search capability

---

## Considered Options

### Option 1: Custom Autocomplete with Meilisearch
**Description:** Custom search UI components with Meilisearch instant search.

**Pros:**
- Full control over UX
- Optimized for maritime domain
- Consistent with design system
- Mobile-optimized

**Cons:**
- More development effort
- Maintain own components

### Option 2: Algolia InstantSearch
**Description:** Use Algolia's InstantSearch React components.

**Pros:**
- Ready-made components
- Excellent UX patterns
- Well-tested

**Cons:**
- Algolia lock-in (different backend)
- Limited customization
- Cost at scale

### Option 3: Headless Search UI
**Description:** Use headless search library with custom rendering.

**Pros:**
- Flexibility
- Backend agnostic
- Custom styling

**Cons:**
- Still need Meilisearch adapter
- More glue code

---

## Decision

**Chosen Option:** Custom Autocomplete with Meilisearch

We will build custom search components using Meilisearch's JavaScript SDK, implementing autocomplete, faceted filtering, and instant search patterns optimized for the maritime domain.

### Rationale
Custom components allow optimization for IMPA code patterns, maritime terminology, and offline-first mobile. Meilisearch provides the typo-tolerance and speed needed. The investment in custom UI pays off in domain-specific features.

---

## Consequences

### Positive
- Optimized for IMPA codes
- Maritime-specific UX
- Consistent design system
- Offline mobile support

### Negative
- Development investment
- **Mitigation:** Reusable component library
- Testing complexity
- **Mitigation:** Comprehensive Storybook stories

### Risks
- Performance on large catalogs: Meilisearch pagination, limit facets
- Mobile keyboard handling: Platform-specific optimizations

---

## Implementation Notes

### Search Components Architecture

```
components/search/
├── global-search/
│   ├── global-search.tsx      # Main search bar
│   ├── search-results.tsx     # Results dropdown
│   ├── search-hit.tsx         # Individual result
│   └── recent-searches.tsx    # Search history
├── catalog-search/
│   ├── catalog-search.tsx     # Catalog page search
│   ├── faceted-filters.tsx    # Filter sidebar
│   ├── filter-group.tsx       # Filter category
│   └── active-filters.tsx     # Applied filter chips
├── hooks/
│   ├── use-search.ts          # Search state hook
│   ├── use-facets.ts          # Facet management
│   └── use-search-history.ts  # Recent searches
└── utils/
    ├── meilisearch-client.ts  # SDK wrapper
    └── search-analytics.ts    # Search tracking
```

### Meilisearch Client Configuration

```typescript
// lib/search/meilisearch-client.ts
import { MeiliSearch, Index, SearchResponse } from 'meilisearch';

const client = new MeiliSearch({
  host: process.env.NEXT_PUBLIC_MEILISEARCH_HOST!,
  apiKey: process.env.NEXT_PUBLIC_MEILISEARCH_KEY!,
});

export interface ProductSearchResult {
  id: string;
  impaCode: string;
  name: string;
  description: string;
  category: string;
  subcategory: string;
  unit: string;
  ihmStatus: string;
  synonyms: string[];
  _formatted?: {
    name?: string;
    description?: string;
  };
}

export interface SearchFilters {
  category?: string[];
  subcategory?: string[];
  ihmStatus?: string[];
  unit?: string[];
}

export async function searchProducts(
  query: string,
  filters?: SearchFilters,
  options?: {
    limit?: number;
    offset?: number;
    facets?: string[];
  }
): Promise<SearchResponse<ProductSearchResult>> {
  const index = client.index('products');

  const filterArray: string[] = [];

  if (filters?.category?.length) {
    filterArray.push(`category IN [${filters.category.map(c => `"${c}"`).join(', ')}]`);
  }
  if (filters?.subcategory?.length) {
    filterArray.push(`subcategory IN [${filters.subcategory.map(s => `"${s}"`).join(', ')}]`);
  }
  if (filters?.ihmStatus?.length) {
    filterArray.push(`ihmStatus IN [${filters.ihmStatus.map(s => `"${s}"`).join(', ')}]`);
  }

  return index.search(query, {
    limit: options?.limit || 20,
    offset: options?.offset || 0,
    filter: filterArray.length > 0 ? filterArray.join(' AND ') : undefined,
    facets: options?.facets || ['category', 'subcategory', 'ihmStatus', 'unit'],
    attributesToHighlight: ['name', 'description'],
    highlightPreTag: '<mark>',
    highlightPostTag: '</mark>',
  });
}

// IMPA code specific search
export async function searchByImpaCode(code: string): Promise<ProductSearchResult[]> {
  const index = client.index('products');

  // Exact match first
  const exactResult = await index.search(code, {
    filter: `impaCode = "${code}"`,
    limit: 1,
  });

  if (exactResult.hits.length > 0) {
    return exactResult.hits;
  }

  // Partial match
  return (await index.search(code, {
    filter: `impaCode CONTAINS "${code}"`,
    limit: 10,
  })).hits;
}
```

### Global Search Component

```tsx
// components/search/global-search/global-search.tsx
'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Command } from 'cmdk';
import { Search, X, Loader2 } from 'lucide-react';
import { useDebounce } from '@/hooks/use-debounce';
import { useSearchHistory } from '../hooks/use-search-history';
import { searchProducts, ProductSearchResult } from '@/lib/search/meilisearch-client';
import { cn } from '@/lib/utils';

export function GlobalSearch() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ProductSearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const debouncedQuery = useDebounce(query, 150);
  const { recentSearches, addSearch, clearHistory } = useSearchHistory();

  // Keyboard shortcut to open search
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen(prev => !prev);
      }
    };
    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);

  // Search when query changes
  useEffect(() => {
    if (!debouncedQuery || debouncedQuery.length < 2) {
      setResults([]);
      return;
    }

    const performSearch = async () => {
      setIsLoading(true);
      try {
        const response = await searchProducts(debouncedQuery, undefined, { limit: 8 });
        setResults(response.hits);
      } catch (error) {
        console.error('Search error:', error);
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    };

    performSearch();
  }, [debouncedQuery]);

  const handleSelect = useCallback((product: ProductSearchResult) => {
    addSearch(query);
    setOpen(false);
    setQuery('');
    router.push(`/catalog/products/${product.id}`);
  }, [query, addSearch, router]);

  const handleSearchSubmit = useCallback(() => {
    if (query) {
      addSearch(query);
      setOpen(false);
      router.push(`/catalog?q=${encodeURIComponent(query)}`);
      setQuery('');
    }
  }, [query, addSearch, router]);

  return (
    <>
      {/* Search Trigger Button */}
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground bg-muted rounded-lg hover:bg-accent transition-colors w-full max-w-sm"
      >
        <Search className="h-4 w-4" />
        <span className="flex-1 text-left">Search products...</span>
        <kbd className="hidden md:inline-flex h-5 items-center gap-1 rounded border bg-background px-1.5 text-xs text-muted-foreground">
          <span className="text-xs">⌘</span>K
        </kbd>
      </button>

      {/* Search Dialog */}
      <Command.Dialog
        open={open}
        onOpenChange={setOpen}
        label="Global Search"
        className="fixed inset-0 z-50"
      >
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm" onClick={() => setOpen(false)} />

        <div className="fixed left-1/2 top-[20%] z-50 w-full max-w-2xl -translate-x-1/2">
          <div className="bg-popover rounded-xl shadow-lg border overflow-hidden">
            {/* Search Input */}
            <div className="flex items-center border-b px-4">
              <Search className="h-4 w-4 text-muted-foreground" />
              <Command.Input
                ref={inputRef}
                value={query}
                onValueChange={setQuery}
                placeholder="Search by product name, IMPA code, or description..."
                className="flex-1 h-12 px-3 text-sm bg-transparent outline-none placeholder:text-muted-foreground"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !results.length) {
                    handleSearchSubmit();
                  }
                }}
              />
              {isLoading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
              {query && (
                <button onClick={() => setQuery('')} className="p-1 hover:bg-accent rounded">
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>

            {/* Results */}
            <Command.List className="max-h-[400px] overflow-y-auto p-2">
              <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
                {query.length < 2 ? 'Type at least 2 characters to search...' : 'No products found.'}
              </Command.Empty>

              {/* Recent Searches */}
              {!query && recentSearches.length > 0 && (
                <Command.Group heading="Recent Searches">
                  {recentSearches.map((search, i) => (
                    <Command.Item
                      key={i}
                      value={search}
                      onSelect={() => {
                        setQuery(search);
                        inputRef.current?.focus();
                      }}
                      className="flex items-center gap-2 px-3 py-2 text-sm rounded-md cursor-pointer hover:bg-accent"
                    >
                      <Search className="h-4 w-4 text-muted-foreground" />
                      {search}
                    </Command.Item>
                  ))}
                  <button
                    onClick={clearHistory}
                    className="w-full text-left px-3 py-2 text-xs text-muted-foreground hover:text-foreground"
                  >
                    Clear history
                  </button>
                </Command.Group>
              )}

              {/* Search Results */}
              {results.length > 0 && (
                <Command.Group heading="Products">
                  {results.map((product) => (
                    <Command.Item
                      key={product.id}
                      value={product.impaCode}
                      onSelect={() => handleSelect(product)}
                      className="flex items-start gap-3 px-3 py-2 rounded-md cursor-pointer hover:bg-accent"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs bg-primary/10 text-primary px-1.5 py-0.5 rounded">
                            {product.impaCode}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {product.category}
                          </span>
                        </div>
                        <p
                          className="text-sm font-medium truncate mt-1"
                          dangerouslySetInnerHTML={{
                            __html: product._formatted?.name || product.name
                          }}
                        />
                        <p
                          className="text-xs text-muted-foreground line-clamp-1"
                          dangerouslySetInnerHTML={{
                            __html: product._formatted?.description || product.description
                          }}
                        />
                      </div>
                    </Command.Item>
                  ))}
                </Command.Group>
              )}

              {/* View All Results */}
              {query && results.length > 0 && (
                <Command.Item
                  onSelect={handleSearchSubmit}
                  className="flex items-center justify-center gap-2 px-3 py-3 text-sm text-primary hover:bg-accent rounded-md cursor-pointer"
                >
                  View all results for "{query}"
                </Command.Item>
              )}
            </Command.List>
          </div>
        </div>
      </Command.Dialog>
    </>
  );
}
```

### Faceted Filters Component

```tsx
// components/search/catalog-search/faceted-filters.tsx
'use client';

import { useState } from 'react';
import { ChevronDown, X } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { cn } from '@/lib/utils';

interface FacetValue {
  value: string;
  count: number;
}

interface Facet {
  name: string;
  label: string;
  values: FacetValue[];
}

interface FacetedFiltersProps {
  facets: Facet[];
  selectedFilters: Record<string, string[]>;
  onFilterChange: (facetName: string, values: string[]) => void;
  onClearAll: () => void;
}

export function FacetedFilters({
  facets,
  selectedFilters,
  onFilterChange,
  onClearAll,
}: FacetedFiltersProps) {
  const totalSelected = Object.values(selectedFilters).flat().length;

  return (
    <div className="w-64 shrink-0">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">Filters</h3>
        {totalSelected > 0 && (
          <Button variant="ghost" size="sm" onClick={onClearAll}>
            Clear all ({totalSelected})
          </Button>
        )}
      </div>

      {/* Active Filters */}
      {totalSelected > 0 && (
        <div className="flex flex-wrap gap-1 mb-4">
          {Object.entries(selectedFilters).flatMap(([facetName, values]) =>
            values.map((value) => (
              <Badge
                key={`${facetName}-${value}`}
                variant="secondary"
                className="gap-1"
              >
                {value}
                <button
                  onClick={() =>
                    onFilterChange(
                      facetName,
                      values.filter((v) => v !== value)
                    )
                  }
                  className="ml-1 hover:text-destructive"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))
          )}
        </div>
      )}

      {/* Facet Groups */}
      <div className="space-y-2">
        {facets.map((facet) => (
          <FacetGroup
            key={facet.name}
            facet={facet}
            selected={selectedFilters[facet.name] || []}
            onChange={(values) => onFilterChange(facet.name, values)}
          />
        ))}
      </div>
    </div>
  );
}

function FacetGroup({
  facet,
  selected,
  onChange,
}: {
  facet: Facet;
  selected: string[];
  onChange: (values: string[]) => void;
}) {
  const [isOpen, setIsOpen] = useState(true);
  const [showAll, setShowAll] = useState(false);

  const displayValues = showAll ? facet.values : facet.values.slice(0, 5);
  const hasMore = facet.values.length > 5;

  const toggleValue = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter((v) => v !== value));
    } else {
      onChange([...selected, value]);
    }
  };

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger className="flex items-center justify-between w-full py-2 text-sm font-medium hover:text-primary">
        <span>
          {facet.label}
          {selected.length > 0 && (
            <span className="ml-2 text-xs text-muted-foreground">
              ({selected.length})
            </span>
          )}
        </span>
        <ChevronDown
          className={cn(
            'h-4 w-4 transition-transform',
            isOpen && 'rotate-180'
          )}
        />
      </CollapsibleTrigger>

      <CollapsibleContent>
        <ScrollArea className={cn('pr-4', facet.values.length > 8 && 'h-48')}>
          <div className="space-y-1 py-2">
            {displayValues.map((item) => (
              <label
                key={item.value}
                className="flex items-center gap-2 py-1 text-sm cursor-pointer hover:text-primary"
              >
                <Checkbox
                  checked={selected.includes(item.value)}
                  onCheckedChange={() => toggleValue(item.value)}
                />
                <span className="flex-1 truncate">{item.value}</span>
                <span className="text-xs text-muted-foreground">
                  {item.count}
                </span>
              </label>
            ))}
          </div>
        </ScrollArea>

        {hasMore && (
          <button
            onClick={() => setShowAll(!showAll)}
            className="text-xs text-primary hover:underline py-1"
          >
            {showAll ? 'Show less' : `Show ${facet.values.length - 5} more`}
          </button>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}
```

### Catalog Search Page

```tsx
// app/(buyer)/catalog/page.tsx
'use client';

import { useSearchParams, useRouter } from 'next/navigation';
import { useState, useEffect, useCallback } from 'react';
import { useDebounce } from '@/hooks/use-debounce';
import { searchProducts, SearchFilters, ProductSearchResult } from '@/lib/search/meilisearch-client';
import { FacetedFilters } from '@/components/search/catalog-search/faceted-filters';
import { ProductGrid } from '@/components/catalog/product-grid';
import { SearchInput } from '@/components/search/catalog-search/search-input';
import { Pagination } from '@/components/ui/pagination';
import { Skeleton } from '@/components/ui/skeleton';

const ITEMS_PER_PAGE = 24;

export default function CatalogPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const initialQuery = searchParams.get('q') || '';
  const initialPage = parseInt(searchParams.get('page') || '1', 10);

  const [query, setQuery] = useState(initialQuery);
  const [filters, setFilters] = useState<SearchFilters>({});
  const [page, setPage] = useState(initialPage);
  const [results, setResults] = useState<ProductSearchResult[]>([]);
  const [facets, setFacets] = useState<Record<string, Record<string, number>>>({});
  const [totalHits, setTotalHits] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  const debouncedQuery = useDebounce(query, 200);

  // Update URL when search changes
  const updateUrl = useCallback((q: string, p: number) => {
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (p > 1) params.set('page', p.toString());
    router.push(`/catalog?${params.toString()}`, { scroll: false });
  }, [router]);

  // Perform search
  useEffect(() => {
    const performSearch = async () => {
      setIsLoading(true);
      try {
        const response = await searchProducts(
          debouncedQuery,
          filters,
          {
            limit: ITEMS_PER_PAGE,
            offset: (page - 1) * ITEMS_PER_PAGE,
            facets: ['category', 'subcategory', 'ihmStatus', 'unit'],
          }
        );

        setResults(response.hits);
        setFacets(response.facetDistribution || {});
        setTotalHits(response.estimatedTotalHits || 0);
      } catch (error) {
        console.error('Search error:', error);
      } finally {
        setIsLoading(false);
      }
    };

    performSearch();
    updateUrl(debouncedQuery, page);
  }, [debouncedQuery, filters, page, updateUrl]);

  const handleFilterChange = (facetName: string, values: string[]) => {
    setFilters(prev => ({
      ...prev,
      [facetName]: values,
    }));
    setPage(1); // Reset to first page on filter change
  };

  const handleClearFilters = () => {
    setFilters({});
    setPage(1);
  };

  // Transform facets for FacetedFilters component
  const facetData = Object.entries(facets).map(([name, values]) => ({
    name,
    label: name.charAt(0).toUpperCase() + name.slice(1).replace(/([A-Z])/g, ' $1'),
    values: Object.entries(values)
      .map(([value, count]) => ({ value, count }))
      .sort((a, b) => b.count - a.count),
  }));

  const totalPages = Math.ceil(totalHits / ITEMS_PER_PAGE);

  return (
    <div className="container py-6">
      <h1 className="text-2xl font-bold mb-6">Product Catalog</h1>

      {/* Search Bar */}
      <SearchInput
        value={query}
        onChange={setQuery}
        placeholder="Search by IMPA code, product name, or description..."
        className="mb-6"
      />

      <div className="flex gap-6">
        {/* Filters Sidebar */}
        <FacetedFilters
          facets={facetData}
          selectedFilters={filters}
          onFilterChange={handleFilterChange}
          onClearAll={handleClearFilters}
        />

        {/* Results */}
        <div className="flex-1">
          {/* Results Header */}
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-muted-foreground">
              {isLoading ? (
                <Skeleton className="h-4 w-32" />
              ) : (
                `${totalHits.toLocaleString()} products found`
              )}
            </p>
            {/* Sort dropdown would go here */}
          </div>

          {/* Product Grid */}
          {isLoading ? (
            <ProductGridSkeleton count={ITEMS_PER_PAGE} />
          ) : (
            <ProductGrid products={results} />
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <Pagination
              currentPage={page}
              totalPages={totalPages}
              onPageChange={setPage}
              className="mt-6"
            />
          )}
        </div>
      </div>
    </div>
  );
}

function ProductGridSkeleton({ count }: { count: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="border rounded-lg p-4">
          <Skeleton className="h-4 w-16 mb-2" />
          <Skeleton className="h-5 w-full mb-2" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      ))}
    </div>
  );
}
```

### Mobile Search (React Native)

```tsx
// apps/mobile/components/search/catalog-search.tsx
import { useState, useCallback } from 'react';
import {
  View,
  TextInput,
  FlatList,
  TouchableOpacity,
  Text,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useDebounce } from '@/hooks/use-debounce';
import { useCatalogSearch } from '@/hooks/queries/use-catalog-search';
import { ProductListItem } from '@/components/catalog/product-list-item';

export function CatalogSearch() {
  const [query, setQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({});

  const debouncedQuery = useDebounce(query, 200);
  const { data, isLoading, fetchNextPage, hasNextPage } = useCatalogSearch(
    debouncedQuery,
    filters
  );

  const products = data?.pages.flatMap(page => page.hits) || [];

  const handleLoadMore = useCallback(() => {
    if (hasNextPage) {
      fetchNextPage();
    }
  }, [hasNextPage, fetchNextPage]);

  return (
    <View style={styles.container}>
      {/* Search Input */}
      <View style={styles.searchBar}>
        <Ionicons name="search" size={20} color="#666" style={styles.searchIcon} />
        <TextInput
          style={styles.input}
          value={query}
          onChangeText={setQuery}
          placeholder="Search IMPA code or product..."
          placeholderTextColor="#999"
          autoCorrect={false}
          returnKeyType="search"
        />
        {query.length > 0 && (
          <TouchableOpacity onPress={() => setQuery('')} style={styles.clearButton}>
            <Ionicons name="close-circle" size={20} color="#666" />
          </TouchableOpacity>
        )}
        <TouchableOpacity
          onPress={() => setShowFilters(!showFilters)}
          style={[styles.filterButton, showFilters && styles.filterButtonActive]}
        >
          <Ionicons name="options" size={20} color={showFilters ? '#fff' : '#666'} />
        </TouchableOpacity>
      </View>

      {/* Filter Pills (when active filters exist) */}
      {Object.keys(filters).length > 0 && (
        <View style={styles.filterPills}>
          {/* Active filter chips */}
        </View>
      )}

      {/* Results */}
      {isLoading && products.length === 0 ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#0369a1" />
        </View>
      ) : (
        <FlatList
          data={products}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <ProductListItem product={item} />}
          onEndReached={handleLoadMore}
          onEndReachedThreshold={0.5}
          ListEmptyComponent={
            query.length >= 2 ? (
              <View style={styles.emptyContainer}>
                <Ionicons name="search-outline" size={48} color="#ccc" />
                <Text style={styles.emptyText}>No products found</Text>
                <Text style={styles.emptySubtext}>Try a different search term</Text>
              </View>
            ) : (
              <View style={styles.emptyContainer}>
                <Text style={styles.emptyText}>Enter a search term</Text>
                <Text style={styles.emptySubtext}>Search by IMPA code or product name</Text>
              </View>
            )
          }
          ListFooterComponent={
            isLoading && products.length > 0 ? (
              <ActivityIndicator style={styles.footerLoader} />
            ) : null
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    backgroundColor: '#f5f5f5',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  searchIcon: {
    marginRight: 8,
  },
  input: {
    flex: 1,
    fontSize: 16,
    paddingVertical: 8,
  },
  clearButton: {
    padding: 4,
  },
  filterButton: {
    padding: 8,
    marginLeft: 8,
    borderRadius: 8,
    backgroundColor: '#e0e0e0',
  },
  filterButtonActive: {
    backgroundColor: '#0369a1',
  },
  filterPills: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: 8,
    gap: 8,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 100,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginTop: 16,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  footerLoader: {
    padding: 16,
  },
});
```

### Search Analytics Hook

```typescript
// hooks/use-search-analytics.ts
import { useCallback } from 'react';
import { useAnalytics } from '@/lib/analytics';

export function useSearchAnalytics() {
  const analytics = useAnalytics();

  const trackSearch = useCallback((query: string, resultsCount: number) => {
    analytics.track('catalog_search', {
      query,
      results_count: resultsCount,
      timestamp: new Date().toISOString(),
    });
  }, [analytics]);

  const trackSearchClick = useCallback((
    query: string,
    productId: string,
    position: number
  ) => {
    analytics.track('search_result_click', {
      query,
      product_id: productId,
      position,
      timestamp: new Date().toISOString(),
    });
  }, [analytics]);

  const trackFilterUsage = useCallback((
    facetName: string,
    values: string[]
  ) => {
    analytics.track('filter_applied', {
      facet: facetName,
      values,
      timestamp: new Date().toISOString(),
    });
  }, [analytics]);

  const trackNoResults = useCallback((query: string) => {
    analytics.track('search_no_results', {
      query,
      timestamp: new Date().toISOString(),
    });
  }, [analytics]);

  return {
    trackSearch,
    trackSearchClick,
    trackFilterUsage,
    trackNoResults,
  };
}
```

### Dependencies
- ADR-NF-003: Meilisearch Search Engine
- ADR-NF-002: pgvector for Semantic Search
- ADR-UI-002: Component Library (shadcn/ui)
- ADR-UI-008: Mobile Catalog Caching

### Migration Strategy
1. Set up Meilisearch index with product data
2. Configure searchable attributes and facets
3. Build GlobalSearch component
4. Implement FacetedFilters
5. Create catalog search page
6. Add mobile search components
7. Implement search analytics
8. Test typo-tolerance with maritime terms
9. Optimize for performance

---

## Operational Considerations

### Search Filters Specification

#### Available Filters by Search Context

| Context | Filter | Type | Values |
|---------|--------|------|--------|
| **Product Catalog** | Category | Multi-select | Dynamic from catalog |
| | Subcategory | Multi-select (cascading) | Based on category |
| | IHM Status | Multi-select | Compliant, Non-compliant, Unknown |
| | Unit | Multi-select | Each, Set, Meter, Kilogram, etc. |
| | Price Range | Range slider | Min-Max (when pricing available) |
| **RFQ Search** | Status | Multi-select | Draft, Published, Closed, Awarded |
| | Port | Autocomplete | Port database |
| | Date Range | Date picker | Created/Deadline |
| | Supplier Count | Range | Min-Max suppliers invited |
| **Order Search** | Status | Multi-select | Pending, Confirmed, Shipped, Delivered |
| | Supplier | Multi-select | Organization list |
| | Date Range | Date picker | Order date |
| | Total Amount | Range | Min-Max |

#### Filter Configuration

```typescript
// lib/search/filter-config.ts
export const catalogFilters: FilterConfig[] = [
  {
    id: 'category',
    label: 'Category',
    type: 'multi-select',
    attribute: 'category',
    operator: 'IN',
    collapsible: true,
    defaultExpanded: true,
    showCount: true,
    searchable: true,
    maxVisible: 10,
  },
  {
    id: 'ihmStatus',
    label: 'IHM Compliance',
    type: 'multi-select',
    attribute: 'ihmStatus',
    operator: 'IN',
    options: [
      { value: 'compliant', label: 'Compliant', color: 'green' },
      { value: 'non_compliant', label: 'Non-Compliant', color: 'red' },
      { value: 'unknown', label: 'Unknown', color: 'gray' },
    ],
  },
  {
    id: 'priceRange',
    label: 'Price Range',
    type: 'range',
    attribute: 'price',
    min: 0,
    max: 10000,
    step: 10,
    format: 'currency',
    requiresSupplier: true, // Only show when supplier selected
  },
];
```

### Sorting Options

#### Sort Configuration by Context

| Context | Sort Options | Default |
|---------|-------------|---------|
| **Product Search** | Relevance, Name A-Z, Name Z-A, IMPA Code | Relevance |
| **RFQ List** | Deadline (soonest), Created (newest), Created (oldest), Quotes received | Deadline (soonest) |
| **Order List** | Date (newest), Date (oldest), Total (high-low), Total (low-high), Status | Date (newest) |
| **Quote Comparison** | Price (low-high), Price (high-low), Delivery time, Supplier rating | Price (low-high) |

```typescript
// Meilisearch sort configuration
const sortOptions = {
  catalog: [
    { value: '_relevance', label: 'Most Relevant', meilisearch: null },
    { value: 'name:asc', label: 'Name A-Z', meilisearch: ['name:asc'] },
    { value: 'name:desc', label: 'Name Z-A', meilisearch: ['name:desc'] },
    { value: 'impaCode:asc', label: 'IMPA Code', meilisearch: ['impaCode:asc'] },
  ],
};
```

### Empty State Behavior

#### Empty State Scenarios

| Scenario | Display | Actions |
|----------|---------|---------|
| Initial (no query) | Recent searches + Popular categories | Quick links |
| No results (query) | "No results for X" + suggestions | Clear filters, Try similar, Contact support |
| No results (filters) | "No products match filters" | Clear filters button, Broaden suggestion |
| Error state | "Search unavailable" + retry | Retry button, Offline fallback |
| Offline | "Searching offline catalog" | Limited results indicator |

#### Empty State Component

```typescript
// components/search/empty-state.tsx
interface EmptyStateProps {
  type: 'initial' | 'no_results' | 'filtered' | 'error' | 'offline';
  query?: string;
  suggestions?: string[];
  onClearFilters?: () => void;
  onRetry?: () => void;
}

export function SearchEmptyState({
  type,
  query,
  suggestions,
  onClearFilters,
  onRetry,
}: EmptyStateProps) {
  const content = {
    initial: {
      icon: <Search className="h-12 w-12" />,
      title: 'Search our catalog',
      description: 'Find products by name, IMPA code, or description',
      action: null,
    },
    no_results: {
      icon: <SearchX className="h-12 w-12" />,
      title: `No results for "${query}"`,
      description: 'Try different keywords or check your spelling',
      action: suggestions?.length ? (
        <div className="mt-4">
          <p className="text-sm text-muted-foreground mb-2">Try searching for:</p>
          <div className="flex flex-wrap gap-2">
            {suggestions.map((s) => (
              <Button key={s} variant="outline" size="sm" onClick={() => setQuery(s)}>
                {s}
              </Button>
            ))}
          </div>
        </div>
      ) : null,
    },
    filtered: {
      icon: <Filter className="h-12 w-12" />,
      title: 'No products match your filters',
      description: 'Try removing some filters to see more results',
      action: (
        <Button onClick={onClearFilters} className="mt-4">
          Clear all filters
        </Button>
      ),
    },
    error: {
      icon: <AlertCircle className="h-12 w-12" />,
      title: 'Search is temporarily unavailable',
      description: 'Please try again in a moment',
      action: (
        <Button onClick={onRetry} className="mt-4">
          <RefreshCw className="h-4 w-4 mr-2" />
          Try again
        </Button>
      ),
    },
    offline: {
      icon: <CloudOff className="h-12 w-12" />,
      title: 'Searching offline catalog',
      description: 'Some products may not be available',
      action: null,
    },
  };

  const { icon, title, description, action } = content[type];

  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="text-muted-foreground mb-4">{icon}</div>
      <h3 className="text-lg font-medium">{title}</h3>
      <p className="text-sm text-muted-foreground mt-1 max-w-sm">{description}</p>
      {action}
    </div>
  );
}
```

### Relevance Tuning

#### Meilisearch Ranking Configuration

```typescript
// Ranking rules (in order of priority)
const rankingRules = [
  'words',           // Number of matching terms
  'typo',            // Number of typos
  'proximity',       // Distance between matching terms
  'attribute',       // Attribute importance
  'sort',            // User-selected sort
  'exactness',       // Exact vs prefix match
];

// Searchable attributes (in order of importance)
const searchableAttributes = [
  'impaCode',        // Highest priority - exact code match
  'name',            // Product name
  'synonyms',        // Alternative names
  'description',     // Full description
  'specifications',  // Technical specs
  'category',        // Category name
];

// Typo tolerance settings
const typoTolerance = {
  enabled: true,
  minWordSizeForTypos: {
    oneTypo: 4,      // Allow 1 typo for 4+ char words
    twoTypos: 8,     // Allow 2 typos for 8+ char words
  },
  disableOnAttributes: ['impaCode'], // Exact match for codes
};
```

#### Search Synonyms

```typescript
// Maritime industry synonyms
const synonyms = {
  'rope': ['line', 'cordage', 'hawser'],
  'paint': ['coating', 'primer', 'antifouling'],
  'valve': ['tap', 'cock', 'stopcock'],
  'pump': ['bilge pump', 'transfer pump'],
  'ppe': ['safety equipment', 'protective gear'],
  'fire extinguisher': ['extinguisher', 'fire fighting'],
};
```

### Metrics Tracking

#### Key Performance Indicators

| Metric | Definition | Target | Tracking |
|--------|-----------|--------|----------|
| **Search Success Rate** | Searches leading to product view | > 70% | Analytics |
| **Click-Through Rate (CTR)** | Clicks / Impressions for position | P1: >30%, P2-5: >15% | Analytics |
| **Zero Results Rate** | Searches with no results | < 5% | Dashboard alert |
| **Time to First Click** | Query → First result click | < 5 seconds | Analytics |
| **Search Refinement Rate** | Users who modify initial query | < 30% | Analytics |
| **Filter Usage Rate** | Searches using filters | Track by filter | Analytics |
| **Add to Cart from Search** | Search → Cart conversion | > 20% | Analytics |

#### Analytics Implementation

```typescript
// hooks/use-search-analytics.ts
export function useSearchAnalytics() {
  const posthog = usePostHog();

  const trackSearch = useCallback((data: SearchEvent) => {
    posthog.capture('catalog_search', {
      query: data.query,
      results_count: data.resultsCount,
      filters_applied: data.filters,
      sort_by: data.sortBy,
      search_type: data.isImpaCode ? 'impa_code' : 'text',
      response_time_ms: data.responseTime,
      is_offline: data.isOffline,
    });

    // Track zero results separately for alerting
    if (data.resultsCount === 0) {
      posthog.capture('search_zero_results', {
        query: data.query,
        filters_applied: data.filters,
      });
    }
  }, [posthog]);

  const trackResultClick = useCallback((data: ClickEvent) => {
    posthog.capture('search_result_click', {
      query: data.query,
      product_id: data.productId,
      product_impa: data.impaCode,
      position: data.position,
      results_count: data.totalResults,
    });
  }, [posthog]);

  const trackAddToCart = useCallback((data: CartEvent) => {
    posthog.capture('search_add_to_cart', {
      query: data.query,
      product_id: data.productId,
      position: data.searchPosition,
    });
  }, [posthog]);

  return { trackSearch, trackResultClick, trackAddToCart };
}
```

#### Zero Results Monitoring

```typescript
// lib/analytics/zero-results-monitor.ts
class ZeroResultsMonitor {
  private threshold = 10; // Alert after 10 zero-result queries for same term
  private timeWindow = 60 * 60 * 1000; // 1 hour

  async checkAndAlert(query: string): Promise<void> {
    const key = `zero_results:${query.toLowerCase()}`;
    const count = await redis.incr(key);
    await redis.expire(key, this.timeWindow / 1000);

    if (count === this.threshold) {
      await this.sendAlert({
        query,
        count,
        message: `Query "${query}" returned zero results ${count} times in the last hour`,
        action: 'Consider adding synonyms or checking catalog coverage',
      });
    }
  }
}
```

### Success Metrics Summary

| Metric | Measurement | Target | Alert Threshold |
|--------|-------------|--------|-----------------|
| Search latency (p95) | Server-side timing | < 100ms | > 200ms |
| Search success rate | Searches → clicks | > 70% | < 60% |
| Zero results rate | Daily average | < 5% | > 10% |
| CTR (position 1) | Clicks / Impressions | > 30% | < 20% |
| Filter adoption | Searches with filters | > 40% | < 25% |
| Mobile search success | Mobile-specific | > 65% | < 55% |

### Open Questions - Resolved

- **Q:** What are the success metrics for search UX?
  - **A:** We track the following primary success metrics:
    1. **Search Success Rate (target: >70%)**: Percentage of searches that result in a product detail view or add-to-cart within 30 seconds
    2. **Zero Results Rate (target: <5%)**: Percentage of searches returning no results; monitored for alerting and synonym tuning
    3. **Click-Through Rate by Position**: CTR for position 1 should be >30%; used to validate ranking relevance
    4. **Time to First Click (target: <5s)**: Measures search result quality and UI responsiveness
    5. **Search-to-Cart Conversion (target: >20%)**: End-to-end funnel metric from search to cart
    6. **Filter Usage Rate**: Tracks which filters are valuable; informs UX improvements

    Metrics are tracked via PostHog analytics with daily dashboards and weekly reports. Zero results and latency spikes trigger automated Slack alerts.

---

## References
- [Meilisearch Documentation](https://docs.meilisearch.com/)
- [cmdk (Command Menu)](https://cmdk.paco.me/)
- [Search UI Best Practices](https://www.nngroup.com/articles/search-visible-and-simple/)
- [Faceted Search Guidelines](https://baymard.com/blog/faceted-search)
