/**
 * CMA (Comparative Market Analysis) API - Task #85.
 */

import type { CMAComparable, CMAReportCreate, CMAReport, CMAReportListResponse } from '../types';

import { getApiUrl, buildHeaders, safeFetch, handleResponse } from './client';

// Re-export client types used in signatures
export type { ApiErrorCategory } from './client';
export { ApiError } from './client';

/**
 * Find comparable properties for a subject property
 */
export async function findComparables(
  propertyId: string,
  params?: {
    max_distance_km?: number;
    min_score?: number;
    max_results?: number;
  }
): Promise<CMAComparable[]> {
  const searchParams = new URLSearchParams();
  if (params?.max_distance_km) searchParams.set('max_distance_km', String(params.max_distance_km));
  if (params?.min_score) searchParams.set('min_score', String(params.min_score));
  if (params?.max_results) searchParams.set('max_results', String(params.max_results));

  const query = searchParams.toString();
  const response = await safeFetch(
    `${getApiUrl()}/cma/comparables/${propertyId}${query ? `?${query}` : ''}`,
    {
      method: 'POST',
      headers: buildHeaders(),
      credentials: 'include',
    }
  );
  return handleResponse<CMAComparable[]>(response);
}

/**
 * Generate a new CMA report
 */
export async function generateCMAReport(request: CMAReportCreate): Promise<CMAReport> {
  const response = await safeFetch(`${getApiUrl()}/cma/generate`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(request),
  });
  return handleResponse<CMAReport>(response);
}

/**
 * Get a CMA report by ID
 */
export async function getCMAReport(reportId: string): Promise<CMAReport> {
  const response = await safeFetch(`${getApiUrl()}/cma/${reportId}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<CMAReport>(response);
}

/**
 * Download CMA report as PDF
 */
export async function downloadCMAPdf(reportId: string): Promise<Blob> {
  const response = await safeFetch(`${getApiUrl()}/cma/${reportId}/pdf`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Failed to download PDF: ${response.status}`);
  }

  return response.blob();
}

/**
 * List user's CMA reports
 */
export async function listCMAReports(params?: {
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<CMAReportListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  if (params?.page) searchParams.set('page', String(params.page));
  if (params?.page_size) searchParams.set('page_size', String(params.page_size));

  const query = searchParams.toString();
  const response = await safeFetch(`${getApiUrl()}/cma${query ? `?${query}` : ''}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<CMAReportListResponse>(response);
}

/**
 * Delete a CMA report
 */
export async function deleteCMAReport(reportId: string): Promise<void> {
  const response = await safeFetch(`${getApiUrl()}/cma/${reportId}`, {
    method: 'DELETE',
    headers: buildHeaders(),
    credentials: 'include',
  });

  if (!response.ok && response.status !== 204) {
    throw new Error(`Failed to delete report: ${response.status}`);
  }
}
