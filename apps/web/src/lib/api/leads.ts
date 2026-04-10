/**
 * Lead Scoring API (Task #55): lead CRUD, scoring, bulk operations.
 */

import type {
  Lead,
  LeadWithScore,
  LeadScoreBreakdown,
  AgentAssignment,
  LeadListResponse,
  LeadDetailResponse,
  LeadFilters,
  LeadStatus,
  BulkAssignRequest,
  BulkStatusUpdateRequest,
  BulkOperationResponse,
  RecalculateScoresRequest,
  RecalculateScoresResponse,
  ScoringStatistics,
} from '../types';

import { getApiUrl, buildHeaders, safeFetch, ApiError, handleResponse } from './client';

// Re-export client types used in signatures
export type { ApiErrorCategory } from './client';

/**
 * Get list of leads with optional filters.
 *
 * Agents see only their assigned leads. Admins see all leads.
 */
export async function getLeads(
  params?: LeadFilters & { page?: number; page_size?: number }
): Promise<LeadListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.append('page', String(params.page));
  if (params?.page_size) searchParams.append('page_size', String(params.page_size));
  if (params?.status) searchParams.append('status', params.status);
  if (params?.score_min !== undefined) searchParams.append('score_min', String(params.score_min));
  if (params?.score_max !== undefined) searchParams.append('score_max', String(params.score_max));
  if (params?.source) searchParams.append('source', params.source);
  if (params?.has_email !== undefined) searchParams.append('has_email', String(params.has_email));
  if (params?.agent_id) searchParams.append('agent_id', params.agent_id);
  if (params?.sort_by) searchParams.append('sort_by', params.sort_by);
  if (params?.sort_order) searchParams.append('sort_order', params.sort_order);

  const queryString = searchParams.toString();
  const url = queryString ? `${getApiUrl()}/leads?${queryString}` : `${getApiUrl()}/leads`;

  const response = await safeFetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<LeadListResponse>(response);
}

/**
 * Get high-value leads (score >= threshold, default 70).
 */
export async function getHighValueLeads(threshold = 70, limit = 50): Promise<LeadWithScore[]> {
  const searchParams = new URLSearchParams();
  searchParams.append('threshold', String(threshold));
  searchParams.append('limit', String(limit));

  const response = await safeFetch(`${getApiUrl()}/leads/high-value?${searchParams}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<LeadWithScore[]>(response);
}

/**
 * Get detailed lead information including interactions and score history.
 */
export async function getLead(leadId: string): Promise<LeadDetailResponse> {
  const response = await safeFetch(`${getApiUrl()}/leads/${encodeURIComponent(leadId)}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<LeadDetailResponse>(response);
}

/**
 * Get lead score breakdown with factors and recommendations.
 */
export async function getLeadScoreBreakdown(leadId: string): Promise<LeadScoreBreakdown> {
  const response = await safeFetch(`${getApiUrl()}/leads/${encodeURIComponent(leadId)}/score`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<LeadScoreBreakdown>(response);
}

/**
 * Update lead information.
 */
export async function updateLead(leadId: string, data: Partial<Lead>): Promise<Lead> {
  const response = await safeFetch(`${getApiUrl()}/leads/${encodeURIComponent(leadId)}`, {
    method: 'PATCH',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<Lead>(response);
}

/**
 * Update lead status.
 */
export async function updateLeadStatus(
  leadId: string,
  status: LeadStatus,
  notes?: string
): Promise<Lead> {
  const searchParams = new URLSearchParams();
  searchParams.append('status', status);
  if (notes) searchParams.append('notes', notes);

  const response = await safeFetch(
    `${getApiUrl()}/leads/${encodeURIComponent(leadId)}/status?${searchParams}`,
    {
      method: 'PATCH',
      headers: buildHeaders(),
      credentials: 'include',
    }
  );
  return handleResponse<Lead>(response);
}

/**
 * Assign an agent to a lead.
 */
export async function assignAgentToLead(
  leadId: string,
  agentId: string,
  options?: { notes?: string; is_primary?: boolean }
): Promise<AgentAssignment> {
  const response = await safeFetch(`${getApiUrl()}/leads/${encodeURIComponent(leadId)}/assign`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify({
      agent_id: agentId,
      notes: options?.notes,
      is_primary: options?.is_primary ?? true,
    }),
  });
  return handleResponse<AgentAssignment>(response);
}

/**
 * Bulk assign leads to an agent (admin only).
 */
export async function bulkAssignLeads(request: BulkAssignRequest): Promise<BulkOperationResponse> {
  const response = await safeFetch(`${getApiUrl()}/leads/bulk/assign`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(request),
  });
  return handleResponse<BulkOperationResponse>(response);
}

/**
 * Bulk update lead status (admin only).
 */
export async function bulkUpdateLeadStatus(
  request: BulkStatusUpdateRequest
): Promise<BulkOperationResponse> {
  const response = await safeFetch(`${getApiUrl()}/leads/bulk/status`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(request),
  });
  return handleResponse<BulkOperationResponse>(response);
}

/**
 * Recalculate lead scores (admin only).
 */
export async function recalculateScores(
  request?: RecalculateScoresRequest
): Promise<RecalculateScoresResponse> {
  const response = await safeFetch(`${getApiUrl()}/leads/scores/recalculate`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(request || {}),
  });
  return handleResponse<RecalculateScoresResponse>(response);
}

/**
 * Get scoring statistics (admin only).
 */
export async function getScoringStatistics(): Promise<ScoringStatistics> {
  const response = await safeFetch(`${getApiUrl()}/leads/scores/statistics`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<ScoringStatistics>(response);
}

/**
 * Export leads to CSV (admin only).
 */
export async function exportLeads(params?: {
  status?: LeadStatus;
  score_min?: number;
}): Promise<Blob> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.append('status', params.status);
  if (params?.score_min !== undefined) searchParams.append('score_min', String(params.score_min));

  const queryString = searchParams.toString();
  const url = queryString
    ? `${getApiUrl()}/leads/export?${queryString}`
    : `${getApiUrl()}/leads/export`;

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

/**
 * Delete a lead (GDPR right to be forgotten, admin only).
 */
export async function deleteLead(leadId: string): Promise<{ message: string }> {
  const response = await safeFetch(`${getApiUrl()}/leads/${encodeURIComponent(leadId)}`, {
    method: 'DELETE',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<{ message: string }>(response);
}
