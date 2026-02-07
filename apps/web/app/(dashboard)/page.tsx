"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { listProducts, listCategories } from "@/lib/api/products";
import { StatCard } from "@/components/dashboard/stat-card";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Package, FolderTree, Users, Anchor, Search, Plus, Eye } from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();

  const { data: productData, isLoading: productsLoading } = useQuery({
    queryKey: ["products-count"],
    queryFn: () => listProducts({ limit: 0 }),
  });

  const { data: categoryData, isLoading: categoriesLoading } = useQuery({
    queryKey: ["categories-count"],
    queryFn: () => listCategories(),
  });

  const isLoading = productsLoading || categoriesLoading;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome to PortiQ Maritime Procurement Platform
        </p>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Total Products"
            value={productData?.total ?? "--"}
            icon={Package}
            description="In the catalog"
          />
          <StatCard
            title="Categories"
            value={categoryData?.length ?? "--"}
            icon={FolderTree}
            description="Product categories"
          />
          <StatCard
            title="Suppliers"
            value="--"
            icon={Users}
            description="Registered suppliers"
          />
          <StatCard
            title="Active Vessels"
            value="--"
            icon={Anchor}
            description="Fleet vessels"
          />
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        <Button onClick={() => router.push("/search")}>
          <Search className="mr-2 h-4 w-4" />
          Search Products
        </Button>
        <Button variant="outline" onClick={() => router.push("/products?action=create")}>
          <Plus className="mr-2 h-4 w-4" />
          Add Product
        </Button>
        <Button variant="outline" onClick={() => router.push("/suppliers")}>
          <Eye className="mr-2 h-4 w-4" />
          View Suppliers
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <RecentActivity />
      </div>
    </div>
  );
}
