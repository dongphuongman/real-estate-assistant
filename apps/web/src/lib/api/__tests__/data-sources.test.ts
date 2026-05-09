/**
 * Tests for data-sources.ts — Data Sources, MCP Connectors, Bulk Jobs.
 */

import { jest } from '@jest/globals';
import type {
  DataSource,
  DataSourceListResponse,
  DataSourceSyncResponse,
  DataSourceTestResponse,
  SyncHistoryResponse,
  MCPConnectorsListResponse,
  MCPConnectorDetailResponse,
  MCPConnectorHealthResponse,
  MCPHealthResponse,
  BulkJobCreateResponse,
  BulkJobListResponse,
  BulkJobResponse,
} from '../../types';

// Mock fetch globally
(globalThis as unknown as { fetch: jest.Mock }).fetch = jest.fn();
const mockFetch = globalThis.fetch as jest.Mock;

// Helper to create a successful JSON response
function okResponse<T>(data: T) {
  return {
    ok: true,
    json: async () => data,
    status: 200,
    headers: { get: () => null },
  };
}

// Helper to create an error response
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

import {
  listDataSources,
  createDataSource,
  getDataSource,
  updateDataSource,
  deleteDataSource,
  syncDataSource,
  testDataSource,
  getDataSourceSyncHistory,
  listMCPConnectors,
  getMCPConnector,
  healthCheckMCPConnector,
  healthCheckAllMCPConnectors,
  createBulkImportJob,
  createBulkExportJob,
  listBulkJobs,
  getBulkJob,
  cancelBulkJob,
  deleteBulkJob,
} from '../data-sources';

beforeEach(() => {
  jest.clearAllMocks();
});

