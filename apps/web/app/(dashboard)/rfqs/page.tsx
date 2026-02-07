import { ComingSoon } from "@/components/common/coming-soon";

export default function RfqsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">RFQs</h1>
        <p className="text-muted-foreground">
          Request for Quotes management
        </p>
      </div>
      <ComingSoon
        title="Request for Quotes"
        description="Create and manage RFQs from your fleet vessels. Compare supplier quotes and make purchasing decisions."
      />
    </div>
  );
}
