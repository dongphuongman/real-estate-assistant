/**
 * Search API: property search, export, and relevance feedback.
 */

import type {
  SearchRequest,
  SearchResponse,
  ExportFormat,
  ExportPropertiesRequest,
} from '../types';

import { getApiUrl, buildHeaders, safeFetch, handleResponse, ApiError } from './client';

// Re-export client types used in signatures
export type { ApiErrorCategory } from './client';

export async function searchProperties(request: SearchRequest): Promise<SearchResponse> {
  const response = await safeFetch(`${getApiUrl()}/search`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(request),
  });
  return handleResponse<SearchResponse>(response);
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

// ============================================================================
// Task #118: Search Relevance Feedback
// ============================================================================

/**
 * Submit a relevance rating for a search result.
 * Rating: 1 = thumbs down (poor match), 5 = thumbs up (great match).
 */
export async function submitFeedback(
  query: string,
  propertyId: string,
  rating: number
): Promise<{ id: string }> {
  const response = await safeFetch(`${getApiUrl()}/feedback/rating`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify({ query, property_id: propertyId, rating }),
  });
  return handleResponse<{ id: string }>(response);
}
