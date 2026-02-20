import {
  ChatRequest,
  ChatResponse,
  Collection,
  CollectionCreate,
  CollectionListResponse,
  CollectionUpdate,
  ExcelSheetsRequest,
  ExcelSheetsResponse,
  Favorite,
  FavoriteCheckResponse,
  FavoriteCreate,
  FavoriteListResponse,
  FavoriteUpdate,
  IngestRequest,
  IngestResponse,
  InvestmentAnalysisInput,
  InvestmentAnalysisResult,
  MarketIndicators,
  MarketTrends,
  ModelProviderCatalog,
  ModelPreferences,
  ModelRuntimeTestResponse,
  MortgageInput,
  MortgageResult,
  TCOInput,
  TCOResult,
  NeighborhoodQualityInput,
  NeighborhoodQualityResult,
  NotificationSettings,
  PortalFiltersRequest,
  PortalIngestResponse,
  PortalAdaptersResponse,
  PriceHistory,
  RagQaRequest,
  RagQaResponse,
  RagResetResponse,
  RagUploadResponse,
  SavedSearch,
  SavedSearchCreate,
  SavedSearchListResponse,
  SavedSearchUpdate,
  SearchRequest,
  SearchResponse,
  ExportFormat,
  ExportPropertiesRequest,
  PromptTemplateApplyResponse,
  PromptTemplateInfo,
} from './types';

function getApiUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || '/api/v1';
}

function getUserEmail(): string | undefined {
  if (typeof window === 'undefined') return undefined;
  const email = window.localStorage.getItem('userEmail');
  return email && email.trim() ? email.trim() : undefined;
}

function buildAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};

  const userEmail = getUserEmail();
  if (userEmail) headers['X-User-Email'] = userEmail;

  return headers;
}

function buildHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  return { ...headers, ...buildAuthHeaders(), ...(extra || {}) };
}

function buildMultipartHeaders(extra?: Record<string, string>): Record<string, string> {
  return { ...buildAuthHeaders(), ...(extra || {}) };
}

/**
 * Error category for classification and handling.
 */
export type ApiErrorCategory =
  | 'network' // Connection failed, offline, DNS issues
  | 'timeout' // Request timed out
  | 'auth' // 401/403 authentication/authorization errors
  | 'validation' // 400/422 client-side validation errors
  | 'not_found' // 404 resource not found
  | 'rate_limit' // 429 too many requests
  | 'server' // 500+ server-side errors
  | 'unknown'; // Unclassified errors

/**
 * Custom error class for API errors that includes request_id for correlation
 * and error categorization for better handling strategies.
 *
 * @example
 * ```ts
 * try {
 *   await searchProperties({ query: "test" });
 * } catch (e) {
 *   if (e instanceof ApiError) {
 *     if (e.isRetryable) {
 *       // Implement retry logic
 *     }
 *     if (e.category === "auth") {
 *       // Redirect to login
 *     }
 *   }
 * }
 * ```
 */
export class ApiError extends Error {
  public readonly category: ApiErrorCategory;
  public readonly isRetryable: boolean;

  constructor(
    message: string,
    public readonly status: number,
    public readonly request_id?: string,
    category?: ApiErrorCategory
  ) {
    super(message);
    this.name = 'ApiError';

    // Determine category if not provided
    this.category = category ?? ApiError.categorizeStatus(status);

    // Determine if error is retryable
    this.isRetryable = ApiError.isRetryableCategory(this.category, status);
  }

  /**
   * Categorize error based on HTTP status code.
   */
  static categorizeStatus(status: number): ApiErrorCategory {
    if (status === 0) return 'network';
    if (status === 401 || status === 403) return 'auth';
    if (status === 404) return 'not_found';
    if (status === 408 || status === 504) return 'timeout';
    if (status === 429) return 'rate_limit';
    if (status === 400 || status === 422) return 'validation';
    if (status >= 500) return 'server';
    return 'unknown';
  }

  /**
   * Determine if an error category is generally retryable.
   * Network errors, timeouts, rate limits, and some server errors may be retried.
   */
  static isRetryableCategory(category: ApiErrorCategory, status: number): boolean {
    switch (category) {
      case 'network':
      case 'timeout':
      case 'rate_limit':
        return true;
      case 'server':
        // 503 Service Unavailable and 502 Bad Gateway are often transient
        return status === 502 || status === 503;
      default:
        return false;
    }
  }

