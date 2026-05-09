/**
 * Data Sources API (Task #79), Bulk Jobs API (Task #80), MCP Connector API (Task #71).
 */

import type {
  DataSource,
  DataSourceCreate,
  DataSourceUpdate,
  DataSourceListResponse,
  DataSourceSyncResponse,
  DataSourceTestRequest,
  DataSourceTestResponse,
  SyncHistoryResponse,
  BulkImportRequest,
  BulkExportRequest,
  BulkJobResponse,
  BulkJobListResponse,
  BulkJobCreateResponse,
  MCPConnectorsListResponse,
  MCPConnectorDetailResponse,
  MCPConnectorHealthResponse,
  MCPHealthResponse,
} from '../types';

import { getApiUrl, buildHeaders, safeFetch, handleResponse } from './client';

// Re-export client types used in signatures
export type { ApiErrorCategory } from './client';
export { ApiError } from './client';

// =============================================================================
// Data Sources API (Task #79)
// =============================================================================

/**
 * List all data sources with pagination and filtering
 */
export async function listDataSources(params?: {
  page?: number;
  page_size?: number;
  status?: string;
  source_type?: string;
}): Promise<DataSourceListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set('page', params.page.toString());
  if (params?.page_size) searchParams.set('page_size', params.page_size.toString());
  if (params?.status) searchParams.set('status', params.status);
  if (params?.source_type) searchParams.set('source_type', params.source_type);

  const query = searchParams.toString();
  const response = await safeFetch(`${getApiUrl()}/data-sources${query ? `?${query}` : ''}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<DataSourceListResponse>(response);
}

/**
 * Create a new data source
 */
export async function createDataSource(data: DataSourceCreate): Promise<DataSource> {
  const response = await safeFetch(`${getApiUrl()}/data-sources`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<DataSource>(response);
}

/**
 * Get a specific data source by ID
 */
export async function getDataSource(id: string): Promise<DataSource> {
  const response = await safeFetch(`${getApiUrl()}/data-sources/${id}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<DataSource>(response);
}

/**
 * Update a data source
 */
export async function updateDataSource(id: string, data: DataSourceUpdate): Promise<DataSource> {
  const response = await safeFetch(`${getApiUrl()}/data-sources/${id}`, {
    method: 'PATCH',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<DataSource>(response);
}

/**
 * Delete a data source (requires confirmation)
 */
export async function deleteDataSource(id: string, confirm = true): Promise<void> {
  const response = await safeFetch(`${getApiUrl()}/data-sources/${id}?confirm=${confirm}`, {
    method: 'DELETE',
    headers: buildHeaders(),
    credentials: 'include',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Delete failed' }));
    throw new Error(error.detail || 'Delete failed');
  }
}

/**
 * Trigger a manual sync for a data source
 */
export async function syncDataSource(id: string): Promise<DataSourceSyncResponse> {
  const response = await safeFetch(`${getApiUrl()}/data-sources/${id}/sync`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<DataSourceSyncResponse>(response);
}

/**
 * Test a data source connection without saving
 */
export async function testDataSource(data: DataSourceTestRequest): Promise<DataSourceTestResponse> {
  const response = await safeFetch(`${getApiUrl()}/data-sources/test`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<DataSourceTestResponse>(response);
}

/**
 * Get sync history for a data source
 */
export async function getDataSourceSyncHistory(
  id: string,
  params?: { page?: number; page_size?: number }
): Promise<SyncHistoryResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set('page', params.page.toString());
  if (params?.page_size) searchParams.set('page_size', params.page_size.toString());

  const query = searchParams.toString();
  const response = await safeFetch(
    `${getApiUrl()}/data-sources/${id}/history${query ? `?${query}` : ''}`,
    {
      method: 'GET',
      headers: buildHeaders(),
      credentials: 'include',
    }
  );
  return handleResponse<SyncHistoryResponse>(response);
}

// =============================================================================
// MCP Connector API (Task #71: MCP Registry API)
// =============================================================================

/**
 * List all MCP connectors with status
 */
export async function listMCPConnectors(): Promise<MCPConnectorsListResponse> {
  const response = await safeFetch(`${getApiUrl()}/mcp/connectors`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<MCPConnectorsListResponse>(response);
}

/**
 * Get detailed information about a specific connector
 */
export async function getMCPConnector(name: string): Promise<MCPConnectorDetailResponse> {
  const response = await safeFetch(`${getApiUrl()}/mcp/connectors/${encodeURIComponent(name)}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<MCPConnectorDetailResponse>(response);
}

/**
 * Perform health check on a specific connector
 */
export async function healthCheckMCPConnector(name: string): Promise<MCPConnectorHealthResponse> {
  const response = await safeFetch(
    `${getApiUrl()}/mcp/connectors/${encodeURIComponent(name)}/health`,
    {
      method: 'GET',
      headers: buildHeaders(),
      credentials: 'include',
    }
  );
  return handleResponse<MCPConnectorHealthResponse>(response);
}

/**
 * Health check for all MCP connectors
 */
export async function healthCheckAllMCPConnectors(): Promise<MCPHealthResponse> {
  const response = await safeFetch(`${getApiUrl()}/mcp/health`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<MCPHealthResponse>(response);
}

// =============================================================================
// Bulk Jobs API (Task #80: Import/Export Data API)
// =============================================================================

/**
 * Create a new bulk import job
 */
export async function createBulkImportJob(
  request: BulkImportRequest
): Promise<BulkJobCreateResponse> {
  const response = await safeFetch(`${getApiUrl()}/bulk-jobs/import`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(request),
  });
  return handleResponse<BulkJobCreateResponse>(response);
}

/**
 * Create a new bulk export job
 */
export async function createBulkExportJob(
  request: BulkExportRequest
): Promise<BulkJobCreateResponse> {
  const response = await safeFetch(`${getApiUrl()}/bulk-jobs/export`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(request),
  });
  return handleResponse<BulkJobCreateResponse>(response);
}

/**
 * List bulk jobs with optional filters
 */
export async function listBulkJobs(params?: {
  job_type?: string;
  status?: string;
  source_type?: string;
  page?: number;
  page_size?: number;
}): Promise<BulkJobListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.job_type) searchParams.set('job_type', params.job_type);
  if (params?.status) searchParams.set('status', params.status);
  if (params?.source_type) searchParams.set('source_type', params.source_type);
  if (params?.page) searchParams.set('page', params.page.toString());
  if (params?.page_size) searchParams.set('page_size', params.page_size.toString());

  const query = searchParams.toString();
  const response = await safeFetch(`${getApiUrl()}/bulk-jobs${query ? `?${query}` : ''}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<BulkJobListResponse>(response);
}

/**
 * Get a specific bulk job by ID
 */
export async function getBulkJob(jobId: string): Promise<BulkJobResponse> {
  const response = await safeFetch(`${getApiUrl()}/bulk-jobs/${encodeURIComponent(jobId)}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<BulkJobResponse>(response);
}

/**
 * Cancel a running bulk job
 */
export async function cancelBulkJob(jobId: string): Promise<BulkJobResponse> {
  const response = await safeFetch(`${getApiUrl()}/bulk-jobs/${encodeURIComponent(jobId)}/cancel`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<BulkJobResponse>(response);
}

/**
 * Delete a bulk job
 */
export async function deleteBulkJob(jobId: string): Promise<void> {
  const response = await safeFetch(`${getApiUrl()}/bulk-jobs/${encodeURIComponent(jobId)}`, {
    method: 'DELETE',
    headers: buildHeaders(),
    credentials: 'include',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Delete failed' }));
    throw new Error(error.detail || 'Delete failed');
  }
}
