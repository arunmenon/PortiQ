"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { FacetCount } from "@/lib/api/types";

function formatFacetName(name: string): string {
  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

interface FacetSectionProps {
  name: string;
  values: FacetCount[];
  selected: string[];
  onToggle: (value: string) => void;
}

function FacetSection({ name, values, selected, onToggle }: FacetSectionProps) {
  const [expanded, setExpanded] = useState(true);

  if (values.length === 0) return null;

  return (
    <div>
      <button
        className="flex w-full items-center justify-between py-2 text-sm font-medium"
        onClick={() => setExpanded(!expanded)}
      >
        {formatFacetName(name)}
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        )}
      </button>
      {expanded && (
        <div className="space-y-1 pb-3">
          {values.map((facet) => {
            const isSelected = selected.includes(facet.value);
            return (
              <button
                key={facet.value}
                className={cn(
                  "flex w-full items-center justify-between rounded-md px-2 py-1.5 text-sm transition-colors",
                  isSelected
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
                onClick={() => onToggle(facet.value)}
              >
                <div className="flex items-center gap-2">
                  <div
                    className={cn(
                      "h-4 w-4 rounded border flex items-center justify-center",
                      isSelected ? "border-primary bg-primary" : "border-muted-foreground/30"
                    )}
                  >
                    {isSelected && (
                      <svg className="h-3 w-3 text-primary-foreground" viewBox="0 0 12 12" fill="none">
                        <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    )}
                  </div>
                  <span className="truncate">{facet.value || "(empty)"}</span>
                </div>
                <Badge variant="secondary" className="ml-2 text-xs">
                  {facet.count}
                </Badge>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

interface FacetSidebarProps {
  facets: Record<string, FacetCount[]>;
  selectedFacets: Record<string, string[]>;
  onFacetChange: (facet: string, value: string) => void;
}

export function FacetSidebar({ facets, selectedFacets, onFacetChange }: FacetSidebarProps) {
  const hasSelections = Object.values(selectedFacets).some((v) => v.length > 0);

  return (
    <Card className="w-64 flex-shrink-0">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">Filters</CardTitle>
          {hasSelections && (
            <Button
              variant="ghost"
              size="sm"
              className="h-auto p-0 text-xs text-muted-foreground"
              onClick={() => {
                Object.entries(selectedFacets).forEach(([facet, values]) => {
                  values.forEach((value) => onFacetChange(facet, value));
                });
              }}
            >
              Clear all
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {Object.entries(facets).map(([name, values]) => (
          <FacetSection
            key={name}
            name={name}
            values={values}
            selected={selectedFacets[name] || []}
            onToggle={(value) => onFacetChange(name, value)}
          />
        ))}
      </CardContent>
    </Card>
  );
}
