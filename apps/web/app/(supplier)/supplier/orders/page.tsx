import { ComingSoon } from "@/components/common/coming-soon";

export default function SupplierOrdersPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Orders</h1>
        <p className="text-muted-foreground">
          Manage purchase orders and deliveries
        </p>
      </div>
      <ComingSoon
        title="Supplier Orders"
        description="Track awarded purchase orders, manage deliveries, and submit invoices."
      />
    </div>
  );
}
