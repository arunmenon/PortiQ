"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Search, PackageOpen, AlertTriangle } from "lucide-react";

interface InventoryItem {
  id: string;
  product_name: string;
  impa_code: string | null;
  sku: string | null;
  category_name: string | null;
  quantity_on_hand: number;
  quantity_reserved: number;
  quantity_available: number;
  reorder_level: number;
  unit_of_measure: string;
  updated_at: string;
}

interface InventoryListResponse {
  items: InventoryItem[];
  total: number;
  limit: number;
  offset: number;
}

const PAGE_SIZE = 25;

async function listInventory(params?: {
  search?: string;
  low_stock?: boolean;
  limit?: number;
  offset?: number;
}): Promise<InventoryListResponse> {
  return apiClient.get<InventoryListResponse>(
    "/api/v1/supplier/inventory",
    params as Record<string, string | number | boolean | undefined>,
  );
}

export default function SupplierInventoryPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [page, setPage] = useState(0);

  const { data, isLoading, error } = useQuery({
    queryKey: ["supplier-inventory", searchTerm, lowStockOnly, page],
    queryFn: () =>
      listInventory({
        search: searchTerm || undefined,
        low_stock: lowStockOnly || undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Inventory</h1>
        <p className="text-muted-foreground">
          Monitor stock levels and manage inventory
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by product name or IMPA code..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setPage(0);
            }}
            className="pl-9"
          />
        </div>
        <Button
          variant={lowStockOnly ? "default" : "outline"}
          onClick={() => {
            setLowStockOnly(!lowStockOnly);
            setPage(0);
          }}
        >
          <AlertTriangle className="mr-2 h-4 w-4" />
          Low Stock
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <PackageOpen className="mb-4 h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium">Failed to load inventory</p>
          <p className="text-sm text-muted-foreground">
            Please check your connection and try again.
          </p>
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Product</TableHead>
                  <TableHead>IMPA Code</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead className="text-right">On Hand</TableHead>
                  <TableHead className="text-right">Reserved</TableHead>
                  <TableHead className="text-right">Available</TableHead>
                  <TableHead className="text-right">Reorder Level</TableHead>
                  <TableHead>Unit</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((item) => {
                  const isLowStock =
                    item.quantity_available <= item.reorder_level;
                  return (
                    <TableRow key={item.id}>
                      <TableCell className="font-medium">
                        {item.product_name}
                      </TableCell>
                      <TableCell>
                        {item.impa_code ? (
                          <Badge
                            variant="secondary"
                            className="font-mono text-xs"
                          >
                            {item.impa_code}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {item.category_name || (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        {item.quantity_on_hand}
                      </TableCell>
                      <TableCell className="text-right">
                        {item.quantity_reserved}
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {item.quantity_available}
                      </TableCell>
                      <TableCell className="text-right">
                        {item.reorder_level}
                      </TableCell>
                      <TableCell>{item.unit_of_measure}</TableCell>
                      <TableCell>
                        {isLowStock ? (
                          <Badge className="bg-red-100 text-red-800" variant="secondary">
                            LOW STOCK
                          </Badge>
                        ) : (
                          <Badge className="bg-green-100 text-green-800" variant="secondary">
                            IN STOCK
                          </Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 0}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page + 1} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page + 1 >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      ) : (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <PackageOpen className="mb-4 h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium">No inventory items found</p>
          <p className="text-sm text-muted-foreground">
            {searchTerm || lowStockOnly
              ? "Try adjusting your filters."
              : "Add products to your catalog to start tracking inventory."}
          </p>
        </div>
      )}
    </div>
  );
}
