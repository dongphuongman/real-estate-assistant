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