  /**
   * Create a network error (for fetch failures, offline, etc.)
   */
  static networkError(originalError?: Error): ApiError {
    const message = originalError?.message || 'Network request failed. Check your connection.';
    const error = new ApiError(message, 0, undefined, 'network');
    if (originalError) {
      error.cause = originalError;
    }
    return error;
  }

  /**
   * Create a timeout error.
   */
  static timeoutError(request_id?: string): ApiError {
    return new ApiError('Request timed out. Please try again.', 408, request_id, 'timeout');
  }
}

/**
 * Safely perform a fetch request with network error handling.
 * Wraps fetch to convert network failures into ApiError.
 */
async function safeFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (error) {
    // Network errors (offline, DNS, CORS, etc.)
    throw ApiError.networkError(error instanceof Error ? error : undefined);
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorText = await response.text().catch(() => '');
    const headers = (response as unknown as { headers?: { get?: (name: string) => string | null } })
      .headers;
    const requestId =
      headers && typeof headers.get === 'function'
        ? headers.get('X-Request-ID') || undefined
        : undefined;
    let message = 'API request failed';
    if (errorText) {
      try {
        const parsed: unknown = JSON.parse(errorText);
        if (parsed && typeof parsed === 'object') {
          const detail = (parsed as { detail?: unknown }).detail;
          if (typeof detail === 'string' && detail.trim()) {
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
    throw new ApiError(message, response.status, requestId || undefined);
  }
  return response.json();
}

export async function getNotificationSettings(): Promise<NotificationSettings> {
  const response = await safeFetch(`${getApiUrl()}/settings/notifications`, {
    method: 'GET',
    headers: {
      ...buildHeaders(),
    },
  });
  return handleResponse<NotificationSettings>(response);
}

export async function updateNotificationSettings(
  settings: NotificationSettings
): Promise<NotificationSettings> {
  const response = await fetch(`${getApiUrl()}/settings/notifications`, {
    method: 'PUT',
    headers: {
      ...buildHeaders(),
    },
    body: JSON.stringify(settings),
  });
  return handleResponse<NotificationSettings>(response);
}

export async function getModelsCatalog(): Promise<ModelProviderCatalog[]> {
  const response = await fetch(`${getApiUrl()}/settings/models`, {
    method: 'GET',
    headers: {
      ...buildHeaders(),
    },
  });
  return handleResponse<ModelProviderCatalog[]>(response);
}

export async function testModelRuntime(provider: string): Promise<ModelRuntimeTestResponse> {
  const response = await fetch(
    `${getApiUrl()}/settings/test-runtime?provider=${encodeURIComponent(provider)}`,
    {
      method: 'GET',
      headers: {
        ...buildHeaders(),
      },
    }
  );
  return handleResponse<ModelRuntimeTestResponse>(response);
}

export async function getModelPreferences(): Promise<ModelPreferences> {
  const response = await fetch(`${getApiUrl()}/settings/model-preferences`, {
    method: 'GET',
    headers: {
      ...buildHeaders(),
    },
  });
  return handleResponse<ModelPreferences>(response);
}

export async function updateModelPreferences(
  payload: Partial<ModelPreferences>
): Promise<ModelPreferences> {
  const response = await fetch(`${getApiUrl()}/settings/model-preferences`, {
    method: 'PUT',
    headers: {
      ...buildHeaders(),
    },
    body: JSON.stringify(payload),
  });
  return handleResponse<ModelPreferences>(response);
}

export async function calculateMortgage(input: MortgageInput): Promise<MortgageResult> {
  const response = await fetch(`${getApiUrl()}/tools/mortgage-calculator`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(input),
  });
  return handleResponse<MortgageResult>(response);
}

export async function calculateTCO(input: TCOInput): Promise<TCOResult> {
  const response = await fetch(`${getApiUrl()}/tools/tco-calculator`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(input),
  });
  return handleResponse<TCOResult>(response);
}

export async function calculateInvestment(
  input: InvestmentAnalysisInput
): Promise<InvestmentAnalysisResult> {
  const response = await fetch(`${getApiUrl()}/tools/investment-analysis`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(input),
  });
  return handleResponse<InvestmentAnalysisResult>(response);
}

