import {
  ChatRequest,
  ChatResponse,
  ModelProviderCatalog,
  ModelPreferences,
  MortgageInput,
  MortgageResult,
  NotificationSettings,
  SearchRequest,
  SearchResponse,
  ExportFormat,
  ExportPropertiesRequest,
  PromptTemplateApplyResponse,
  PromptTemplateInfo,
} from "./types";

function getApiUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
}

function getApiKey(): string | undefined {
  const key = process.env.NEXT_PUBLIC_API_KEY;
  return key && key.trim() ? key.trim() : undefined;
}

function getUserEmail(): string | undefined {
  if (typeof window === "undefined") return undefined;
  const email = window.localStorage.getItem("userEmail");
  return email && email.trim() ? email.trim() : undefined;
}

function buildHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  const apiKey = getApiKey();
  if (apiKey) headers["X-API-Key"] = apiKey;

  const userEmail = getUserEmail();
  if (userEmail) headers["X-User-Email"] = userEmail;

  return { ...headers, ...(extra || {}) };
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorText = await response.text().catch(() => "");
    const headers = (response as unknown as { headers?: { get?: (name: string) => string | null } }).headers;
    const requestId =
      headers && typeof headers.get === "function"
        ? headers.get("X-Request-ID") || undefined
        : undefined;
    let message = "API request failed";
    if (errorText) {
      try {
        const parsed: unknown = JSON.parse(errorText);
        if (parsed && typeof parsed === "object") {
          const detail = (parsed as { detail?: unknown }).detail;
          if (typeof detail === "string" && detail.trim()) {
            message = detail.trim();
          } else if (detail !== undefined) {
            message = JSON.stringify(detail);
          } else {
            message = errorText;
          }
        } else {
          message = errorText;
        }
      } catch {
        message = errorText;
      }
    }
    const statusPart = `status=${response.status}`;
    const composed = requestId ? `${message} (${statusPart}, request_id=${requestId})` : `${message} (${statusPart})`;
    throw new Error(composed);
  }
  return response.json();
}

export async function getNotificationSettings(): Promise<NotificationSettings> {
  const response = await fetch(`${getApiUrl()}/settings/notifications`, {
    method: "GET",
    headers: {
      ...buildHeaders(),
    },
  });
  return handleResponse<NotificationSettings>(response);
}

export async function updateNotificationSettings(settings: NotificationSettings): Promise<NotificationSettings> {
  const response = await fetch(`${getApiUrl()}/settings/notifications`, {
    method: "PUT",
    headers: {
      ...buildHeaders(),
    },
    body: JSON.stringify(settings),
  });
  return handleResponse<NotificationSettings>(response);
}

export async function getModelsCatalog(): Promise<ModelProviderCatalog[]> {
  const response = await fetch(`${getApiUrl()}/settings/models`, {
    method: "GET",
    headers: {
      ...buildHeaders(),
    },
  });
  return handleResponse<ModelProviderCatalog[]>(response);
}

export async function getModelPreferences(): Promise<ModelPreferences> {
  const response = await fetch(`${getApiUrl()}/settings/model-preferences`, {
    method: "GET",
    headers: {
      ...buildHeaders(),
    },
  });
  return handleResponse<ModelPreferences>(response);
}

export async function updateModelPreferences(payload: Partial<ModelPreferences>): Promise<ModelPreferences> {
  const response = await fetch(`${getApiUrl()}/settings/model-preferences`, {
    method: "PUT",
    headers: {
      ...buildHeaders(),
    },
    body: JSON.stringify(payload),
  });
  return handleResponse<ModelPreferences>(response);
}

export async function calculateMortgage(input: MortgageInput): Promise<MortgageResult> {
  const response = await fetch(`${getApiUrl()}/tools/mortgage-calculator`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify(input),
  });
  return handleResponse<MortgageResult>(response);
}

export async function comparePropertiesApi(propertyIds: string[]) {
  const response = await fetch(`${getApiUrl()}/tools/compare-properties`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({ property_ids: propertyIds }),
  });
  return handleResponse<{
    properties: Array<{
      id?: string;
      price?: number;
      price_per_sqm?: number;
      city?: string;
      rooms?: number;
      bathrooms?: number;
      area_sqm?: number;
      year_built?: number;
      property_type?: string;
    }>;
    summary: { count: number; min_price?: number; max_price?: number; price_difference?: number };
  }>(response);
}

export async function priceAnalysisApi(query: string) {
  const response = await fetch(`${getApiUrl()}/tools/price-analysis`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({ query }),
  });
  return handleResponse<{
    query: string;
    count: number;
    average_price?: number;
    median_price?: number;
    min_price?: number;
    max_price?: number;
    average_price_per_sqm?: number;
    median_price_per_sqm?: number;
    distribution_by_type: Record<string, number>;
  }>(response);
}

