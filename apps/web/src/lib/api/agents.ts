/**
 * Agent/Broker API (Task #45) and Agent Performance Analytics API (Task #56).
 */

import type {
  Deal,
  DealCreate,
  DealStatus,
  DealListResponse,
  AgentMetrics,
  TeamComparison,
  PerformanceTrendsResponse,
  CoachingInsightsResponse,
  GoalProgressListResponse,
  TopPerformersResponse,
  AgentsNeedingSupportResponse,
  AgentProfile,
  AgentProfileCreate,
  AgentProfileUpdate,
  AgentProfileListResponse,
  AgentListingListResponse,
  AgentInquiry,
  AgentInquiryCreate,
  AgentInquiryUpdate,
  AgentInquiryListResponse,
  ViewingAppointment,
  ViewingAppointmentCreate,
  ViewingAppointmentUpdate,
  ViewingAppointmentListResponse,
  AgentFilters,
} from '../types';

import { getApiUrl, buildHeaders, safeFetch, handleResponse } from './client';

// Re-export client types used in signatures
export type { ApiErrorCategory } from './client';
export { ApiError } from './client';

// =============================================================================
// Agent Performance Analytics API (Task #56)
// =============================================================================

/**
 * Get current agent's performance metrics.
 */
export async function getAgentMetrics(params?: {
  period_start?: string;
  period_end?: string;
}): Promise<AgentMetrics> {
  const searchParams = new URLSearchParams();
  if (params?.period_start) searchParams.append('period_start', params.period_start);
  if (params?.period_end) searchParams.append('period_end', params.period_end);

  const queryString = searchParams.toString();
  const url = queryString
    ? `${getApiUrl()}/agent-analytics/me?${queryString}`
    : `${getApiUrl()}/agent-analytics/me`;

  const response = await safeFetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<AgentMetrics>(response);
}

/**
 * Get team comparison for current agent.
 */
export async function getTeamComparison(params?: {
  period_start?: string;
  period_end?: string;
}): Promise<TeamComparison> {
  const searchParams = new URLSearchParams();
  if (params?.period_start) searchParams.append('period_start', params.period_start);
  if (params?.period_end) searchParams.append('period_end', params.period_end);

  const queryString = searchParams.toString();
  const url = queryString
    ? `${getApiUrl()}/agent-analytics/me/comparison?${queryString}`
    : `${getApiUrl()}/agent-analytics/me/comparison`;

  const response = await safeFetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<TeamComparison>(response);
}

/**
 * Get performance trends over time.
 */
export async function getPerformanceTrends(params?: {
  interval?: 'day' | 'week' | 'month' | 'quarter';
  periods?: number;
}): Promise<PerformanceTrendsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.interval) searchParams.append('interval', params.interval);
  if (params?.periods) searchParams.append('periods', String(params.periods));

  const response = await safeFetch(
    `${getApiUrl()}/agent-analytics/me/trends?${searchParams.toString()}`,
    {
      method: 'GET',
      headers: buildHeaders(),
      credentials: 'include',
    }
  );
  return handleResponse<PerformanceTrendsResponse>(response);
}

/**
 * Get coaching insights for current agent.
 */