export async function neighborhoodQualityApi(
  input: NeighborhoodQualityInput
): Promise<NeighborhoodQualityResult> {
  const response = await fetch(`${getApiUrl()}/tools/neighborhood-quality`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(input),
  });
  return handleResponse<NeighborhoodQualityResult>(response);
}

/**
 * Convenience function to get neighborhood badge data for a property.
 * Can be used directly on property cards with property data.
 *
 * @param property - Property object with id, latitude, longitude, city, neighborhood
 * @returns Neighborhood quality result for badge display
 */
export async function getNeighborhoodBadge(property: {
  id?: string;
  latitude?: number;
  longitude?: number;
  city?: string;
  neighborhood?: string;
}): Promise<NeighborhoodQualityResult> {
  return neighborhoodQualityApi({
    property_id: property.id || 'unknown',
    latitude: property.latitude,
    longitude: property.longitude,
    city: property.city,
    neighborhood: property.neighborhood,
  });
}

export async function comparePropertiesApi(propertyIds: string[]) {
  const response = await fetch(`${getApiUrl()}/tools/compare-properties`, {
    method: 'POST',
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
    method: 'POST',
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
    method: 'POST',
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
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify({ property_id: propertyId }),
  });
  return handleResponse<{ property_id: string; estimated_value: number }>(response);
}

export async function legalCheckApi(text: string) {
  const response = await fetch(`${getApiUrl()}/tools/legal-check`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify({ text }),
  });
  return handleResponse<{ risks: Array<Record<string, unknown>>; score: number }>(response);
}

export async function enrichAddressApi(address: string) {
  const response = await fetch(`${getApiUrl()}/tools/enrich-address`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify({ address }),
  });
  return handleResponse<{ address: string; data: Record<string, unknown> }>(response);
}

export async function listPromptTemplates(): Promise<PromptTemplateInfo[]> {
  const response = await fetch(`${getApiUrl()}/prompt-templates`, {
    method: 'GET',
    headers: buildHeaders(),
  });
  return handleResponse<PromptTemplateInfo[]>(response);
}

export async function applyPromptTemplate(
  templateId: string,
  variables: Record<string, unknown>
): Promise<PromptTemplateApplyResponse> {
  const response = await fetch(`${getApiUrl()}/prompt-templates/apply`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify({ template_id: templateId, variables }),
  });
  return handleResponse<PromptTemplateApplyResponse>(response);
}

export async function uploadRagDocuments(files: File[]): Promise<RagUploadResponse> {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file, file.name);
  }

  const response = await fetch(`${getApiUrl()}/rag/upload`, {
    method: 'POST',
    headers: buildMultipartHeaders(),
    body: formData,
  });
  return handleResponse<RagUploadResponse>(response);
}

export async function resetRagKnowledge(): Promise<RagResetResponse> {
  const response = await fetch(`${getApiUrl()}/rag/reset`, {
    method: 'POST',
    headers: buildHeaders(),
  });
  return handleResponse<RagResetResponse>(response);
}

export async function ragQa(request: RagQaRequest): Promise<RagQaResponse> {
  const response = await fetch(`${getApiUrl()}/rag/qa`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(request),
  });
  return handleResponse<RagQaResponse>(response);
}

export async function crmSyncContactApi(name: string, phone?: string, email?: string) {
  const response = await fetch(`${getApiUrl()}/tools/crm-sync-contact`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify({ name, phone, email }),
  });
  return handleResponse<{ id: string }>(response);
}

export async function searchProperties(request: SearchRequest): Promise<SearchResponse> {
  const response = await safeFetch(`${getApiUrl()}/search`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(request),
  });
  return handleResponse<SearchResponse>(response);
}