// =============================================================================
// Data Sources API
// =============================================================================
describe('Data Sources API', () => {
  const sampleSource: DataSource = {
    id: 'ds-1',
    name: 'Test Source',
    source_type: 'api',
    status: 'active',
    config: {},
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  };

  describe('listDataSources', () => {
    it('fetches without params', async () => {
      const data: DataSourceListResponse = { items: [], total: 0 };
      mockFetch.mockResolvedValueOnce(okResponse(data));

      const result = await listDataSources();

      expect(result.total).toBe(0);
      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('/data-sources');
      expect(url).not.toContain('?');
    });

    it('passes pagination params', async () => {
      mockFetch.mockResolvedValueOnce(okResponse({ items: [], total: 0 }));

      await listDataSources({ page: 2, page_size: 25 });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('page=2');
      expect(url).toContain('page_size=25');
    });

    it('passes status and source_type filters', async () => {
      mockFetch.mockResolvedValueOnce(okResponse({ items: [], total: 0 }));

      await listDataSources({ status: 'active', source_type: 'api' });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('status=active');
      expect(url).toContain('source_type=api');
    });

    it('returns data sources list', async () => {
      const data: DataSourceListResponse = { items: [sampleSource], total: 1 };
      mockFetch.mockResolvedValueOnce(okResponse(data));

      const result = await listDataSources();
      expect(result.items).toHaveLength(1);
      expect(result.items[0].name).toBe('Test Source');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(errorResponse(500, 'Server error'));

      await expect(listDataSources()).rejects.toThrow();
    });
  });

  describe('createDataSource', () => {
    it('sends POST with data source data', async () => {
      const input = {
        name: 'New Source',
        source_type: 'api' as const,
        config: { url: 'https://example.com' },
      };
      mockFetch.mockResolvedValueOnce(okResponse(sampleSource));

      await createDataSource(input);

      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('POST');
      expect(JSON.parse(opts.body)).toEqual(input);
      expect(url).toContain('/data-sources');
    });
  });

  describe('getDataSource', () => {
    it('fetches single data source by id', async () => {
      mockFetch.mockResolvedValueOnce(okResponse(sampleSource));

      const result = await getDataSource('ds-1');

      expect(result.id).toBe('ds-1');
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('GET');
      expect(url).toContain('/data-sources/ds-1');
    });
  });

  describe('updateDataSource', () => {
    it('sends PATCH with update data', async () => {
      const update = { name: 'Updated Source' };
      mockFetch.mockResolvedValueOnce(okResponse({ ...sampleSource, name: 'Updated Source' }));

      const result = await updateDataSource('ds-1', update);

      expect(result.name).toBe('Updated Source');
      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('PATCH');
      expect(JSON.parse(opts.body)).toEqual(update);
    });
  });

  describe('deleteDataSource', () => {
    it('succeeds on ok response with default confirm=true', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, status: 204 });

      await expect(deleteDataSource('ds-1')).resolves.toBeUndefined();
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('DELETE');
      expect(url).toContain('confirm=true');
    });

    it('passes confirm=false', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, status: 204 });

      await deleteDataSource('ds-1', false);

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('confirm=false');
    });

    it('throws Error on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Not found' }),
      });

      await expect(deleteDataSource('bad-id')).rejects.toThrow('Not found');
    });

    it('uses fallback message when json() rejects', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('json failed');
        },
      });

      await expect(deleteDataSource('ds-1')).rejects.toThrow('Delete failed');
    });
  });

  describe('syncDataSource', () => {
    it('sends POST to /sync endpoint', async () => {
      const syncResponse: DataSourceSyncResponse = {
        status: 'syncing',
        job_id: 'job-1',
        message: 'Sync started',
      };
      mockFetch.mockResolvedValueOnce(okResponse(syncResponse));

      const result = await syncDataSource('ds-1');

      expect(result.status).toBe('syncing');
      expect(result.job_id).toBe('job-1');
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('POST');
      expect(url).toContain('/data-sources/ds-1/sync');
    });
  });

  describe('testDataSource', () => {
    it('sends POST to /test endpoint with config', async () => {
      const testRequest = {
        source_type: 'api' as const,
        config: { url: 'https://example.com/api' },
      };
      const testResponse: DataSourceTestResponse = {
        success: true,
        message: 'Connection OK',
        records_available: 150,
      };
      mockFetch.mockResolvedValueOnce(okResponse(testResponse));

      const result = await testDataSource(testRequest);

      expect(result.success).toBe(true);
      expect(result.records_available).toBe(150);
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('POST');
      expect(url).toContain('/data-sources/test');
      expect(JSON.parse(opts.body)).toEqual(testRequest);
    });
  });

  describe('getDataSourceSyncHistory', () => {
    it('fetches history without params', async () => {
      const history: SyncHistoryResponse = { items: [], total: 0 };
      mockFetch.mockResolvedValueOnce(okResponse(history));

      const result = await getDataSourceSyncHistory('ds-1');

      expect(result.total).toBe(0);
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('GET');
      expect(url).toContain('/data-sources/ds-1/history');
    });

    it('passes pagination params', async () => {
      mockFetch.mockResolvedValueOnce(okResponse({ items: [], total: 0 }));

      await getDataSourceSyncHistory('ds-1', { page: 3, page_size: 15 });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('page=3');
      expect(url).toContain('page_size=15');
    });

    it('returns sync history items', async () => {
      const history: SyncHistoryResponse = {
        items: [
          {
            id: 'sync-1',
            data_source_id: 'ds-1',
            status: 'completed',
            records_processed: 100,
            started_at: '2024-01-01T00:00:00Z',
            completed_at: '2024-01-01T00:01:00Z',
          },
        ],
        total: 1,
      };
      mockFetch.mockResolvedValueOnce(okResponse(history));

      const result = await getDataSourceSyncHistory('ds-1');
      expect(result.items).toHaveLength(1);
      expect(result.items[0].status).toBe('completed');
    });
  });
});

