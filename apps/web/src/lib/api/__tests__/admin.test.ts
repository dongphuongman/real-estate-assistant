/**
 * Tests for admin.ts — Data ingestion, Excel sheet parsing, portal/API integration, file upload.
 */

import { jest } from '@jest/globals';

// Mock fetch globally BEFORE importing the module under test
(globalThis as unknown as { fetch: jest.Mock }).fetch = jest.fn();
const mockFetch = globalThis.fetch as jest.Mock;

import type {
  IngestResponse,
  ExcelSheetsResponse,
  PortalAdaptersResponse,
  PortalIngestResponse,
} from '../../types';
import { ApiError } from '../client';

import {
  ingestData,
  getExcelSheets,
  ingestFileUpload,
  getExcelSheetsUpload,
  listPortals,
  fetchFromPortal,
} from '../admin';

// Helper: create a successful JSON response
function okResponse<T>(data: T) {
  return {
    ok: true,
    json: async () => data,
    status: 200,
    headers: { get: () => null },
  };
}

// Helper: create an error response
function errorResponse(status: number, detail: string) {
  return {
    ok: false,
    status,
    statusText: 'Error',
    text: async () => JSON.stringify({ detail }),
    json: async () => ({ detail }),
    headers: { get: () => null },
  };
}

beforeEach(() => {
  jest.clearAllMocks();
});

// =============================================================================
// ingestData
// =============================================================================
describe('ingestData', () => {
  const sampleResponse: IngestResponse = {
    message: 'Ingestion complete',
    properties_processed: 25,
    errors: [],
    source_type: 'excel',
    source_name: 'test-data.xlsx',
  };

  it('sends POST to /admin/ingest with JSON body', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(sampleResponse));

    const request = {
      file_urls: ['https://example.com/data.xlsx'],
      sheet_name: 'Sheet1',
      header_row: 0,
      source_name: 'test-source',
    };

    const result = await ingestData(request);

    expect(result).toEqual(sampleResponse);
    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toContain('/admin/ingest');
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body)).toEqual(request);
  });

  it('sends request with only required fields', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(sampleResponse));

    await ingestData({});

    const [, opts] = mockFetch.mock.calls[0];
    expect(JSON.parse(opts.body)).toEqual({});
  });

  it('throws ApiError on failure', async () => {
    mockFetch.mockResolvedValueOnce(errorResponse(500, 'Ingestion failed'));

    await expect(ingestData({ file_urls: ['bad-url'] })).rejects.toThrow(ApiError);
  });

  it('includes force flag when set', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(sampleResponse));

    await ingestData({ force: true, file_urls: ['url'] });

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.force).toBe(true);
  });
});

// =============================================================================
// getExcelSheets
// =============================================================================
describe('getExcelSheets', () => {
  const sampleResponse: ExcelSheetsResponse = {
    file_url: 'https://example.com/data.xlsx',
    sheet_names: ['Sheet1', 'Sheet2', 'Properties'],
    default_sheet: 'Sheet1',
    row_count: { Sheet1: 100, Sheet2: 50, Properties: 200 },
  };

  it('sends POST to /admin/excel/sheets', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(sampleResponse));

    const result = await getExcelSheets({ file_url: 'https://example.com/data.xlsx' });

    expect(result).toEqual(sampleResponse);
    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toContain('/admin/excel/sheets');
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body)).toEqual({ file_url: 'https://example.com/data.xlsx' });
  });

  it('throws ApiError on error', async () => {
    mockFetch.mockResolvedValueOnce(errorResponse(400, 'Invalid file URL'));

    await expect(getExcelSheets({ file_url: '' })).rejects.toThrow(ApiError);
  });
});

// =============================================================================
// ingestFileUpload
// =============================================================================
describe('ingestFileUpload', () => {
  const sampleResponse: IngestResponse = {
    message: 'File uploaded and ingested',
    properties_processed: 10,
    errors: [],
  };

  it('uploads file via FormData to /admin/ingest/upload', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(sampleResponse));

    const file = new File(['content'], 'data.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    const result = await ingestFileUpload(file);

    expect(result).toEqual(sampleResponse);
    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toContain('/admin/ingest/upload');
    expect(opts.method).toBe('POST');
    expect(opts.body).toBeInstanceOf(FormData);
  });

  it('appends optional sheet_name and source_name to FormData', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(sampleResponse));

    const file = new File(['data'], 'test.csv');
    await ingestFileUpload(file, { sheet_name: 'Sheet1', source_name: 'my-source', header_row: 2 });

    const [, opts] = mockFetch.mock.calls[0];
    const fd = opts.body as FormData;
    expect(fd.get('sheet_name')).toBe('Sheet1');
    expect(fd.get('source_name')).toBe('my-source');
    expect(fd.get('header_row')).toBe('2');
  });

  it('defaults header_row to 0 when not provided', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(sampleResponse));

    const file = new File(['data'], 'test.csv');
    await ingestFileUpload(file);

    const fd = mockFetch.mock.calls[0][1].body as FormData;
    expect(fd.get('header_row')).toBe('0');
  });

  it('omits sheet_name and source_name when not provided', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(sampleResponse));

    const file = new File(['data'], 'test.csv');
    await ingestFileUpload(file, { header_row: 1 });

    const fd = mockFetch.mock.calls[0][1].body as FormData;
    expect(fd.get('sheet_name')).toBeNull();
    expect(fd.get('source_name')).toBeNull();
    expect(fd.get('header_row')).toBe('1');
  });

  it('throws ApiError on failure', async () => {
    mockFetch.mockResolvedValueOnce(errorResponse(422, 'Invalid file'));

    const file = new File(['bad'], 'bad.txt');
    await expect(ingestFileUpload(file)).rejects.toThrow(ApiError);
  });
});

