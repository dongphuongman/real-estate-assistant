"use client";
import React, { useState } from "react";
import {
  calculateMortgage,
  comparePropertiesApi,
  priceAnalysisApi,
  locationAnalysisApi,
  valuationApi,
  legalCheckApi,
  enrichAddressApi,
  crmSyncContactApi,
} from "@/lib/api";

export default function ToolsPage() {
  return (
    <div className="container mx-auto p-6 space-y-8">
      <h1 className="text-2xl font-semibold">Tools</h1>
      <MortgageSection />
      <CompareSection />
      <PriceAnalysisSection />
      <LocationAnalysisSection />
      <hr className="my-4" />
      <ValuationSection />
      <LegalCheckSection />
      <EnrichAddressSection />
      <CrmSyncSection />
    </div>
  );
}

function MortgageSection() {
  const [propertyPrice, setPropertyPrice] = useState<string>("");
  const [downPaymentPercent, setDownPaymentPercent] = useState<string>("20");
  const [interestRate, setInterestRate] = useState<string>("6.5");
  const [loanYears, setLoanYears] = useState<string>("30");
  const [result, setResult] = useState<null | { monthly_payment: number }>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">Mortgage Calculator</h2>
      <div className="grid grid-cols-2 gap-2 my-2">
        <input
          className="border p-2"
          placeholder="Property price"
          value={propertyPrice}
          onChange={(e) => setPropertyPrice(e.target.value)}
        />
        <input
          className="border p-2"
          placeholder="Down payment %"
          value={downPaymentPercent}
          onChange={(e) => setDownPaymentPercent(e.target.value)}
        />
        <input
          className="border p-2"
          placeholder="Interest rate %"
          value={interestRate}
          onChange={(e) => setInterestRate(e.target.value)}
        />
        <input
          className="border p-2"
          placeholder="Loan years"
          value={loanYears}
          onChange={(e) => setLoanYears(e.target.value)}
        />
      </div>
      <button
        className="bg-black text-white px-3 py-2 rounded"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await calculateMortgage({
              property_price: parseFloat(propertyPrice),
              down_payment_percent: parseFloat(downPaymentPercent),
              interest_rate: parseFloat(interestRate),
              loan_years: parseInt(loanYears, 10),
            });
            setResult(res);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || "Calculation failed");
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? "Calculating..." : "Calculate"}
      </button>
      {error && <p className="text-red-600 mt-2">{error}</p>}
      {hint && <p className="text-sm text-gray-600 mt-1">{hint}</p>}
      {result && <p className="mt-2">Monthly payment: {result.monthly_payment.toFixed(2)}</p>}
    </section>
  );
}

function CompareSection() {
  const [ids, setIds] = useState<string>("");
  const [data, setData] = useState<Awaited<ReturnType<typeof comparePropertiesApi>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">Compare Properties</h2>
      <input
        className="border p-2 w-full my-2"
        placeholder="IDs comma-separated"
        value={ids}
        onChange={(e) => setIds(e.target.value)}
      />
      <button
        className="bg-black text-white px-3 py-2 rounded"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await comparePropertiesApi(ids.split(",").map((p) => p.trim()).filter(Boolean));
            setData(res);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || "Compare failed");
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? "Comparing..." : "Compare"}
      </button>
      {error && <p className="text-red-600 mt-2">{error}</p>}
      {hint && <p className="text-sm text-gray-600 mt-1">{hint}</p>}
      {data && (
        <div className="mt-2">
          <p>Count: {data.summary?.count}</p>
          <p>Min price: {data.summary?.min_price ?? "-"}</p>
          <p>Max price: {data.summary?.max_price ?? "-"}</p>
          <p>Diff: {data.summary?.price_difference ?? "-"}</p>
        </div>
      )}
    </section>
  );
}

function PriceAnalysisSection() {
  const [query, setQuery] = useState<string>("");
  const [data, setData] = useState<Awaited<ReturnType<typeof priceAnalysisApi>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">Price Analysis</h2>
      <input
        className="border p-2 w-full my-2"
        placeholder="Query (e.g., city or type)"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <button
        className="bg-black text-white px-3 py-2 rounded"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await priceAnalysisApi(query);
            setData(res);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || "Analysis failed");
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? "Analyzing..." : "Analyze"}
      </button>
      {error && <p className="text-red-600 mt-2">{error}</p>}
      {hint && <p className="text-sm text-gray-600 mt-1">{hint}</p>}
      {data && (
        <div className="mt-2">
          <p>Count: {data.count}</p>
          <p>Average price: {data.average_price ?? "-"}</p>
          <p>Median price: {data.median_price ?? "-"}</p>
        </div>
      )}
    </section>
  );
}