// =============================================================================
// MCP Connectors API
// =============================================================================
describe('MCP Connectors API', () => {
  describe('listMCPConnectors', () => {
    it('fetches all connectors', async () => {
      const data: MCPConnectorsListResponse = {
        connectors: [
          {
            name: 'connector-1',
            display_name: 'Connector One',
            status: 'connected',
            capabilities: ['tools'],
          },
        ],
        total: 1,
      };
      mockFetch.mockResolvedValueOnce(okResponse(data));

      const result = await listMCPConnectors();

      expect(result.total).toBe(1);
      expect(result.connectors[0].name).toBe('connector-1');
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('GET');
      expect(url).toContain('/mcp/connectors');
    });
  });

  describe('getMCPConnector', () => {
    it('fetches single connector by name', async () => {
      const detail: MCPConnectorDetailResponse = {
        name: 'connector-1',
        display_name: 'Connector One',
        status: 'connected',
        capabilities: ['tools'],
        description: 'A test connector',
        version: '1.0',
        tools: [],
        last_health_check: '2024-01-01T00:00:00Z',
      };
      mockFetch.mockResolvedValueOnce(okResponse(detail));

      const result = await getMCPConnector('connector-1');

      expect(result.name).toBe('connector-1');
      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('/mcp/connectors/connector-1');
    });

    it('encodes connector name with special chars', async () => {
      mockFetch.mockResolvedValueOnce(
        okResponse({
          name: 'conn/special',
          display_name: 'Special',
          status: 'connected',
          capabilities: [],
          description: '',
          version: '1.0',
          tools: [],
          last_health_check: '',
        })
      );

      await getMCPConnector('conn/special');

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('conn%2Fspecial');
    });
  });

  describe('healthCheckMCPConnector', () => {
    it('checks health of a specific connector', async () => {
      const health: MCPConnectorHealthResponse = {
        name: 'connector-1',
        status: 'healthy',
        response_time_ms: 45,
        checked_at: '2024-01-01T00:00:00Z',
        details: {},
      };
      mockFetch.mockResolvedValueOnce(okResponse(health));

      const result = await healthCheckMCPConnector('connector-1');

      expect(result.status).toBe('healthy');
      expect(result.response_time_ms).toBe(45);
      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('/mcp/connectors/connector-1/health');
    });
  });

  describe('healthCheckAllMCPConnectors', () => {
    it('checks health of all connectors', async () => {
      const health: MCPHealthResponse = {
        overall_status: 'healthy',
        connectors: {
          'connector-1': { status: 'healthy', response_time_ms: 30 },
          'connector-2': { status: 'degraded', response_time_ms: 500 },
        },
        checked_at: '2024-01-01T00:00:00Z',
      };
      mockFetch.mockResolvedValueOnce(okResponse(health));

      const result = await healthCheckAllMCPConnectors();

      expect(result.overall_status).toBe('healthy');
      expect(Object.keys(result.connectors)).toHaveLength(2);
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('GET');
      expect(url).toContain('/mcp/health');
    });
  });
});