// =============================================================================
// getExcelSheetsUpload
// =============================================================================
describe('getExcelSheetsUpload', () => {
  const sampleResponse: ExcelSheetsResponse = {
    file_url: '',
    sheet_names: ['Data'],
    row_count: { Data: 50 },
  };

  it('uploads file via FormData to /admin/excel/sheets/upload', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(sampleResponse));

    const file = new File(['excel-data'], 'sheets.xlsx', { type: 'application/octet-stream' });
    const result = await getExcelSheetsUpload(file);

    expect(result).toEqual(sampleResponse);
    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toContain('/admin/excel/sheets/upload');
    expect(opts.method).toBe('POST');
    expect(opts.body).toBeInstanceOf(FormData);
  });

  it('throws ApiError on failure', async () => {
    mockFetch.mockResolvedValueOnce(errorResponse(400, 'No sheets found'));

    const file = new File(['empty'], 'empty.xlsx');
    await expect(getExcelSheetsUpload(file)).rejects.toThrow(ApiError);
  });
});

// =============================================================================
// listPortals
// =============================================================================
describe('listPortals', () => {
  const sampleResponse: PortalAdaptersResponse = {
    adapters: [
      {
        name: 'otodom',
        display_name: 'Otodom',
        configured: true,
        has_api_key: true,
        rate_limit: { requests: 100, window_seconds: 60 },
      },
      {
        name: 'olx',
        display_name: 'OLX',
        configured: false,
        has_api_key: false,
      },
    ],
    count: 2,
  };

  it('sends GET to /admin/portals', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(sampleResponse));

    const result = await listPortals();

    expect(result).toEqual(sampleResponse);
    expect(result.count).toBe(2);
    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toContain('/admin/portals');
    expect(opts.method).toBe('GET');
  });

  it('returns empty adapters list', async () => {
    mockFetch.mockResolvedValueOnce(okResponse({ adapters: [], count: 0 }));

    const result = await listPortals();
    expect(result.adapters).toHaveLength(0);
    expect(result.count).toBe(0);
  });

  it('throws ApiError on failure', async () => {
    mockFetch.mockResolvedValueOnce(errorResponse(500, 'Internal error'));

    await expect(listPortals()).rejects.toThrow(ApiError);
  });
});

// =============================================================================
// fetchFromPortal
// =============================================================================
describe('fetchFromPortal', () => {
  const sampleResponse: PortalIngestResponse = {
    success: true,
    message: 'Fetched 15 properties',
    portal: 'otodom',
    properties_processed: 15,
    source_type: 'portal',
    source_name: 'otodom-krakow',
    errors: [],
    filters_applied: { city: 'Krakow' },
  };

  it('sends POST to /admin/portals/fetch with filters', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(sampleResponse));

    const request = {
      portal: 'otodom',
      city: 'Krakow',
      min_price: 200000,
      max_price: 500000,
      min_rooms: 2,
      max_rooms: 4,
      property_type: 'apartment',
      listing_type: 'sale',
      limit: 50,
      source_name: 'otodom-krakow',
    };

    const result = await fetchFromPortal(request);

    expect(result).toEqual(sampleResponse);
    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toContain('/admin/portals/fetch');
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body)).toEqual(request);
  });

  it('sends minimal request with only portal name', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(sampleResponse));

    await fetchFromPortal({ portal: 'olx' });

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.portal).toBe('olx');
    expect(body.city).toBeUndefined();
    expect(body.min_price).toBeUndefined();
  });

  it('handles response with errors', async () => {
    const errorResponse_: PortalIngestResponse = {
      success: false,
      message: 'Partial failure',
      portal: 'olx',
      properties_processed: 3,
      source_type: 'portal',
      errors: ['Timeout on page 2', 'Invalid data on row 15'],
    };
    mockFetch.mockResolvedValueOnce(okResponse(errorResponse_));

    const result = await fetchFromPortal({ portal: 'olx' });
    expect(result.success).toBe(false);
    expect(result.errors).toHaveLength(2);
  });

  it('throws ApiError on server error', async () => {
    mockFetch.mockResolvedValueOnce(errorResponse(502, 'Bad Gateway'));

    await expect(fetchFromPortal({ portal: 'otodom' })).rejects.toThrow(ApiError);
  });
});
