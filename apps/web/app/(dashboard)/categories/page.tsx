"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { FolderTree } from "lucide-react";
import { listCategories } from "@/lib/api/products";
import type { CategoryTreeNode } from "@/lib/api/types";

export default function CategoriesPage() {
  const { data, isLoading, error } = useQuery<CategoryTreeNode[]>({
    queryKey: ["categories"],
    queryFn: () => listCategories(),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Categories</h1>
        <p className="text-muted-foreground">
          Browse the maritime product category hierarchy
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <FolderTree className="mb-4 h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium">Failed to load categories</p>
          <p className="text-sm text-muted-foreground">
            Please check your connection and try again.
          </p>
        </div>
      ) : data && data.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {data.map((category) => (
            <Card key={category.id}>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">{category.name}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex gap-2">
                  <Badge variant="secondary">
                    {category.product_count} products
                  </Badge>
                  {category.children_count > 0 && (
                    <Badge variant="outline">
                      {category.children_count} subcategories
                    </Badge>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <FolderTree className="mb-4 h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium">No categories found</p>
          <p className="text-sm text-muted-foreground">
            Categories will appear here once they are created.
          </p>
        </div>
      )}
    </div>
  );
}