export async function getCoachingInsights(): Promise<CoachingInsightsResponse> {
  const response = await safeFetch(`${getApiUrl()}/agent-analytics/me/insights`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<CoachingInsightsResponse>(response);
}

/**
 * Get goal progress for current agent.
 */
export async function getGoalProgress(): Promise<GoalProgressListResponse> {
  const response = await safeFetch(`${getApiUrl()}/agent-analytics/me/goals`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<GoalProgressListResponse>(response);
}

/**
 * Get top performers (admin only).
 */
export async function getTopPerformers(params?: {
  metric?: 'deals' | 'revenue' | 'conversion';
  limit?: number;
  period_days?: number;
}): Promise<TopPerformersResponse> {
  const searchParams = new URLSearchParams();
  if (params?.metric) searchParams.append('metric', params.metric);
  if (params?.limit) searchParams.append('limit', String(params.limit));
  if (params?.period_days) searchParams.append('period_days', String(params.period_days));

  const response = await safeFetch(
    `${getApiUrl()}/agent-analytics/top-performers?${searchParams.toString()}`,
    {
      method: 'GET',
      headers: buildHeaders(),
      credentials: 'include',
    }
  );
  return handleResponse<TopPerformersResponse>(response);
}

/**
 * Get agents needing support (admin only).
 */
export async function getAgentsNeedingSupport(params?: {
  threshold_days?: number;
}): Promise<AgentsNeedingSupportResponse> {
  const searchParams = new URLSearchParams();
  if (params?.threshold_days) searchParams.append('threshold_days', String(params.threshold_days));

  const response = await safeFetch(
    `${getApiUrl()}/agent-analytics/needs-support?${searchParams.toString()}`,
    {
      method: 'GET',
      headers: buildHeaders(),
      credentials: 'include',
    }
  );
  return handleResponse<AgentsNeedingSupportResponse>(response);
}

/**
 * Create a new deal.
 */
export async function createDeal(dealData: DealCreate): Promise<Deal> {
  const response = await safeFetch(`${getApiUrl()}/agent-analytics/deals`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(dealData),
  });
  return handleResponse<Deal>(response);
}

/**
 * Get deals for current agent.
 */
export async function getMyDeals(params?: {
  status?: DealStatus;
  page?: number;
  page_size?: number;
}): Promise<DealListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.append('status', params.status);
  if (params?.page) searchParams.append('page', String(params.page));
  if (params?.page_size) searchParams.append('page_size', String(params.page_size));

  const response = await safeFetch(
    `${getApiUrl()}/agent-analytics/deals?${searchParams.toString()}`,
    {
      method: 'GET',
      headers: buildHeaders(),
      credentials: 'include',
    }
  );
  return handleResponse<DealListResponse>(response);
}

/**
 * Get a specific deal by ID.
 */
export async function getDeal(dealId: string): Promise<Deal> {
  const response = await safeFetch(
    `${getApiUrl()}/agent-analytics/deals/${encodeURIComponent(dealId)}`,
    {
      method: 'GET',
      headers: buildHeaders(),
      credentials: 'include',
    }
  );
  return handleResponse<Deal>(response);
}

/**
 * Update a deal.
 */
export async function updateDeal(
  dealId: string,
  data: Partial<{
    status: DealStatus;
    deal_value: number;
    notes: string;
  }>
): Promise<Deal> {
  const response = await safeFetch(
    `${getApiUrl()}/agent-analytics/deals/${encodeURIComponent(dealId)}`,
    {
      method: 'PATCH',
      headers: buildHeaders(),
      credentials: 'include',
      body: JSON.stringify(data),
    }
  );
  return handleResponse<Deal>(response);
}

// =============================================================================
// Agent/Broker API (Task #45)
// =============================================================================

/**
 * Get list of agents with optional filters (public endpoint).
 */
export async function getAgents(
  params?: AgentFilters & { page?: number; page_size?: number }
): Promise<AgentProfileListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.append('page', String(params.page));
  if (params?.page_size) searchParams.append('page_size', String(params.page_size));
  if (params?.city) searchParams.append('city', params.city);
  if (params?.specialty) searchParams.append('specialty', params.specialty);
  if (params?.min_rating !== undefined) {
    searchParams.append('min_rating', String(params.min_rating));
  }
  if (params?.agency_id) searchParams.append('agency_id', params.agency_id);
  if (params?.sort_by) searchParams.append('sort_by', params.sort_by);
  if (params?.is_verified !== undefined) {
    searchParams.append('is_verified', String(params.is_verified));
  }
  if (params?.is_active !== undefined) {
    searchParams.append('is_active', String(params.is_active));
  }

  const queryString = searchParams.toString();
  const url = queryString ? `${getApiUrl()}/agents?${queryString}` : `${getApiUrl()}/agents`;

  const response = await safeFetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<AgentProfileListResponse>(response);
}

/**
 * Get a specific agent by ID (public endpoint).
 */
