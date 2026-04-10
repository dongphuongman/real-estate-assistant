/**
 * Market API: price history, trends, indicators, area comparison, anomaly detection.
 */

import type {
  PriceHistory,
  MarketTrends,
  MarketIndicators,
  AreaComparison,
  AreaInsights,
  MarketAnomaly,
  AnomalyListResponse,
  AnomalyStatsResponse,
  AnomalyDismissRequest,
  AnomalyFilterParams,
} from '../types';

import { getApiUrl, buildHeaders, safeFetch, handleResponse } from './client';

// Re-export client types used in signatures
export type { ApiErrorCategory } from './client';
export { ApiError } from './client';

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

/**
 * Task #84: Compare two areas/cities side by side.
 * Returns comparison metrics including price differences and property counts.
 */
export async function compareAreas(city1: string, city2: string): Promise<AreaComparison> {
  const url = `${getApiUrl()}/market/compare?city1=${encodeURIComponent(city1)}&city2=${encodeURIComponent(city2)}`;

  const response = await safeFetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<AreaComparison>(response);
}

/**
 * Task #84: Get detailed market insights for a single area.
 */
export async function getAreaInsights(city: string): Promise<AreaInsights> {
  const url = `${getApiUrl()}/market/area/${encodeURIComponent(city)}`;

  const response = await safeFetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<AreaInsights>(response);
}

// ============================================================================
// Task #53: Market Anomaly Detection
// ============================================================================

/**
 * Get list of detected market anomalies with optional filters.
 *
 * Supports filtering by:
 * - severity: low, medium, high, critical
 * - anomaly_type: price_spike, price_drop, volume_spike, volume_drop, unusual_pattern
 * - scope_type: property, city, district, market, region
 * - scope_id: specific property/city/district ID
 */
export async function getAnomalies(params?: AnomalyFilterParams): Promise<AnomalyListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.append('limit', String(params.limit));
  if (params?.offset) searchParams.append('offset', String(params.offset));
  if (params?.severity) searchParams.append('severity', params.severity);
  if (params?.anomaly_type) searchParams.append('anomaly_type', params.anomaly_type);
  if (params?.scope_type) searchParams.append('scope_type', params.scope_type);
  if (params?.scope_id) searchParams.append('scope_id', params.scope_id);

  const queryString = searchParams.toString();
  const url = queryString ? `${getApiUrl()}/anomalies?${queryString}` : `${getApiUrl()}/anomalies`;

  const response = await safeFetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<AnomalyListResponse>(response);
}

/**
 * Get a single anomaly by ID with full details.
 */
export async function getAnomaly(id: string): Promise<MarketAnomaly> {
  const response = await safeFetch(`${getApiUrl()}/anomalies/${encodeURIComponent(id)}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<MarketAnomaly>(response);
}

/**
 * Dismiss an anomaly (mark as reviewed/acknowledged).
 *
 * Once dismissed, the anomaly won't trigger future alerts.
 */
export async function dismissAnomaly(
  id: string,
  request?: AnomalyDismissRequest
): Promise<MarketAnomaly> {
  const response = await safeFetch(`${getApiUrl()}/anomalies/${encodeURIComponent(id)}/dismiss`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(request || {}),
  });
  return handleResponse<MarketAnomaly>(response);
}

/**
 * Get anomaly statistics summary.
 *
 * Returns:
 * - Total anomalies
 * - Count by severity
 * - Count by type
 * - Undismissed count
 */
export async function getAnomalyStats(): Promise<AnomalyStatsResponse> {
  const response = await safeFetch(`${getApiUrl()}/anomalies/stats`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<AnomalyStatsResponse>(response);
}

/**
 * Subscribe to real-time anomaly notifications via Server-Sent Events.
 *
 * Returns an EventSource that emits anomaly events as they're detected.
 *
 * @example
 * ```ts
 * const eventSource = subscribeToAnomalies();
 * eventSource.onmessage = (event) => {
 *   const anomaly = JSON.parse(event.data);
 *   console.log('New anomaly:', anomaly);
 * };
 *
 * // Don't forget to close when done
 * eventSource.close();
 * ```
 */
export function subscribeToAnomalies(): EventSource {
  const url = `${getApiUrl()}/anomalies/stream`;
  return new EventSource(url);
}
