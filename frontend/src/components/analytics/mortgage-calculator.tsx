"use client";

import React, { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { calculateMortgage, ApiError } from "@/lib/api";
import { MortgageResult } from "@/lib/types";
import { Loader2, AlertCircle, RefreshCw, Calculator } from "lucide-react";

interface ErrorState {
  message: string;
  requestId?: string;
}

const extractErrorState = (err: unknown): ErrorState => {
  let message = "Unknown error";
  let requestId: string | undefined = undefined;

  if (err instanceof ApiError) {
    message = err.message;
    requestId = err.request_id;
  } else if (err instanceof Error) {
    message = err.message;
  } else {
    message = String(err);
  }

  return { message, requestId };
};

export function MortgageCalculator() {
  const [loading, setLoading] = useState(false);
  const [errorState, setErrorState] = useState<ErrorState | null>(null);
  const [result, setResult] = useState<MortgageResult | null>(null);
  const [lastFormData, setLastFormData] = useState<typeof formData | null>(null);

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
    setErrorState(null);
    setLastFormData(formData);

    try {
      const data = await calculateMortgage(formData);
      setResult(data);
    } catch (err: unknown) {
      setErrorState(extractErrorState(err));
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = async () => {
    if (!lastFormData || loading) return;
    setLoading(true);
    setErrorState(null);

    try {
      const data = await calculateMortgage(lastFormData);
      setResult(data);
    } catch (err: unknown) {
      setErrorState(extractErrorState(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid gap-6 md:grid-cols-2">
      {/* STATE 1: Empty state - guidance before calculation */}
      {!result && !errorState && !loading && (
        <div
          className="col-span-full md:col-span-2 rounded-lg border bg-muted/30 p-6 text-center"
          role="status"
          aria-live="polite"
        >
          <div className="flex justify-center mb-3">
            <div className="p-3 rounded-full bg-primary/10">
              <Calculator className="h-8 w-8 text-primary" aria-hidden="true" />
            </div>
          </div>
          <h3 className="text-lg font-semibold mb-2">Mortgage Calculator</h3>
          <p className="text-sm text-muted-foreground max-w-md mx-auto mb-3">
            Enter your property details below to estimate monthly payments, total interest, and complete loan breakdown.
          </p>
          <p className="text-xs text-muted-foreground">
            Adjust the default values and click Calculate to see your personalized mortgage analysis.
          </p>
        </div>
      )}

      {/* Calculator Form */}
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

            {/* STATE 3: Error state with request_id and retry */}
            {errorState && (
              <div
                className="flex flex-col items-start gap-3 rounded-lg border border-destructive/20 bg-destructive/10 p-4"
                role="alert"
                aria-live="assertive"
              >
                <div className="flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 text-destructive mt-0.5 shrink-0" aria-hidden="true" />
                  <div className="flex-1">
                    <p className="text-sm text-destructive font-medium">Calculation failed</p>
                    <p className="text-sm text-destructive/90 mt-1">{errorState.message}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 w-full">
                  {errorState.requestId && (
                    <p className="text-xs text-muted-foreground font-mono">
                      request_id={errorState.requestId}
                    </p>
                  )}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleRetry}
                    disabled={loading}
                    className="gap-2 ml-auto"
                  >
                    <RefreshCw className="h-3 w-3" />
                    Retry
                  </Button>
                </div>
              </div>
            )}
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
