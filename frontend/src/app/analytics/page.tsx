import { BarChart3 } from "lucide-react";
import { MortgageCalculator } from "@/components/analytics/mortgage-calculator";

export default function AnalyticsPage() {
  return (
    <div className="container py-8 space-y-8">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Analytics & Tools</h1>
        <p className="text-muted-foreground text-lg">
          Market insights and financial tools to help you make informed decisions.
        </p>
      </div>

      <div className="grid gap-8">
        <section>
          <h2 className="text-2xl font-semibold mb-4 flex items-center gap-2">
            <BarChart3 className="h-6 w-6" />
            Mortgage Calculator
          </h2>
          <MortgageCalculator />
        </section>

        <section className="rounded-lg border bg-card p-8 text-center text-muted-foreground">
          <p>More analytics tools and market insights coming soon.</p>
        </section>
      </div>
    </div>
  );
}
