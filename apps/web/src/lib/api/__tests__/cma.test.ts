/**
 * Tests for cma.ts API module (Comparative Market Analysis).
 * Covers findComparables, generateCMAReport, getCMAReport,
 * downloadCMAPdf, listCMAReports, deleteCMAReport.
 */

import { describe, it, expect, jest, beforeEach } from '@jest/globals';

// Mock fetch globally before any imports
const mockFetch = jest.fn();
(globalThis as unknown as { fetch: jest.Mock }).fetch = mockFetch;

import {
  findComparables,
  generateCMAReport,
  getCMAReport,
  downloadCMAPdf,
  listCMAReports,
  deleteCMAReport,
  ApiError,
} from '@/lib/api/cma';

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

describe('cma.ts API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockReset();
  });

  // =========================================================================
  // findComparables
  // =========================================================================

  describe('findComparables', () => {
    it('finds comparables without params via POST', async () => {
      const result = [
        { property_id: 'comp-1', address: 'Street 1', score: 0.95, distance_km: 0.3 },
        { property_id: 'comp-2', address: 'Street 2', score: 0.88, distance_km: 0.8 },
      ];
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await findComparables('prop-1');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/cma/comparables/prop-1`);
      expect(calledUrl).not.toContain('?');
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(init.credentials).toBe('include');
      expect(response).toHaveLength(2);
      expect(response[0].score).toBe(0.95);
    });

    it('appends filter params when provided', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse([]));

      await findComparables('prop-1', {
        max_distance_km: 5,
        min_score: 0.8,
        max_results: 10,
      });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('max_distance_km=5');
      expect(calledUrl).toContain('min_score=0.8');
      expect(calledUrl).toContain('max_results=10');
    });

    it('omits undefined optional params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse([]));

      await findComparables('prop-1', { max_distance_km: 10 });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('max_distance_km=10');
      expect(calledUrl).not.toContain('min_score');
      expect(calledUrl).not.toContain('max_results');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Not found', 404));

      await expect(findComparables('bad')).rejects.toThrow(ApiError);
    });

    it('handles network failure (safeFetch)', async () => {
      mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

      try {
        await findComparables('prop-1');
        fail('Expected ApiError');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).category).toBe('network');
      }
    });
  });

  // =========================================================================
  // generateCMAReport
  // =========================================================================

  describe('generateCMAReport', () => {
    it('generates a report via POST with credentials', async () => {
      const result = {
        id: 'report-1',
        subject_property_id: 'prop-1',
        status: 'completed',
        comparables: [],
        created_at: '2024-01-15T00:00:00Z',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const input = {
        subject_property_id: 'prop-1',
        comparable_ids: ['comp-1', 'comp-2'],
        adjustments: [],
      };
      const response = await generateCMAReport(input);

      expectCalledWithPath(`${API_BASE}/cma/generate`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(init.credentials).toBe('include');
      expect(JSON.parse(init.body as string)).toEqual(input);
      expect(response.id).toBe('report-1');
      expect(response.status).toBe('completed');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Bad request', 400));

      await expect(generateCMAReport({ subject_property_id: 'bad' })).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // getCMAReport
  // =========================================================================

  describe('getCMAReport', () => {
    it('fetches a report by ID via GET with credentials', async () => {
      const result = {
        id: 'report-1',
        subject_property_id: 'prop-1',
        status: 'completed',
        comparables: [{ property_id: 'comp-1', score: 0.9 }],
        valuation: { estimated_value: 350000, confidence: 0.85 },
        created_at: '2024-01-15T00:00:00Z',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getCMAReport('report-1');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/cma/report-1`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('GET');
      expect(init.credentials).toBe('include');
      expect(response.id).toBe('report-1');
      expect(response.valuation.estimated_value).toBe(350000);
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Not found', 404));

      await expect(getCMAReport('bad')).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // downloadCMAPdf
  // =========================================================================

  describe('downloadCMAPdf', () => {
    it('downloads PDF as Blob on success', async () => {
      const blob = new Blob(['pdf-content'], { type: 'application/pdf' });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: 'OK',
        headers: new Headers({ 'Content-Type': 'application/pdf' }),
        json: async () => null,
        text: async () => 'pdf-content',
        blob: async () => blob,
      } as Response);

      const response = await downloadCMAPdf('report-1');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/cma/report-1/pdf`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('GET');
      expect(init.credentials).toBe('include');
      expect(response).toBeInstanceOf(Blob);
    });

    it('throws Error on non-ok response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        headers: new Headers(),
        json: async () => null,
        text: async () => '',
        blob: async () => new Blob(),
      } as Response);

      await expect(downloadCMAPdf('bad')).rejects.toThrow('Failed to download PDF: 404');
    });

    it('throws on 500 status', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Error',
        headers: new Headers(),
        json: async () => null,
        text: async () => '',
        blob: async () => new Blob(),
      } as Response);

      await expect(downloadCMAPdf('report-1')).rejects.toThrow('Failed to download PDF: 500');
    });
  });

  // =========================================================================
  // listCMAReports
  // =========================================================================

  describe('listCMAReports', () => {
    it('lists reports without params via GET', async () => {
      const result = {
        reports: [{ id: 'r1', status: 'completed', created_at: '2024-01-01T00:00:00Z' }],
        total: 1,
        page: 1,
        page_size: 20,
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await listCMAReports();

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/cma`);
      expect(calledUrl).not.toContain('?');
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('GET');
      expect(init.credentials).toBe('include');
      expect(response.reports).toHaveLength(1);
    });

    it('appends filter params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ reports: [], total: 0 }));

      await listCMAReports({ status: 'completed', page: 2, page_size: 10 });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('status=completed');
      expect(calledUrl).toContain('page=2');
      expect(calledUrl).toContain('page_size=10');
    });

    it('omits undefined params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ reports: [], total: 0 }));

      await listCMAReports({ status: 'pending' });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('status=pending');
      expect(calledUrl).not.toContain('page=');
      expect(calledUrl).not.toContain('page_size=');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(listCMAReports()).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // deleteCMAReport
  // =========================================================================

  describe('deleteCMAReport', () => {
    it('deletes report on 204 No Content without error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
        statusText: 'No Content',
        headers: new Headers(),
        json: async () => null,
        text: async () => '',
      } as Response);

      await deleteCMAReport('report-1');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/cma/report-1`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('DELETE');
      expect(init.credentials).toBe('include');
    });

    it('deletes report on 200 OK without error', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(null, 200));

      await deleteCMAReport('report-1');

      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('throws Error on non-ok, non-204 response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        headers: new Headers(),
        json: async () => null,
        text: async () => '',
      } as Response);

      await expect(deleteCMAReport('bad')).rejects.toThrow('Failed to delete report: 404');
    });

    it('throws Error on 500 status', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Error',
        headers: new Headers(),
        json: async () => null,
        text: async () => '',
      } as Response);

      await expect(deleteCMAReport('report-1')).rejects.toThrow('Failed to delete report: 500');
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