function LocationAnalysisSection() {
  const [pid, setPid] = useState<string>("");
  const [data, setData] = useState<Awaited<ReturnType<typeof locationAnalysisApi>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">Location Analysis</h2>
      <input
        className="border p-2 w-full my-2"
        placeholder="Property ID"
        value={pid}
        onChange={(e) => setPid(e.target.value)}
      />
      <button
        className="bg-black text-white px-3 py-2 rounded"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await locationAnalysisApi(pid);
            setData(res);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || "Location analysis failed");
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? "Analyzing..." : "Analyze"}
      </button>
      {error && <p className="text-red-600 mt-2">{error}</p>}
      {hint && <p className="text-sm text-gray-600 mt-1">{hint}</p>}
      {data && (
        <div className="mt-2">
          <p>City: {data.city ?? "-"}</p>
          <p>Neighborhood: {data.neighborhood ?? "-"}</p>
          <p>Lat/Lon: {data.lat ?? "-"}, {data.lon ?? "-"}</p>
        </div>
      )}
    </section>
  );
}

function ValuationSection() {
  const [pid, setPid] = useState<string>("");
  const [value, setValue] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">Valuation (CE Stub)</h2>
      <input
        className="border p-2 w-full my-2"
        placeholder="Property ID"
        value={pid}
        onChange={(e) => setPid(e.target.value)}
      />
      <button
        className="bg-black text-white px-3 py-2 rounded"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await valuationApi(pid);
            setValue(res.estimated_value);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || "Valuation failed");
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? "Estimating..." : "Estimate"}
      </button>
      {error && <p className="text-red-600 mt-2">{error}</p>}
      {hint && <p className="text-sm text-gray-600 mt-1">{hint}</p>}
      {value !== null && <p className="mt-2">Estimated value: {value.toFixed(2)}</p>}
    </section>
  );
}

function LegalCheckSection() {
  const [text, setText] = useState<string>("");
  const [data, setData] = useState<Awaited<ReturnType<typeof legalCheckApi>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">Legal Check (CE Stub)</h2>
      <textarea
        className="border p-2 w-full my-2"
        placeholder="Contract text"
        rows={4}
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <button
        className="bg-black text-white px-3 py-2 rounded"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await legalCheckApi(text);
            setData(res);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || "Legal check failed");
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? "Analyzing..." : "Analyze"}
      </button>
      {error && <p className="text-red-600 mt-2">{error}</p>}
      {hint && <p className="text-sm text-gray-600 mt-1">{hint}</p>}
      {data && (
        <div className="mt-2">
          <p>Score: {data.score}</p>
          <p>Risks: {Array.isArray(data.risks) ? data.risks.length : 0}</p>
        </div>
      )}
    </section>
  );
}

function EnrichAddressSection() {
  const [address, setAddress] = useState<string>("");
  const [data, setData] = useState<Awaited<ReturnType<typeof enrichAddressApi>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">Data Enrichment (CE Stub)</h2>
      <input
        className="border p-2 w-full my-2"
        placeholder="Address"
        value={address}
        onChange={(e) => setAddress(e.target.value)}
      />
      <button
        className="bg-black text-white px-3 py-2 rounded"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await enrichAddressApi(address);
            setData(res);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || "Enrichment failed");
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? "Enriching..." : "Enrich"}
      </button>
      {error && <p className="text-red-600 mt-2">{error}</p>}
      {hint && <p className="text-sm text-gray-600 mt-1">{hint}</p>}
      {data && (
        <div className="mt-2">
          <p>Address: {data.address}</p>
          <pre className="bg-gray-100 p-2 rounded text-sm">{JSON.stringify(data.data, null, 2)}</pre>
        </div>
      )}
    </section>
  );
}

function CrmSyncSection() {
  const [name, setName] = useState<string>("");
  const [phone, setPhone] = useState<string>("");
  const [email, setEmail] = useState<string>("");
  const [id, setId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">CRM Sync Contact (CE Stub)</h2>
      <div className="grid grid-cols-3 gap-2 my-2">
        <input
          className="border p-2"
          placeholder="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          className="border p-2"
          placeholder="Phone"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
        <input
          className="border p-2"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>
      <button
        className="bg-black text-white px-3 py-2 rounded"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await crmSyncContactApi(name, phone || undefined, email || undefined);
            setId(res.id);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || "CRM sync failed");
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? "Syncing..." : "Sync"}
      </button>
      {error && <p className="text-red-600 mt-2">{error}</p>}
      {hint && <p className="text-sm text-gray-600 mt-1">{hint}</p>}
      {id && <p className="mt-2">Contact ID: {id}</p>}
    </section>
  );
}

function getToolHint(error: string): string | null {
  if (error.includes("Data enrichment disabled")) {
    return "Enable on the backend: set DATA_ENRICHMENT_ENABLED=true and restart the API.";
  }
  if (error.includes("CRM connector not configured")) {
    return "Configure on the backend: set CRM_WEBHOOK_URL and restart the API.";
  }
  if (error.includes("Valuation disabled")) {
    return "Configure on the backend: set VALUATION_MODE=simple and restart the API.";
  }
  if (error.includes("Legal check disabled")) {
    return "Configure on the backend: set LEGAL_CHECK_MODE=basic and restart the API.";
  }
  if (error.includes("Vector store unavailable")) {
    return "Load/initialize the vector store (Chroma) before running this tool.";
  }
  return null;
}
