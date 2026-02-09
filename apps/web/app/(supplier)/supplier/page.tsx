"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  FileText,
  Send,
  ShoppingCart,
  ArrowRight,
  Clock,
  TrendingUp,
} from "lucide-react";
import Link from "next/link";
import { listSupplierOpportunities } from "@/lib/api/supplier-portal";

export default function SupplierDashboard() {
  const { data: rfqData, isLoading } = useQuery({
    queryKey: ["supplier-opportunities-summary"],
    queryFn: () =>
      listSupplierOpportunities({ limit: 5 }),
  });

  const openOpportunities = rfqData?.total ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Supplier Dashboard</h1>
        <p className="text-muted-foreground">
          Your procurement activity overview
        </p>
      </div>

      {/* Stats cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Open RFQ Invitations
            </CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <p className="text-3xl font-bold">{openOpportunities}</p>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              Awaiting your response
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Active Quotes
            </CardTitle>
            <Send className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">--</p>
            <p className="text-xs text-muted-foreground mt-1">
              Quotes under evaluation
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Pending Orders
            </CardTitle>
            <ShoppingCart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">--</p>
            <p className="text-xs text-muted-foreground mt-1">
              Orders to fulfill
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Quick actions */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Card className="transition-shadow hover:shadow-md">
          <CardContent className="flex items-center justify-between p-6">
            <div className="flex items-center gap-4">
              <div className="rounded-lg bg-primary/10 p-3">
                <TrendingUp className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="font-semibold">View Opportunities</p>
                <p className="text-sm text-muted-foreground">
                  Browse open RFQs and submit quotes
                </p>
              </div>
            </div>
            <Button variant="ghost" size="icon" asChild>
              <Link href="/supplier/rfqs">
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card className="transition-shadow hover:shadow-md">
          <CardContent className="flex items-center justify-between p-6">
            <div className="flex items-center gap-4">
              <div className="rounded-lg bg-primary/10 p-3">
                <Clock className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="font-semibold">My Quotes</p>
                <p className="text-sm text-muted-foreground">
                  Track submitted quotes and their status
                </p>
              </div>
            </div>
            <Button variant="ghost" size="icon" asChild>
              <Link href="/supplier/rfqs">
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Recent activity */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent RFQ Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : rfqData && rfqData.items.length > 0 ? (
            <div className="space-y-3">
              {rfqData.items.map((rfq) => (
                <Link
                  key={rfq.id}
                  href={`/supplier/rfqs/${rfq.id}`}
                  className="flex items-center justify-between rounded-md border p-3 transition-colors hover:bg-accent"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">
                      {rfq.title}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {rfq.reference_number}
                      {rfq.delivery_port && ` | ${rfq.delivery_port}`}
                    </p>
                  </div>
                  <div className="ml-4 flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">
                      {rfq.line_items.length} items
                    </Badge>
                    <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center py-8 text-center">
              <FileText className="mb-3 h-10 w-10 text-muted-foreground" />
              <p className="text-sm font-medium">No recent activity</p>
              <p className="text-xs text-muted-foreground">
                New RFQ invitations will appear here
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
