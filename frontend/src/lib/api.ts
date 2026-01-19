import {
  ChatRequest,
  ChatResponse,
  ModelProviderCatalog,
  MortgageInput,
  MortgageResult,
  NotificationSettings,
  SearchRequest,
  SearchResponse,
  ExportFormat,
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
    const errorText = await response.text();
    const headers = (response as unknown as { headers?: { get?: (name: string) => string | null } }).headers;
    const requestId =
      headers && typeof headers.get === "function"
        ? headers.get("X-Request-ID") || undefined
        : undefined;
    const message = errorText || "API request failed";
    const composed = requestId ? `${message} (request_id=${requestId})` : message;
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

export async function calculateMortgage(input: MortgageInput): Promise<MortgageResult> {
  const response = await fetch(`${getApiUrl()}/tools/mortgage-calculator`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify(input),
  });
  return handleResponse<MortgageResult>(response);
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
  onChunk: (chunk: string) => void
): Promise<void> {
  const response = await fetch(`${getApiUrl()}/chat`, {
    method: "POST",
    headers: {
      ...buildHeaders(),
    },
    body: JSON.stringify({ ...request, stream: true }),
  });

  if (!response.ok || !response.body) {
    throw new Error("Failed to start stream");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    // Parse SSE format: "data: ...\n\n"
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

export async function exportPropertiesBySearch(
  search: SearchRequest,
  format: ExportFormat
): Promise<{ filename: string; blob: Blob }> {
  const response = await fetch(`${getApiUrl()}/export/properties`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({ format, search }),
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Export request failed");
  }
  const cd = response.headers.get("Content-Disposition") || "";
  let filename = `properties.${format}`;
  const match = cd.match(/filename="([^"]+)"/i);
  if (match && match[1]) {
    filename = match[1];
  }
  const blob = await response.blob();
  return { filename, blob };
}
