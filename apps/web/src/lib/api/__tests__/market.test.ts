/**
 * Tests for market.ts API module.
 * Covers price history, market trends, market indicators, area comparison,
 * area insights, anomaly detection (list, get, dismiss, stats, subscribe).
 */

import { describe, it, expect, jest, beforeEach } from '@jest/globals';

// Mock fetch globally before any imports
const mockFetch = jest.fn();
(globalThis as unknown as { fetch: jest.Mock }).fetch = mockFetch;

// Mock EventSource (not available in jsdom)
class MockEventSource {
  url: string;
  constructor(url: string) {
    this.url = url;
  }
  close() {}
}
(globalThis as unknown as { EventSource: typeof MockEventSource }).EventSource =
  MockEventSource as unknown as typeof EventSource;

import {
  getPriceHistory,
  getMarketTrends,
  getMarketIndicators,
  compareAreas,
  getAreaInsights,
  getAnomalies,
  getAnomaly,
  dismissAnomaly,
  getAnomalyStats,
  subscribeToAnomalies,
  ApiError,
} from '@/lib/api/market';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const API_BASE = '/api/v1';

function createMockResponse(data: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    headers: new Headers({ 'X-Request-ID': 'req-test-123' }),
    json: async () => data,
    text: async () => JSON.stringify(data),
  } as Response;
}

