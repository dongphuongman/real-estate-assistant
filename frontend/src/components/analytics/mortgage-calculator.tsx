"use client";

import React, { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { calculateMortgage } from "@/lib/api";
import { MortgageResult } from "@/lib/types";
import { Loader2 } from "lucide-react";

export function MortgageCalculator() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MortgageResult | null>(null);

  const [formData, setFormData] = useState({
    property_price: 500000,
    down_payment_percent: 20,
    interest_rate: 4.5,
    loan_years: 30,
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: parseFloat(value) || 0,
    }));
  };

  const handleCalculate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const data = await calculateMortgage(formData);
      setResult(data);
    } catch (err) {
      console.error("Mortgage calculation failed:", err);
      setError("Failed to calculate mortgage. Please check your inputs.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Mortgage Calculator</CardTitle>
          <CardDescription>
            Estimate your monthly payments and total costs.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCalculate} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="property_price">Property Price ($)</Label>
              <Input
                id="property_price"
                name="property_price"
                type="number"
                value={formData.property_price}
                onChange={handleChange}
                min="0"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="down_payment_percent">Down Payment (%)</Label>
              <Input
                id="down_payment_percent"
                name="down_payment_percent"
                type="number"
                value={formData.down_payment_percent}
                onChange={handleChange}
                min="0"
                max="100"
                step="0.1"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="interest_rate">Interest Rate (%)</Label>
              <Input
                id="interest_rate"
                name="interest_rate"
                type="number"
                value={formData.interest_rate}
                onChange={handleChange}
                min="0"
                step="0.01"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="loan_years">Loan Term (Years)</Label>
              <Input
                id="loan_years"
                name="loan_years"
                type="number"
                value={formData.loan_years}
                onChange={handleChange}
                min="1"
                max="50"
                required
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Calculate
            </Button>
            {error && <p className="text-sm text-red-500 mt-2">{error}</p>}
          </form>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>Results</CardTitle>
            <CardDescription>
              Breakdown of your estimated mortgage.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Monthly Payment</p>
                <p className="text-2xl font-bold">
                  ${result.monthly_payment.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Down Payment</p>
                <p className="text-xl font-semibold">
                  ${result.down_payment.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Interest</p>
                <p className="text-lg">
                  ${result.total_interest.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Cost</p>
                <p className="text-lg">
                  ${result.total_cost.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </p>
              </div>
            </div>

            <div className="border-t pt-4">
              <h4 className="text-sm font-medium mb-2">Monthly Breakdown</h4>
              <div className="space-y-1">
                {Object.entries(result.breakdown).map(([key, value]) => (
                  <div key={key} className="flex justify-between text-sm">
                    <span className="capitalize">{key.replace(/_/g, " ")}</span>
                    <span>${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