export async function locationAnalysisApi(propertyId: string) {
  const response = await fetch(`${getApiUrl()}/tools/location-analysis`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({ property_id: propertyId }),
  });
  return handleResponse<{
    property_id: string;
    city?: string;
    neighborhood?: string;
    lat?: number;
    lon?: number;
  }>(response);
}

export async function valuationApi(propertyId: string) {
  const response = await fetch(`${getApiUrl()}/tools/valuation`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({ property_id: propertyId }),
  });
  return handleResponse<{ property_id: string; estimated_value: number }>(response);
}

export async function legalCheckApi(text: string) {
  const response = await fetch(`${getApiUrl()}/tools/legal-check`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({ text }),
  });
  return handleResponse<{ risks: Array<Record<string, unknown>>; score: number }>(response);
}

export async function enrichAddressApi(address: string) {
  const response = await fetch(`${getApiUrl()}/tools/enrich-address`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({ address }),
  });
  return handleResponse<{ address: string; data: Record<string, unknown> }>(response);
}

export async function listPromptTemplates(): Promise<PromptTemplateInfo[]> {
  const response = await fetch(`${getApiUrl()}/prompt-templates`, {
    method: "GET",
    headers: buildHeaders(),
  });
  return handleResponse<PromptTemplateInfo[]>(response);
}

export async function applyPromptTemplate(
  templateId: string,
  variables: Record<string, unknown>
): Promise<PromptTemplateApplyResponse> {
  const response = await fetch(`${getApiUrl()}/prompt-templates/apply`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({ template_id: templateId, variables }),
  });
  return handleResponse<PromptTemplateApplyResponse>(response);
}

export async function crmSyncContactApi(name: string, phone?: string, email?: string) {
  const response = await fetch(`${getApiUrl()}/tools/crm-sync-contact`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({ name, phone, email }),
  });
  return handleResponse<{ id: string }>(response);
}

export async function searchProperties(request: SearchRequest): Promise<SearchResponse> {
  const response = await fetch(`${getApiUrl()}/search`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify(request),
  });
  return handleResponse<SearchResponse>(response);
}

export async function chatMessage(request: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${getApiUrl()}/chat`, {
    method: "POST",
    headers: {
      ...buildHeaders(),
    },
    body: JSON.stringify(request),
  });
  return handleResponse<ChatResponse>(response);
}

export async function streamChatMessage(
  request: ChatRequest,
  onChunk: (chunk: string) => void,
  onStart?: (meta: { requestId?: string }) => void
): Promise<void> {
  const response = await fetch(`${getApiUrl()}/chat`, {
    method: "POST",
    headers: {
      ...buildHeaders(),
    },
    body: JSON.stringify({ ...request, stream: true }),
  });

  if (!response.ok || !response.body) {
    const errorText = await response.text().catch(() => "");
    const headers = (response as unknown as { headers?: { get?: (name: string) => string | null } }).headers;
    const requestId =
      headers && typeof headers.get === "function" ? headers.get("X-Request-ID") || undefined : undefined;
    const message = errorText || "Failed to start stream";
    const composed = requestId ? `${message} (request_id=${requestId})` : message;
    throw new Error(composed);
  }

  const requestId = response.headers.get("X-Request-ID") || undefined;
  if (onStart) {
    onStart({ requestId });
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split("\n\n");
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6);
        if (data === "[DONE]") return;
        onChunk(data);
      }
    }
  }
}

async function exportProperties(
  request: ExportPropertiesRequest
): Promise<{ filename: string; blob: Blob }> {
  const response = await fetch(`${getApiUrl()}/export/properties`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const errorText = await response.text().catch(() => "");
    throw new Error(errorText || "Export request failed");
  }
  const cd = response.headers.get("Content-Disposition") || "";
  let filename = `properties.${request.format}`;
  const match = cd.match(/filename="([^"]+)"/i);
  if (match && match[1]) {
    filename = match[1];
  }
  const blob = await response.blob();
  return { filename, blob };
}

export async function exportPropertiesBySearch(
  search: SearchRequest,
  format: ExportFormat,
  options?: Pick<ExportPropertiesRequest, "columns" | "include_header" | "csv_delimiter" | "csv_decimal">
): Promise<{ filename: string; blob: Blob }> {
  return exportProperties({ format, search, ...(options || {}) });
}

export async function exportPropertiesByIds(
  propertyIds: string[],
  format: ExportFormat,
  options?: Pick<ExportPropertiesRequest, "columns" | "include_header" | "csv_delimiter" | "csv_decimal">
): Promise<{ filename: string; blob: Blob }> {
  return exportProperties({ format, property_ids: propertyIds, ...(options || {}) });
}
