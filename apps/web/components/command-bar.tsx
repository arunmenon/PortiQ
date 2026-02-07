"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import { useQuery } from "@tanstack/react-query";
import { Search, Package, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useDebounce } from "@/hooks/use-debounce";
import { getSuggestions } from "@/lib/api/products";
import { classifyIntent, type IntentType } from "@/lib/command-bar/intent-classifier";
import {
  getNavigationCommands,
  getActionCommands,
  filterCommands,
} from "@/lib/command-bar/commands";

const INTENT_LABELS: Record<IntentType, string> = {
  search: "Search",
  navigation: "Go to",
  action: "Action",
  conversation: "Ask AI",
};

const INTENT_VARIANTS: Record<IntentType, "default" | "secondary" | "outline" | "destructive"> = {
  search: "secondary",
  navigation: "outline",
  action: "default",
  conversation: "default",
};

export function CommandBar() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const router = useRouter();
  const debouncedQuery = useDebounce(query, 250);
  const intent = useMemo(() => classifyIntent(query), [query]);

  const navigationCommands = useMemo(
    () => getNavigationCommands((path) => {
      router.push(path);
      setOpen(false);
    }),
    [router],
  );

  const actionCommands = useMemo(
    () => getActionCommands((path) => {
      router.push(path);
      setOpen(false);
    }),
    [router],
  );

  const filteredNavigation = useMemo(
    () => filterCommands(navigationCommands, query),
    [navigationCommands, query],
  );

  const filteredActions = useMemo(
    () => filterCommands(actionCommands, query),
    [actionCommands, query],
  );

  const { data: productResults, isLoading: isLoadingProducts } = useQuery({
    queryKey: ["command-bar-search", debouncedQuery],
    queryFn: () => getSuggestions(debouncedQuery, 5),
    enabled: debouncedQuery.length >= 2,
    staleTime: 30_000,
  });

  // Keyboard shortcut: Cmd+K / Ctrl+K
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        setOpen((prev) => !prev);
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleOpenChange = useCallback((nextOpen: boolean) => {
    setOpen(nextOpen);
    if (!nextOpen) {
      setQuery("");
    }
  }, []);

  const handleProductSelect = useCallback(
    (productId: string) => {
      router.push(`/products/${productId}`);
      setOpen(false);
    },
    [router],
  );

  const handleAskPortiQ = useCallback(() => {
    router.push(`/chat?q=${encodeURIComponent(query)}`);
    setOpen(false);
  }, [query, router]);

  const showProducts = debouncedQuery.length >= 2;
  const showAskPortiQ = intent === "conversation" && query.trim().length > 0;

  return (
    <Command.Dialog
      open={open}
      onOpenChange={handleOpenChange}
      label="Command bar"
      className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh] bg-black/50"
      filter={(value, search) => {
        if (value === "ask-portiq") return 1;
        if (value.toLowerCase().includes(search.toLowerCase())) return 1;
        return 0;
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) handleOpenChange(false);
      }}
    >
      <div className="w-full max-w-[640px] rounded-lg border bg-popover text-popover-foreground shadow-lg">
        <div className="flex items-center gap-2 border-b px-3">
          <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
          <Command.Input
            value={query}
            onValueChange={setQuery}
            placeholder="Search products, navigate, or ask PortiQ..."
          />
          {query.trim().length > 0 && (
            <Badge variant={INTENT_VARIANTS[intent]} className="shrink-0 text-[10px] px-1.5 py-0">
              {INTENT_LABELS[intent]}
            </Badge>
          )}
        </div>

        <Command.List>
          <Command.Empty>
            {query.trim().length === 0
              ? "Type to search products, navigate, or ask a question..."
              : "No results found. Try a different query."}
          </Command.Empty>

          {/* Product search results */}
          {showProducts && (
            <Command.Group heading="Products">
              {isLoadingProducts ? (
                <div className="px-2 py-1.5 space-y-2">
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                </div>
              ) : (
                productResults?.map((result) => (
                  <Command.Item
                    key={result.id}
                    value={`product-${result.impa_code}-${result.name}`}
                    onSelect={() => handleProductSelect(result.id)}
                  >
                    <Package className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span className="flex-1 truncate">{result.name}</span>
                    <Badge variant="outline" className="shrink-0 text-[10px] font-mono">
                      {result.impa_code}
                    </Badge>
                    {result.category_name && (
                      <span className="shrink-0 text-xs text-muted-foreground">
                        {result.category_name}
                      </span>
                    )}
                  </Command.Item>
                ))
              )}
            </Command.Group>
          )}

          {/* Navigation commands */}
          {filteredNavigation.length > 0 && (
            <Command.Group heading="Navigation">
              {filteredNavigation.map((cmd) => (
                <Command.Item
                  key={cmd.id}
                  value={cmd.id}
                  onSelect={cmd.onSelect}
                >
                  <cmd.icon className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="flex-1">{cmd.label}</span>
                  {cmd.shortcut && (
                    <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
                      {cmd.shortcut}
                    </kbd>
                  )}
                </Command.Item>
              ))}
            </Command.Group>
          )}

          {/* Quick actions */}
          {filteredActions.length > 0 && (
            <Command.Group heading="Quick Actions">
              {filteredActions.map((cmd) => (
                <Command.Item
                  key={cmd.id}
                  value={cmd.id}
                  onSelect={cmd.onSelect}
                >
                  <cmd.icon className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="flex-1">{cmd.label}</span>
                </Command.Item>
              ))}
            </Command.Group>
          )}

          {/* Ask PortiQ */}
          {showAskPortiQ && (
            <Command.Group heading="Ask PortiQ">
              <Command.Item
                value="ask-portiq"
                onSelect={handleAskPortiQ}
              >
                <Sparkles className="h-4 w-4 shrink-0 text-primary" />
                <span className="flex-1 truncate">
                  Ask: &ldquo;{query}&rdquo;
                </span>
                <span className="shrink-0 text-xs text-muted-foreground">AI Chat</span>
              </Command.Item>
            </Command.Group>
          )}
        </Command.List>
      </div>
    </Command.Dialog>
  );
}

/** Programmatically open the command bar by dispatching a Cmd+K event */
export function triggerCommandBar() {
  document.dispatchEvent(
    new KeyboardEvent("keydown", { key: "k", metaKey: true, bubbles: true }),
  );
}