export async function chatMessage(request: ChatRequest): Promise<ChatResponse> {
  const response = await safeFetch(`${getApiUrl()}/chat`, {
    method: 'POST',
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
  onStart?: (meta: { requestId?: string }) => void,
  onMeta?: (meta: {
    sources?: ChatResponse['sources'];
    sourcesTruncated?: boolean;
    sessionId?: string;
    intermediateSteps?: ChatResponse['intermediate_steps'];
  }) => void
): Promise<void> {
  const response = await safeFetch(`${getApiUrl()}/chat`, {
    method: 'POST',
    headers: {
      ...buildHeaders(),
    },
    body: JSON.stringify({ ...request, stream: true }),
  });

  if (!response.ok || !response.body) {
    const errorText = await response.text().catch(() => '');
    const headers = (response as unknown as { headers?: { get?: (name: string) => string | null } })
      .headers;
    const requestId =
      headers && typeof headers.get === 'function'
        ? headers.get('X-Request-ID') || undefined
        : undefined;
    const message = errorText || 'Failed to start stream';
    throw new ApiError(message, response.status, requestId || undefined);
  }

  const requestId = response.headers.get('X-Request-ID') || undefined;
  if (onStart) {
    onStart({ requestId });
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value);
    while (true) {
      const boundaryIndex = buffer.indexOf('\n\n');
      if (boundaryIndex === -1) break;
      const rawEvent = buffer.slice(0, boundaryIndex);
      buffer = buffer.slice(boundaryIndex + 2);

      let eventName = 'message';
      const dataLines: string[] = [];
      for (const rawLine of rawEvent.split('\n')) {
        const line = rawLine.trimEnd();
        if (!line) continue;
        if (line.startsWith('event:')) {
          eventName = line.slice(6).trim() || 'message';
          continue;
        }
        if (line.startsWith('data:')) {
          dataLines.push(line.slice(5).trimStart());
        }
      }

      const data = dataLines.join('\n');
      if (!data) continue;
      if (data === '[DONE]') return;

      let parsed: unknown = undefined;
      try {
        parsed = JSON.parse(data);
      } catch {
        parsed = undefined;
      }

      if (parsed && typeof parsed === 'object') {
        const maybeError = (parsed as { error?: unknown }).error;
        if (typeof maybeError === 'string' && maybeError.trim()) {
          throw new Error(maybeError);
        }

        if (eventName === 'meta') {
          if (onMeta) {
            const sources = (parsed as { sources?: unknown }).sources;
            const sourcesTruncated = (parsed as { sources_truncated?: unknown }).sources_truncated;
            const sessionId = (parsed as { session_id?: unknown }).session_id;
            const intermediateSteps = (parsed as { intermediate_steps?: unknown })
              .intermediate_steps;
            onMeta({
              sources: Array.isArray(sources) ? (sources as ChatResponse['sources']) : undefined,
              sourcesTruncated:
                typeof sourcesTruncated === 'boolean' ? sourcesTruncated : undefined,
              sessionId: typeof sessionId === 'string' && sessionId.trim() ? sessionId : undefined,
              intermediateSteps: Array.isArray(intermediateSteps)
                ? (intermediateSteps as ChatResponse['intermediate_steps'])
                : undefined,
            });
          }
          continue;
        }

        const content = (parsed as { content?: unknown }).content;
        if (typeof content === 'string') {
          onChunk(content);
          continue;
        }
      }

      onChunk(data);
    }
  }
}

async function exportProperties(
  request: ExportPropertiesRequest
): Promise<{ filename: string; blob: Blob }> {
  const response = await fetch(`${getApiUrl()}/export/properties`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const errorText = await response.text().catch(() => '');
    const requestId = response.headers.get('X-Request-ID') || undefined;
    const errorMsg = errorText || 'Export request failed';
    throw new ApiError(errorMsg, response.status, requestId || undefined);
  }
  const cd = response.headers.get('Content-Disposition') || '';
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
  options?: Pick<
    ExportPropertiesRequest,
    'columns' | 'include_header' | 'csv_delimiter' | 'csv_decimal'
  >
): Promise<{ filename: string; blob: Blob }> {
  return exportProperties({ format, search, ...(options || {}) });
}

export async function exportPropertiesByIds(
  propertyIds: string[],
  format: ExportFormat,
  options?: Pick<
    ExportPropertiesRequest,
    'columns' | 'include_header' | 'csv_delimiter' | 'csv_decimal'
  >
): Promise<{ filename: string; blob: Blob }> {
  return exportProperties({ format, property_ids: propertyIds, ...(options || {}) });
}

// Admin API functions for data ingestion
export async function ingestData(request: IngestRequest): Promise<IngestResponse> {
  const response = await fetch(`${getApiUrl()}/admin/ingest`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(request),
  });
  return handleResponse<IngestResponse>(response);
}

