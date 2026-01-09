import { BarChart3 } from "lucide-react";

export default function AnalyticsPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-8rem)]">
      <div className="p-6 rounded-full bg-muted/50 mb-6">
        <BarChart3 className="h-12 w-12 text-muted-foreground" />
      </div>
      <h1 className="text-3xl font-bold tracking-tight mb-2">Market Analytics</h1>
      <p className="text-muted-foreground text-lg text-center max-w-[600px]">
        Detailed market insights, price trends, and investment metrics are coming soon.
      </p>
    </div>
  );
}