function createErrorResponse(message: string, status: number) {
  const body = { detail: message };
  return {
    ok: false,
    status,
    statusText: 'Error',
    headers: new Headers({ 'X-Request-ID': 'req-err-001' }),
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as Response;
}

function expectCalledWithPath(pathPrefix: string) {
  const calledUrl = mockFetch.mock.calls[0][0] as string;
  expect(calledUrl).toContain(pathPrefix);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('market.ts API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockReset();
  });

  // =========================================================================
  // getPriceHistory
  // =========================================================================

  describe('getPriceHistory', () => {
    it('fetches price history with default limit via GET', async () => {
      const result = { property_id: 'prop-1', history: [{ date: '2024-01', price: 300000 }] };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getPriceHistory('prop-1');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/market/price-history/prop-1`);
      expect(calledUrl).toContain('limit=100');
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('GET');
      expect(init.credentials).toBe('include');
      expect(response.property_id).toBe('prop-1');
    });

    it('uses custom limit parameter', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ property_id: 'p1', history: [] }));

      await getPriceHistory('prop-1', 50);

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('limit=50');
    });

    it('encodes property ID', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ property_id: 'a/b', history: [] }));

      await getPriceHistory('a/b');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('a%2Fb');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Not found', 404));

      await expect(getPriceHistory('bad')).rejects.toThrow(ApiError);
    });

    it('handles network failure (safeFetch)', async () => {
      mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

      try {
        await getPriceHistory('prop-1');
        fail('Expected ApiError');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).category).toBe('network');
      }
    });
  });

  // =========================================================================
  // getMarketTrends
  // =========================================================================

  describe('getMarketTrends', () => {
    it('fetches trends without params', async () => {
      const result = { trends: [], interval: 'month' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getMarketTrends({});

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/market/trends`);
      expect(response.interval).toBe('month');
    });

    it('appends city, district, interval, months_back params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ trends: [] }));

      await getMarketTrends({
        city: 'Krakow',
        district: 'Old Town',
        interval: 'quarter',
        months_back: 12,
      });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('city=Krakow');
      expect(calledUrl).toContain('district=Old+Town');
      expect(calledUrl).toContain('interval=quarter');
      expect(calledUrl).toContain('months_back=12');
    });

    it('omits undefined params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ trends: [] }));

      await getMarketTrends({ city: 'Krakow' });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('city=Krakow');
      expect(calledUrl).not.toContain('district');
      expect(calledUrl).not.toContain('interval');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Server error', 500));

      await expect(getMarketTrends({})).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // getMarketIndicators
  // =========================================================================

  describe('getMarketIndicators', () => {
    it('fetches indicators without city param', async () => {
      const result = { avg_price: 350000, median_price: 320000, listings_count: 1500 };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getMarketIndicators();

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/market/indicators`);
      expect(calledUrl).not.toContain('city');
      expect(response.avg_price).toBe(350000);
    });

    it('appends city param when provided', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({}));

      await getMarketIndicators('Krakow');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('city=Krakow');
    });

    it('encodes city name', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({}));

      await getMarketIndicators('New York');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('city=New%20York');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(getMarketIndicators()).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // compareAreas
  // =========================================================================

  describe('compareAreas', () => {
    it('compares two areas via GET', async () => {
      const result = {
        city1: 'Krakow',
        city2: 'Warsaw',
        comparison: { price_diff_percent: 15, listings_diff: 200 },
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await compareAreas('Krakow', 'Warsaw');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/market/compare`);
      expect(calledUrl).toContain('city1=Krakow');
      expect(calledUrl).toContain('city2=Warsaw');
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('GET');
      expect(init.credentials).toBe('include');
      expect(response.comparison.price_diff_percent).toBe(15);
    });

    it('encodes city names with special characters', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({}));

      await compareAreas('Krakow', 'Warsaw');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('city1=Krakow');
      expect(calledUrl).toContain('city2=Warsaw');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(compareAreas('a', 'b')).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // getAreaInsights
  // =========================================================================

  describe('getAreaInsights', () => {
    it('fetches area insights via GET with credentials', async () => {
      const result = { city: 'Krakow', price_trend: 'up', volume: 150 };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getAreaInsights('Krakow');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/market/area/Krakow`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('GET');
      expect(init.credentials).toBe('include');
      expect(response.city).toBe('Krakow');
    });

    it('encodes city name', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({}));

      await getAreaInsights('New York');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('New%20York');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Not found', 404));

      await expect(getAreaInsights('bad')).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // Anomaly Detection
  // =========================================================================

  describe('getAnomalies', () => {
    it('fetches anomalies without params', async () => {
      const result = { anomalies: [], total: 0, limit: 20, offset: 0 };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getAnomalies();

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/anomalies`);
      expect(response.anomalies).toHaveLength(0);
    });

    it('appends all filter params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ anomalies: [], total: 0 }));

      await getAnomalies({
        limit: 10,
        offset: 20,
        severity: 'high',
        anomaly_type: 'price_spike',
        scope_type: 'city',
        scope_id: 'Krakow',
      });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('limit=10');
      expect(calledUrl).toContain('offset=20');
      expect(calledUrl).toContain('severity=high');
      expect(calledUrl).toContain('anomaly_type=price_spike');
      expect(calledUrl).toContain('scope_type=city');
      expect(calledUrl).toContain('scope_id=Krakow');
    });

    it('omits undefined params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ anomalies: [], total: 0 }));

      await getAnomalies({ severity: 'critical' });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('severity=critical');
      expect(calledUrl).not.toContain('anomaly_type');
      expect(calledUrl).not.toContain('scope_type');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(getAnomalies()).rejects.toThrow(ApiError);
    });
  });

  describe('getAnomaly', () => {
    it('fetches a single anomaly by ID via GET', async () => {
      const result = {
        id: 'anom-1',
        anomaly_type: 'price_spike',
        severity: 'high',
        description: 'Price increased 50%',
        detected_at: '2024-01-15T00:00:00Z',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getAnomaly('anom-1');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/anomalies/anom-1`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('GET');
      expect(init.credentials).toBe('include');
      expect(response.id).toBe('anom-1');
      expect(response.severity).toBe('high');
    });

    it('encodes anomaly ID', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ id: 'a/b' }));

      await getAnomaly('a/b');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('a%2Fb');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Not found', 404));

      await expect(getAnomaly('bad')).rejects.toThrow(ApiError);
    });
  });

  describe('dismissAnomaly', () => {
    it('dismisses anomaly via POST without request body', async () => {
      const result = { id: 'anom-1', status: 'dismissed' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await dismissAnomaly('anom-1');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/anomalies/anom-1/dismiss`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(init.credentials).toBe('include');
      expect(response.id).toBe('anom-1');
    });

    it('dismisses anomaly with request body', async () => {
      const result = { id: 'anom-1', status: 'dismissed' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      await dismissAnomaly('anom-1', { reason: 'False positive' });

      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(JSON.parse(init.body as string)).toEqual({ reason: 'False positive' });
    });

    it('encodes anomaly ID in dismiss URL', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ id: 'a/b' }));

      await dismissAnomaly('a/b');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('a%2Fb');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(dismissAnomaly('bad')).rejects.toThrow(ApiError);
    });
  });

  describe('getAnomalyStats', () => {
    it('fetches anomaly stats via GET with credentials', async () => {
      const result = {
        total: 100,
        by_severity: { low: 50, medium: 30, high: 15, critical: 5 },
        by_type: { price_spike: 60, price_drop: 40 },
        undismissed_count: 80,
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getAnomalyStats();

      expectCalledWithPath(`${API_BASE}/anomalies/stats`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('GET');
      expect(init.credentials).toBe('include');
      expect(response.total).toBe(100);
      expect(response.undismissed_count).toBe(80);
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(getAnomalyStats()).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // subscribeToAnomalies (EventSource)
  // =========================================================================

  describe('subscribeToAnomalies', () => {
    it('returns an EventSource pointing to anomalies stream', () => {
      const es = subscribeToAnomalies();

      expect(es).toBeInstanceOf(EventSource);
      expect(es.url).toContain(`${API_BASE}/anomalies/stream`);
      es.close();
    });
  });

  // =========================================================================
  // Re-exports
  // =========================================================================

  describe('re-exports', () => {
    it('exports ApiError class from client', () => {
      expect(ApiError).toBeDefined();
      const err = new ApiError('test', 500);
      expect(err).toBeInstanceOf(Error);
      expect(err.name).toBe('ApiError');
    });
  });
});
