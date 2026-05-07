/**
 * Admin API: data ingestion, Excel sheet parsing, portal/API integration, file upload.
 */

import type {
  IngestRequest,
  IngestResponse,
  ExcelSheetsRequest,
  ExcelSheetsResponse,
  PortalFiltersRequest,
  PortalIngestResponse,
  PortalAdaptersResponse,
} from '../types';

import { getApiUrl, buildHeaders, buildMultipartHeaders, handleResponse } from './client';

// Re-export client types used in signatures
export type { ApiErrorCategory } from './client';
export { ApiError } from './client';

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

// File upload API functions for Task #48
export async function ingestFileUpload(
  file: File,
  options?: {
    sheet_name?: string;
    header_row?: number;
    source_name?: string;
  }
): Promise<IngestResponse> {
  const formData = new FormData();
  formData.append('file', file, file.name);
  if (options?.sheet_name) formData.append('sheet_name', options.sheet_name);
  formData.append('header_row', String(options?.header_row ?? 0));
  if (options?.source_name) formData.append('source_name', options.source_name);

  const response = await fetch(`${getApiUrl()}/admin/ingest/upload`, {
    method: 'POST',
    headers: buildMultipartHeaders(),
    body: formData,
  });
  return handleResponse<IngestResponse>(response);
}

export async function getExcelSheetsUpload(file: File): Promise<ExcelSheetsResponse> {
  const formData = new FormData();
  formData.append('file', file, file.name);

  const response = await fetch(`${getApiUrl()}/admin/excel/sheets/upload`, {
    method: 'POST',
    headers: buildMultipartHeaders(),
    body: formData,
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

// Monitoring API functions for Task #57
export interface HealthStatus {
  status: 'healthy' | 'unhealthy' | 'degraded';
  timestamp: string;
  service: string;
  uptime_seconds?: number;
  version?: string;
  git?: {
    commit: string;
    branch?: string;
  };
}

export interface ReadinessStatus {
  database: string;
  database_latency_ms?: number;
  redis: string;
  llm: string;
  overall: 'ready' | 'not_ready';
  timestamp: string;
}

export interface MetricsData {
  text: string;
}

export interface MonitoringOverview {
  database: {
    total_properties: number;
    recent_properties_24h: number;
    by_source: Record<string, number>;
  };
  cache: {
    hits?: number;
    misses?: number;
    total_keys?: number;
    hit_rate?: number;
  };
  knowledge_store: {
    documents: number;
    chunks: number;
  };
  llm: {
    default_provider: string;
    default_model: string;
  };
  environment: string;
  timestamp: string;
}

export async function getHealthStatus(): Promise<HealthStatus> {
  // Use direct API path (not getApiUrl()) because monitoring endpoints are proxied at /api/*
  const response = await fetch('/api/health', {
    method: 'GET',
    headers: buildHeaders(),
  });
  return handleResponse<HealthStatus>(response);
}

export async function getReadinessStatus(): Promise<ReadinessStatus> {
  const response = await fetch('/api/ready', {
    method: 'GET',
    headers: buildHeaders(),
  });
  return handleResponse<ReadinessStatus>(response);
}

export async function getMetrics(): Promise<string> {
  const response = await fetch('/api/metrics', {
    method: 'GET',
    headers: buildHeaders(),
  });
  const text = await response.text();
  return text;
}

export async function getMonitoringOverview(): Promise<MonitoringOverview> {
  const response = await fetch('/api/monitoring/overview', {
    method: 'GET',
    headers: buildHeaders(),
  });
  return handleResponse<MonitoringOverview>(response);
}

export async function sendTestAlert(): Promise<{ status: string; message: string; timestamp: string }> {
  const response = await fetch('/api/monitoring/test-alert', {
    method: 'POST',
    headers: buildHeaders(),
  });
  return handleResponse<{ status: string; message: string; timestamp: string }>(response);
}
