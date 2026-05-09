/**
 * User Profile API (Task #88), User Activity Analytics API (Task #82),
 * RAG API, Prompt Templates API, CRM Sync.
 */

import type {
  ProfileUpdate,
  ProfileResponse,
  PrivacySettings,
  AvatarUploadResponse,
  DataExportRequest,
  DataExportResponse,
  DataExportStatusResponse,
  UserActivitySummary,
  UserActivityTrendsResponse,
  RagQaRequest,
  RagQaResponse,
  RagResetResponse,
  RagUploadResponse,
  PromptTemplateInfo,
  PromptTemplateApplyResponse,
} from '../types';

import {
  getApiUrl,
  buildHeaders,
  buildMultipartHeaders,
  safeFetch,
  ApiError,
  handleResponse,
} from './client';

// Re-export client types used in signatures
export type { ApiErrorCategory } from './client';

// =============================================================================
// RAG API
// =============================================================================

export async function uploadRagDocuments(files: File[]): Promise<RagUploadResponse> {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file, file.name);
  }

  const response = await fetch(`${getApiUrl()}/rag/upload`, {
    method: 'POST',
    headers: buildMultipartHeaders(),
    body: formData,
  });
  return handleResponse<RagUploadResponse>(response);
}

export async function resetRagKnowledge(): Promise<RagResetResponse> {
  const response = await fetch(`${getApiUrl()}/rag/reset`, {
    method: 'POST',
    headers: buildHeaders(),
  });
  return handleResponse<RagResetResponse>(response);
}

export async function ragQa(request: RagQaRequest): Promise<RagQaResponse> {
  const response = await fetch(`${getApiUrl()}/rag/qa`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(request),
  });
  return handleResponse<RagQaResponse>(response);
}

// =============================================================================
// CRM Sync
// =============================================================================

export async function crmSyncContactApi(name: string, phone?: string, email?: string) {
  const response = await fetch(`${getApiUrl()}/tools/crm-sync-contact`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify({ name, phone, email }),
  });
  return handleResponse<{ id: string }>(response);
}

// =============================================================================
// Prompt Templates API
// =============================================================================

export async function listPromptTemplates(): Promise<PromptTemplateInfo[]> {
  const response = await fetch(`${getApiUrl()}/prompt-templates`, {
    method: 'GET',
    headers: buildHeaders(),
  });
  return handleResponse<PromptTemplateInfo[]>(response);
}

export async function applyPromptTemplate(
  templateId: string,
  variables: Record<string, unknown>
): Promise<PromptTemplateApplyResponse> {
  const response = await fetch(`${getApiUrl()}/prompt-templates/apply`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify({ template_id: templateId, variables }),
  });
  return handleResponse<PromptTemplateApplyResponse>(response);
}

// =============================================================================
// User Activity Analytics API (Task #82)
// =============================================================================

/**
 * Get user activity summary with optional date range filter
 */
export async function getUserActivitySummary(params?: {
  period_start?: string;
  period_end?: string;
}): Promise<UserActivitySummary> {
  const searchParams = new URLSearchParams();
  if (params?.period_start) searchParams.append('period_start', params.period_start);
  if (params?.period_end) searchParams.append('period_end', params.period_end);

  const queryString = searchParams.toString();
  const url = queryString
    ? `${getApiUrl()}/user-activity/summary?${queryString}`
    : `${getApiUrl()}/user-activity/summary`;

  const response = await safeFetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<UserActivitySummary>(response);
}

/**
 * Get user activity trends over time
 */
export async function getUserActivityTrends(params?: {
  interval?: 'day' | 'week' | 'month';
  periods?: number;
}): Promise<UserActivityTrendsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.interval) searchParams.append('interval', params.interval);
  if (params?.periods) searchParams.append('periods', String(params.periods));

  const response = await safeFetch(
    `${getApiUrl()}/user-activity/trends?${searchParams.toString()}`,
    {
      method: 'GET',
      headers: buildHeaders(),
      credentials: 'include',
    }
  );
  return handleResponse<UserActivityTrendsResponse>(response);
}

/**
 * Export user activity data as CSV
 */
export async function exportUserActivityCSV(params?: {
  period_start?: string;
  period_end?: string;
}): Promise<Blob> {
  const searchParams = new URLSearchParams();
  if (params?.period_start) searchParams.append('period_start', params.period_start);
  if (params?.period_end) searchParams.append('period_end', params.period_end);

  const url = searchParams.toString()
    ? `${getApiUrl()}/user-activity/export?${searchParams.toString()}`
    : `${getApiUrl()}/user-activity/export`;

  const response = await safeFetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Export failed' }));
    throw new ApiError(error.detail || 'Export failed', response.status);
  }

  return response.blob();
}

// ============================================================
// Task #88: User Profile Management
// ============================================================

/**
 * Get current user's profile
 */
export async function getProfile(): Promise<ProfileResponse> {
  const response = await safeFetch(`${getApiUrl()}/profile`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<ProfileResponse>(response);
}

/**
 * Update current user's profile (partial update)
 */
export async function updateProfile(data: Partial<ProfileUpdate>): Promise<ProfileResponse> {
  const response = await safeFetch(`${getApiUrl()}/profile`, {
    method: 'PUT',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<ProfileResponse>(response);
}

/**
 * Upload avatar image
 */
export async function uploadAvatar(file: File): Promise<AvatarUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await safeFetch(`${getApiUrl()}/profile/avatar`, {
    method: 'POST',
    headers: buildMultipartHeaders(),
    credentials: 'include',
    body: formData,
  });
  return handleResponse<AvatarUploadResponse>(response);
}

/**
 * Delete user's avatar
 */
export async function deleteAvatar(): Promise<void> {
  const response = await safeFetch(`${getApiUrl()}/profile/avatar`, {
    method: 'DELETE',
    headers: buildHeaders(),
    credentials: 'include',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to delete avatar' }));
    throw new ApiError(error.detail || 'Failed to delete avatar', response.status);
  }
}

/**
 * Update privacy settings
 */
export async function updatePrivacySettings(settings: PrivacySettings): Promise<ProfileResponse> {
  const response = await safeFetch(`${getApiUrl()}/profile/privacy`, {
    method: 'PUT',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(settings),
  });
  return handleResponse<ProfileResponse>(response);
}

/**
 * Request GDPR data export
 */
export async function requestDataExport(request: DataExportRequest): Promise<DataExportResponse> {
  const response = await safeFetch(`${getApiUrl()}/profile/export`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(request),
  });
  return handleResponse<DataExportResponse>(response);
}

/**
 * Get data export job status
 */
export async function getExportStatus(exportId: string): Promise<DataExportStatusResponse> {
  const response = await safeFetch(`${getApiUrl()}/profile/export/${exportId}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<DataExportStatusResponse>(response);
}
