"use client";

import { useEffect, useState } from "react";
import { NotificationSettings } from "@/components/settings/notification-settings";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getModelsCatalog } from "@/lib/api";
import type { ModelProviderCatalog } from "@/lib/types";

function formatMoneyPer1m(value: number, currency: string): string {
  if (!Number.isFinite(value)) return "—";
  return `${currency} ${value.toFixed(2)}`;
}

function ModelCatalogComparison() {
  const [catalog, setCatalog] = useState<ModelProviderCatalog[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCatalog = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getModelsCatalog();
      setCatalog(data);
    } catch (err) {
      console.error("Failed to load model catalog:", err);
      setCatalog(null);
      setError("Failed to load model catalog. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCatalog();
  }, []);

  if (loading) {
    return <div className="p-4 text-center">Loading model catalog...</div>;
  }

  if (!catalog) {
    return (
      <div className="p-4 text-center text-red-500">
        {error || "Something went wrong."}
        <Button onClick={fetchCatalog} className="ml-4">
          Retry
        </Button>
      </div>
    );
  }

  if (catalog.length === 0) {
    return (
      <div className="rounded-lg border bg-card p-6 text-center text-sm text-muted-foreground">
        No models available.
      </div>
    );
  }

  return (
    <div className="grid gap-6">
      {catalog.map((provider) => (
        <Card key={provider.name}>
          <CardHeader>
            <CardTitle className="text-xl">{provider.display_name}</CardTitle>
            <CardDescription>
              <span className="mr-3">Provider: {provider.name}</span>
              <span className="mr-3">{provider.is_local ? "Local" : "Hosted"}</span>
              <span>{provider.requires_api_key ? "API key required" : "No API key required"}</span>
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="w-full overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground">
                    <th className="pb-2 pr-4 font-medium">Model</th>
                    <th className="pb-2 pr-4 font-medium">Context</th>
                    <th className="pb-2 pr-4 font-medium">Input / 1M</th>
                    <th className="pb-2 pr-4 font-medium">Output / 1M</th>
                    <th className="pb-2 pr-4 font-medium">Capabilities</th>
                  </tr>
                </thead>
                <tbody>
                  {provider.models.map((model) => (
                    <tr key={model.id} className="border-t">
                      <td className="py-3 pr-4 font-medium">
                        <div className="leading-tight">
                          <div>{model.display_name || model.id}</div>
                          <div className="text-xs text-muted-foreground">{model.id}</div>
                        </div>
                      </td>
                      <td className="py-3 pr-4">{model.context_window.toLocaleString()}</td>
                      <td className="py-3 pr-4">
                        {model.pricing
                          ? formatMoneyPer1m(model.pricing.input_price_per_1m, model.pricing.currency)
                          : "—"}
                      </td>
                      <td className="py-3 pr-4">
                        {model.pricing
                          ? formatMoneyPer1m(model.pricing.output_price_per_1m, model.pricing.currency)
                          : "—"}
                      </td>
                      <td className="py-3 pr-4">
                        {model.capabilities.length ? model.capabilities.join(", ") : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {provider.is_local ? (
              <div className="mt-4 space-y-3">
                <p className="text-xs text-muted-foreground">
                  Local models run on your machine. Token pricing is not applicable; costs depend on your hardware and runtime settings.
                </p>
                <div className="rounded-lg border bg-card p-4 text-sm">
                  <div className="font-medium">Local models & offline usage</div>
                  <div className="mt-1 text-muted-foreground">
                    {provider.runtime_available === false
                      ? "Local runtime not detected. Start your local runtime and ensure the API can reach it."
                      : provider.runtime_available === true
                        ? `Local runtime detected. Downloaded models: ${provider.available_models?.length ?? 0}.`
                        : "Local runtime status is unknown."}
                  </div>
                  <div className="mt-3 space-y-2 text-muted-foreground">
                    <div>
                      1. Install Ollama:{" "}
                      <a
                        className="underline underline-offset-4"
                        href="https://ollama.com/download"
                        target="_blank"
                        rel="noreferrer"
                      >
                        ollama.com/download
                      </a>
                    </div>
                    <div>2. Start Ollama, then download a model:</div>
                    <div className="rounded-md bg-muted px-3 py-2 font-mono text-xs text-foreground">
                      ollama pull llama3.3:8b
                    </div>
                    <div>
                      3. If the API runs in Docker, set <span className="font-mono">OLLAMA_BASE_URL</span> to{" "}
                      <span className="font-mono">http://host.docker.internal:11434</span>.
                    </div>
                  </div>
                  {provider.available_models?.length ? (
                    <div className="mt-3">
                      <div className="text-xs font-medium text-foreground">Downloaded models</div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {provider.available_models.join(", ")}
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            ) : provider.models.some((m) => !m.pricing) ? (
              <p className="mt-4 text-xs text-muted-foreground">
                Pricing may be unavailable for some hosted models.
              </p>
            ) : null}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export default function SettingsPage() {
  return (
    <div className="container py-10">
      <div className="flex flex-col space-y-4 mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account settings and notification preferences.
        </p>
      </div>
      
      <div className="grid gap-8">
        <section>
          <h2 className="text-lg font-semibold mb-4">Notifications</h2>
          <NotificationSettings />
        </section>

        <section>
          <h2 className="text-lg font-semibold mb-2">Models & Costs</h2>
          <p className="text-sm text-muted-foreground mb-4">
            Compare model context windows and token pricing across providers.
          </p>
          <ModelCatalogComparison />
        </section>
      </div>
    </div>
  );
}
