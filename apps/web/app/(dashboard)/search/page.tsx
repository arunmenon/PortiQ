"use client";

import { Suspense, useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams, useRouter } from "next/navigation";
import { searchProductsText, searchProductsFaceted } from "@/lib/api/products";
import { FacetSidebar } from "@/components/search/facet-sidebar";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Search as SearchIcon, LayoutList, Filter } from "lucide-react";

function SearchContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";
  const [inputValue, setInputValue] = useState(initialQuery);
  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [page, setPage] = useState(1);
  const [mode, setMode] = useState<"text" | "faceted">("text");
  const [selectedFacets, setSelectedFacets] = useState<Record<string, string[]>>({});

  const { data: textData, isLoading: textLoading } = useQuery({
    queryKey: ["search-text", searchQuery, page],
    queryFn: () =>
      searchProductsText({
        query: searchQuery,
        page,
        limit: 20,
      }),
    enabled: mode === "text" && searchQuery.length > 0,
  });

  const activeCategoryFacet = selectedFacets["category_name"]?.[0];
  const activeIhmFacet = selectedFacets["ihm_relevant"]?.[0];
  const activeHazmatFacet = selectedFacets["hazmat_class"]?.[0];

  const { data: facetedData, isLoading: facetedLoading } = useQuery({
    queryKey: ["search-faceted", searchQuery, page, activeCategoryFacet, activeIhmFacet, activeHazmatFacet],
    queryFn: () =>
      searchProductsFaceted({
        query: searchQuery,
        page,
        limit: 20,
        category_id: activeCategoryFacet || undefined,
        ihm_relevant: activeIhmFacet === "true" ? true : activeIhmFacet === "false" ? false : undefined,
        hazmat_class: activeHazmatFacet || undefined,
      }),
    enabled: mode === "faceted" && searchQuery.length > 0,
  });

  const data = mode === "text" ? textData : facetedData;
  const isLoading = mode === "text" ? textLoading : facetedLoading;

  function handleSearch() {
    const trimmed = inputValue.trim();
    if (trimmed) {
      setSearchQuery(trimmed);
      setPage(1);
      router.replace(`/search?q=${encodeURIComponent(trimmed)}`);
    }
  }

  const handleFacetChange = useCallback((facet: string, value: string) => {
    setSelectedFacets((prev) => {
      const current = prev[facet] || [];
      const next = current.includes(value)
        ? current.filter((v) => v !== value)
        : [...current, value];
      return { ...prev, [facet]: next };
    });
    setPage(1);
  }, []);

  const results = data?.results || [];
  const total = data?.total || 0;
  const totalPages = data?.total_pages || 0;
  const facets = mode === "faceted" && facetedData ? facetedData.facets : {};

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Search</h1>
        <p className="text-muted-foreground">
          Search across the maritime product catalog
        </p>
      </div>

      <div className="flex gap-2">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by product name, description, or IMPA code..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="pl-9"
          />
        </div>
        <Button onClick={handleSearch}>Search</Button>
        <div className="flex rounded-md border">
          <Button
            variant={mode === "text" ? "default" : "ghost"}
            size="sm"
            className="rounded-r-none"
            onClick={() => { setMode("text"); setPage(1); }}
          >
            <LayoutList className="mr-1.5 h-4 w-4" />
            Text
          </Button>
          <Button
            variant={mode === "faceted" ? "default" : "ghost"}
            size="sm"
            className="rounded-l-none"
            onClick={() => { setMode("faceted"); setPage(1); }}
          >
            <Filter className="mr-1.5 h-4 w-4" />
            Faceted
          </Button>
        </div>
      </div>

      <div className={mode === "faceted" && searchQuery ? "flex gap-6" : ""}>
        {mode === "faceted" && searchQuery && Object.keys(facets).length > 0 && (
          <FacetSidebar
            facets={facets}
            selectedFacets={selectedFacets}
            onFacetChange={handleFacetChange}
          />
        )}

        <div className="flex-1 space-y-3">
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-24 w-full" />
              ))}
            </div>
          ) : results.length > 0 ? (
            <>
              <p className="text-sm text-muted-foreground">
                {total} results for &quot;{data?.query}&quot;
              </p>
              {results.map((result) => (
                <Card key={result.id}>
                  <CardContent className="flex items-start gap-4 p-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm text-muted-foreground">
                          {result.impa_code}
                        </span>
                        {result.category_name && (
                          <Badge variant="secondary">{result.category_name}</Badge>
                        )}
                      </div>
                      <h3 className="mt-1 font-medium">{result.name}</h3>
                      {result.description && (
                        <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
                          {result.description}
                        </p>
                      )}
                      {result.highlight && (
                        <p
                          className="mt-1 text-sm text-muted-foreground"
                          dangerouslySetInnerHTML={{
                            __html: result.highlight.replace(
                              /<(?!\/?mark\b)[^>]*>/gi,
                              ""
                            ),
                          }}
                        />
                      )}
                    </div>
                    <div className="text-right">
                      <span className="text-sm font-medium text-primary">
                        {(result.score * 100).toFixed(0)}% match
                      </span>
                    </div>
                  </CardContent>
                </Card>
              ))}
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    Page {page} of {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              )}
            </>
          ) : searchQuery ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <SearchIcon className="mb-4 h-12 w-12 text-muted-foreground" />
              <p className="text-lg font-medium">No results found</p>
              <p className="text-sm text-muted-foreground">
                Try different search terms or browse categories.
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <SearchIcon className="mb-4 h-12 w-12 text-muted-foreground" />
              <p className="text-lg font-medium">Search the catalog</p>
              <p className="text-sm text-muted-foreground">
                Enter a query to search across products, descriptions, and IMPA
                codes.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense>
      <SearchContent />
    </Suspense>
  );
}
