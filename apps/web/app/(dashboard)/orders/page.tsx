import { ComingSoon } from "@/components/common/coming-soon";

export default function OrdersPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Orders</h1>
        <p className="text-muted-foreground">
          Purchase order management
        </p>
      </div>
      <ComingSoon
        title="Orders"
        description="Track purchase orders, deliveries, and invoices across your fleet."
      />
    </div>
  );
}