export async function getAgent(agentId: string): Promise<AgentProfile> {
  const response = await safeFetch(`${getApiUrl()}/agents/${encodeURIComponent(agentId)}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<AgentProfile>(response);
}

/**
 * Get listings for a specific agent (public endpoint).
 */
export async function getAgentListings(
  agentId: string,
  params?: { listing_type?: 'sale' | 'rent'; page?: number; page_size?: number }
): Promise<AgentListingListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.listing_type) searchParams.append('listing_type', params.listing_type);
  if (params?.page) searchParams.append('page', String(params.page));
  if (params?.page_size) searchParams.append('page_size', String(params.page_size));

  const queryString = searchParams.toString();
  const url = queryString
    ? `${getApiUrl()}/agents/${encodeURIComponent(agentId)}/listings?${queryString}`
    : `${getApiUrl()}/agents/${encodeURIComponent(agentId)}/listings`;

  const response = await safeFetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<AgentListingListResponse>(response);
}

/**
 * Send an inquiry to an agent (public endpoint).
 */
export async function contactAgent(
  agentId: string,
  data: AgentInquiryCreate
): Promise<AgentInquiry> {
  const response = await safeFetch(`${getApiUrl()}/agents/${encodeURIComponent(agentId)}/contact`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<AgentInquiry>(response);
}

/**
 * Schedule a viewing appointment with an agent (public endpoint).
 */
export async function scheduleViewing(
  agentId: string,
  data: ViewingAppointmentCreate
): Promise<ViewingAppointment> {
  const response = await safeFetch(
    `${getApiUrl()}/agents/${encodeURIComponent(agentId)}/schedule-viewing`,
    {
      method: 'POST',
      headers: buildHeaders(),
      credentials: 'include',
      body: JSON.stringify(data),
    }
  );
  return handleResponse<ViewingAppointment>(response);
}

/**
 * Get current agent's own profile (protected - requires agent role).
 */
export async function getOwnAgentProfile(): Promise<AgentProfile | null> {
  const response = await safeFetch(`${getApiUrl()}/agents/profile`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<AgentProfile | null>(response);
}

/**
 * Create agent profile (protected - requires agent role).
 */
export async function createAgentProfile(data: AgentProfileCreate): Promise<AgentProfile> {
  const response = await safeFetch(`${getApiUrl()}/agents/profile`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<AgentProfile>(response);
}

/**
 * Update current agent's profile (protected - requires agent role).
 */
export async function updateOwnAgentProfile(data: AgentProfileUpdate): Promise<AgentProfile> {
  const response = await safeFetch(`${getApiUrl()}/agents/profile`, {
    method: 'PATCH',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<AgentProfile>(response);
}

/**
 * Get inquiries for current agent (protected - requires agent role).
 */
export async function getOwnInquiries(params?: {
  status?: 'new' | 'read' | 'responded' | 'closed';
  page?: number;
  page_size?: number;
}): Promise<AgentInquiryListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.append('status', params.status);
  if (params?.page) searchParams.append('page', String(params.page));
  if (params?.page_size) searchParams.append('page_size', String(params.page_size));

  const queryString = searchParams.toString();
  const url = queryString
    ? `${getApiUrl()}/agents/inquiries?${queryString}`
    : `${getApiUrl()}/agents/inquiries`;

  const response = await safeFetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<AgentInquiryListResponse>(response);
}

/**
 * Update an inquiry (protected - requires agent role).
 */
export async function updateInquiry(
  inquiryId: string,
  data: AgentInquiryUpdate
): Promise<AgentInquiry> {
  const response = await safeFetch(
    `${getApiUrl()}/agents/inquiries/${encodeURIComponent(inquiryId)}`,
    {
      method: 'PATCH',
      headers: buildHeaders(),
      credentials: 'include',
      body: JSON.stringify(data),
    }
  );
  return handleResponse<AgentInquiry>(response);
}

/**
 * Get appointments for current agent (protected - requires agent role).
 */
export async function getOwnAppointments(params?: {
  status?: 'requested' | 'confirmed' | 'cancelled' | 'completed';
  page?: number;
  page_size?: number;
}): Promise<ViewingAppointmentListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.append('status', params.status);
  if (params?.page) searchParams.append('page', String(params.page));
  if (params?.page_size) searchParams.append('page_size', String(params.page_size));

  const queryString = searchParams.toString();
  const url = queryString
    ? `${getApiUrl()}/agents/appointments?${queryString}`
    : `${getApiUrl()}/agents/appointments`;

  const response = await safeFetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<ViewingAppointmentListResponse>(response);
}

/**
 * Update an appointment (protected - requires agent role).
 */
export async function updateAppointment(
  appointmentId: string,
  data: ViewingAppointmentUpdate
): Promise<ViewingAppointment> {
  const response = await safeFetch(
    `${getApiUrl()}/agents/appointments/${encodeURIComponent(appointmentId)}`,
    {
      method: 'PATCH',
      headers: buildHeaders(),
      credentials: 'include',
      body: JSON.stringify(data),
    }
  );
  return handleResponse<ViewingAppointment>(response);
}