// =============================================================================
// Bulk Jobs API
// =============================================================================
describe('Bulk Jobs API', () => {
  describe('createBulkImportJob', () => {
    it('sends POST to /bulk-jobs/import', async () => {
      const request = {
        source_type: 'csv' as const,
        file_url: 'https://example.com/data.csv',
        options: { delimiter: ',' },
      };
      const response: BulkJobCreateResponse = {
        job_id: 'job-1',
        status: 'pending',
        message: 'Job created',
      };
      mockFetch.mockResolvedValueOnce(okResponse(response));

      const result = await createBulkImportJob(request);

      expect(result.job_id).toBe('job-1');
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('POST');
      expect(url).toContain('/bulk-jobs/import');
      expect(JSON.parse(opts.body)).toEqual(request);
    });
  });

  describe('createBulkExportJob', () => {
    it('sends POST to /bulk-jobs/export', async () => {
      const request = {
        source_type: 'api' as const,
        format: 'csv' as const,
        filters: { status: 'active' },
      };
      const response: BulkJobCreateResponse = {
        job_id: 'job-2',
        status: 'pending',
        message: 'Export job created',
      };
      mockFetch.mockResolvedValueOnce(okResponse(response));

      const result = await createBulkExportJob(request);

      expect(result.job_id).toBe('job-2');
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('POST');
      expect(url).toContain('/bulk-jobs/export');
    });
  });

  describe('listBulkJobs', () => {
    it('fetches without params', async () => {
      const data: BulkJobListResponse = { items: [], total: 0 };
      mockFetch.mockResolvedValueOnce(okResponse(data));

      const result = await listBulkJobs();

      expect(result.total).toBe(0);
      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('/bulk-jobs');
      expect(url).not.toContain('?');
    });

    it('passes all filter params', async () => {
      mockFetch.mockResolvedValueOnce(okResponse({ items: [], total: 0 }));

      await listBulkJobs({
        job_type: 'import',
        status: 'completed',
        source_type: 'csv',
        page: 2,
        page_size: 10,
      });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('job_type=import');
      expect(url).toContain('status=completed');
      expect(url).toContain('source_type=csv');
      expect(url).toContain('page=2');
      expect(url).toContain('page_size=10');
    });

    it('returns bulk jobs list', async () => {
      const job: BulkJobResponse = {
        id: 'job-1',
        job_type: 'import',
        source_type: 'csv',
        status: 'completed',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:01:00Z',
        total_records: 100,
        processed_records: 100,
        failed_records: 0,
      };
      const data: BulkJobListResponse = { items: [job], total: 1 };
      mockFetch.mockResolvedValueOnce(okResponse(data));

      const result = await listBulkJobs();
      expect(result.items[0].status).toBe('completed');
    });
  });

  describe('getBulkJob', () => {
    it('fetches single job by id', async () => {
      const job: BulkJobResponse = {
        id: 'job-1',
        job_type: 'import',
        source_type: 'csv',
        status: 'running',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:30Z',
        total_records: 200,
        processed_records: 120,
        failed_records: 2,
      };
      mockFetch.mockResolvedValueOnce(okResponse(job));

      const result = await getBulkJob('job-1');

      expect(result.id).toBe('job-1');
      expect(result.processed_records).toBe(120);
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('GET');
      expect(url).toContain('/bulk-jobs/job-1');
    });

    it('encodes job id', async () => {
      mockFetch.mockResolvedValueOnce(
        okResponse({
          id: 'job/special',
          job_type: 'import',
          source_type: 'csv',
          status: 'pending',
          created_at: '',
          updated_at: '',
          total_records: 0,
          processed_records: 0,
          failed_records: 0,
        })
      );

      await getBulkJob('job/special');

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('job%2Fspecial');
    });
  });

  describe('cancelBulkJob', () => {
    it('sends POST to /cancel endpoint', async () => {
      const job: BulkJobResponse = {
        id: 'job-1',
        job_type: 'import',
        source_type: 'csv',
        status: 'cancelled',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:10Z',
        total_records: 100,
        processed_records: 50,
        failed_records: 0,
      };
      mockFetch.mockResolvedValueOnce(okResponse(job));

      const result = await cancelBulkJob('job-1');

      expect(result.status).toBe('cancelled');
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('POST');
      expect(url).toContain('/bulk-jobs/job-1/cancel');
    });
  });

  describe('deleteBulkJob', () => {
    it('succeeds on ok response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, status: 204 });

      await expect(deleteBulkJob('job-1')).resolves.toBeUndefined();
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('DELETE');
      expect(url).toContain('/bulk-jobs/job-1');
    });

    it('throws Error on failure with detail', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Job not found' }),
      });

      await expect(deleteBulkJob('job-999')).rejects.toThrow('Job not found');
    });

    it('uses fallback message when json() rejects', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('json failed');
        },
      });

      await expect(deleteBulkJob('job-1')).rejects.toThrow('Delete failed');
    });

    it('encodes job id', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, status: 204 });

      await deleteBulkJob('job/special');

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('job%2Fspecial');
    });
  });
});