export async function getExcelSheets(request: ExcelSheetsRequest): Promise<ExcelSheetsResponse> {
  const response = await fetch(`${getApiUrl()}/admin/excel/sheets`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(request),
  });
  return handleResponse<ExcelSheetsResponse>(response);
}

// Portal/API Integration functions for TASK-006
export async function listPortals(): Promise<PortalAdaptersResponse> {
  const response = await fetch(`${getApiUrl()}/admin/portals`, {
    method: 'GET',
    headers: buildHeaders(),
  });
  return handleResponse<PortalAdaptersResponse>(response);
}

export async function fetchFromPortal(
  request: PortalFiltersRequest
): Promise<PortalIngestResponse> {
  const response = await fetch(`${getApiUrl()}/admin/portals/fetch`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(request),
  });
  return handleResponse<PortalIngestResponse>(response);
}

// Saved Searches API functions for Task #36
export async function getSavedSearches(
  includeInactive: boolean = false
): Promise<SavedSearchListResponse> {
  const url = `${getApiUrl()}/saved-searches?include_inactive=${includeInactive}`;
  const response = await safeFetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<SavedSearchListResponse>(response);
}

export async function createSavedSearch(data: SavedSearchCreate): Promise<SavedSearch> {
  const response = await safeFetch(`${getApiUrl()}/saved-searches`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<SavedSearch>(response);
}

export async function getSavedSearch(id: string): Promise<SavedSearch> {
  const response = await safeFetch(`${getApiUrl()}/saved-searches/${id}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<SavedSearch>(response);
}

export async function updateSavedSearch(id: string, data: SavedSearchUpdate): Promise<SavedSearch> {
  const response = await safeFetch(`${getApiUrl()}/saved-searches/${id}`, {
    method: 'PATCH',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<SavedSearch>(response);
}

export async function deleteSavedSearch(id: string): Promise<void> {
  const response = await safeFetch(`${getApiUrl()}/saved-searches/${id}`, {
    method: 'DELETE',
    headers: buildHeaders(),
    credentials: 'include',
  });
  if (!response.ok) {
    const errorText = await response.text().catch(() => '');
    const requestId = response.headers.get('X-Request-ID') || undefined;
    throw new ApiError(
      errorText || 'Failed to delete saved search',
      response.status,
      requestId || undefined
    );
  }
}

export async function toggleSavedSearchAlert(id: string, enabled: boolean): Promise<SavedSearch> {
  const response = await safeFetch(
    `${getApiUrl()}/saved-searches/${id}/toggle-alert?enabled=${enabled}`,
    {
      method: 'POST',
      headers: buildHeaders(),
      credentials: 'include',
    }
  );
  return handleResponse<SavedSearch>(response);
}

export async function markSavedSearchUsed(id: string): Promise<SavedSearch> {
  const response = await safeFetch(`${getApiUrl()}/saved-searches/${id}/use`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<SavedSearch>(response);
}

// Favorites API functions for Task #37
export async function getFavorites(
  collectionId?: string,
  limit: number = 50,
  offset: number = 0
): Promise<FavoriteListResponse> {
  const params = new URLSearchParams();
  if (collectionId) params.append('collection_id', collectionId);
  params.append('limit', String(limit));
  params.append('offset', String(offset));

  const response = await safeFetch(`${getApiUrl()}/favorites?${params}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<FavoriteListResponse>(response);
}

export async function addFavorite(data: FavoriteCreate): Promise<Favorite> {
  const response = await safeFetch(`${getApiUrl()}/favorites`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<Favorite>(response);
}

export async function removeFavorite(favoriteId: string): Promise<void> {
  const response = await safeFetch(`${getApiUrl()}/favorites/${favoriteId}`, {
    method: 'DELETE',
    headers: buildHeaders(),
    credentials: 'include',
  });
  if (!response.ok) {
    const errorText = await response.text().catch(() => '');
    throw new ApiError(errorText || 'Failed to remove favorite', response.status);
  }
}

export async function removeFavoriteByProperty(propertyId: string): Promise<void> {
  const response = await safeFetch(`${getApiUrl()}/favorites/by-property/${propertyId}`, {
    method: 'DELETE',
    headers: buildHeaders(),
    credentials: 'include',
  });
  if (!response.ok) {
    const errorText = await response.text().catch(() => '');
    throw new ApiError(errorText || 'Failed to remove favorite', response.status);
  }
}

export async function checkFavorite(propertyId: string): Promise<FavoriteCheckResponse> {
  const response = await safeFetch(`${getApiUrl()}/favorites/check/${propertyId}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<FavoriteCheckResponse>(response);
}

export async function getFavoriteIds(): Promise<string[]> {
  const response = await safeFetch(`${getApiUrl()}/favorites/ids`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<string[]>(response);
}

export async function updateFavorite(favoriteId: string, data: FavoriteUpdate): Promise<Favorite> {
  const response = await safeFetch(`${getApiUrl()}/favorites/${favoriteId}`, {
    method: 'PATCH',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<Favorite>(response);
}

export async function moveFavoriteToCollection(
  favoriteId: string,
  collectionId: string
): Promise<Favorite> {
  const response = await safeFetch(`${getApiUrl()}/favorites/${favoriteId}/move/${collectionId}`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<Favorite>(response);
}

// Collections API functions for Task #37
export async function getCollections(): Promise<CollectionListResponse> {
  const response = await safeFetch(`${getApiUrl()}/collections`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<CollectionListResponse>(response);
}

export async function createCollection(data: CollectionCreate): Promise<Collection> {
  const response = await safeFetch(`${getApiUrl()}/collections`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<Collection>(response);
}

export async function getDefaultCollection(): Promise<Collection> {
  const response = await safeFetch(`${getApiUrl()}/collections/default`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<Collection>(response);
}

export async function getCollection(id: string): Promise<Collection> {
  const response = await safeFetch(`${getApiUrl()}/collections/${id}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<Collection>(response);
}

export async function updateCollection(id: string, data: CollectionUpdate): Promise<Collection> {
  const response = await safeFetch(`${getApiUrl()}/collections/${id}`, {
    method: 'PUT',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<Collection>(response);
}

export async function deleteCollection(id: string): Promise<void> {
  const response = await safeFetch(`${getApiUrl()}/collections/${id}`, {
    method: 'DELETE',
    headers: buildHeaders(),
    credentials: 'include',
  });
  if (!response.ok) {
    const errorText = await response.text().catch(() => '');
    throw new ApiError(errorText || 'Failed to delete collection', response.status);
  }
}

// Market API functions for Task #38: Price History & Trends
export async function getPriceHistory(
  propertyId: string,
  limit: number = 100
): Promise<PriceHistory> {
  const response = await safeFetch(
    `${getApiUrl()}/market/price-history/${encodeURIComponent(propertyId)}?limit=${limit}`,
    {
      method: 'GET',
      headers: buildHeaders(),
      credentials: 'include',
    }
  );
  return handleResponse<PriceHistory>(response);
}

export async function getMarketTrends(params: {
  city?: string;
  district?: string;
  interval?: 'month' | 'quarter' | 'year';
  months_back?: number;
}): Promise<MarketTrends> {
  const searchParams = new URLSearchParams();
  if (params.city) searchParams.append('city', params.city);
  if (params.district) searchParams.append('district', params.district);
  if (params.interval) searchParams.append('interval', params.interval);
  if (params.months_back) searchParams.append('months_back', String(params.months_back));

  const queryString = searchParams.toString();
  const url = queryString
    ? `${getApiUrl()}/market/trends?${queryString}`
    : `${getApiUrl()}/market/trends`;

  const response = await safeFetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<MarketTrends>(response);
}

export async function getMarketIndicators(city?: string): Promise<MarketIndicators> {
  const url = city
    ? `${getApiUrl()}/market/indicators?city=${encodeURIComponent(city)}`
    : `${getApiUrl()}/market/indicators`;

  const response = await safeFetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<MarketIndicators>(response);
}
