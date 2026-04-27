/**
 * Tests for agents.ts API module.
 * Covers all exported functions for both Agent Performance Analytics (Task #56)
 * and Agent/Broker API (Task #45).
 */

import { describe, it, expect, jest, beforeEach } from '@jest/globals';

// Mock fetch globally before any imports
const mockFetch = jest.fn();
(globalThis as unknown as { fetch: jest.Mock }).fetch = mockFetch;

// Import after fetch is mocked
import {
  getAgentMetrics,
  getTeamComparison,
  getPerformanceTrends,
  getCoachingInsights,
  getGoalProgress,
  getTopPerformers,
  getAgentsNeedingSupport,
  createDeal,
  getMyDeals,
  getDeal,
  updateDeal,
  getAgents,
  getAgent,
  getAgentListings,
  contactAgent,
  scheduleViewing,
  getOwnAgentProfile,
  createAgentProfile,
  updateOwnAgentProfile,
  getOwnInquiries,
  updateInquiry,
  getOwnAppointments,
  updateAppointment,
  ApiError,
} from '@/lib/api/agents';

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

/** Verify that mockFetch was called with a URL starting with the expected path. */
function expectCalledWithPath(pathPrefix: string) {
  const calledUrl = mockFetch.mock.calls[0][0] as string;
  expect(calledUrl).toContain(pathPrefix);
}

// ---------------------------------------------------------------------------
// Shared sample data
// ---------------------------------------------------------------------------

const sampleAgentMetrics = {
  total_leads: 42,
  active_leads: 15,
  new_leads_week: 5,
  high_value_leads: 8,
  total_deals: 12,
  active_deals: 3,
  closed_deals: 7,
  fell_through_deals: 2,
  lead_to_qualified_rate: 0.35,
  qualified_to_deal_rate: 0.5,
  overall_conversion_rate: 0.17,
  avg_time_to_first_contact_hours: 2.5,
  avg_time_to_qualify_days: 14,
  avg_time_to_close_days: 45,
  total_deal_value: 2500000,
  avg_deal_value: 208333,
  total_commission: 62500,
  pending_commission: 12500,
  top_property_types: [{ type: 'apartment', count: 8, percentage: 66.7 }],
  top_locations: [{ location: 'Krakow', count: 6, percentage: 50 }],
  avg_lead_score: 72,
  deals_change_percent: 10,
  revenue_change_percent: 15,
};

const sampleTeamComparison = {
  agent_id: 'agent-1',
  agent_name: 'John Doe',
  rank_by_deals: 3,
  rank_by_revenue: 2,
  rank_by_conversion: 5,
  total_agents: 20,
  deals_vs_avg_percent: 15,
  revenue_vs_avg_percent: 20,
  conversion_vs_avg_percent: -5,
  time_to_close_vs_avg_percent: -10,
  team_avg_deals: 8,
  team_avg_revenue: 200000,
  team_avg_conversion: 0.2,
  team_avg_time_to_close_days: 50,
};

const sampleTrends = {
  trends: [
    {
      period: '2024-01',
      period_start: '2024-01-01',
      period_end: '2024-01-31',
      leads: 10,
      deals_closed: 2,
      revenue: 500000,
      conversion_rate: 0.2,
      avg_deal_value: 250000,
    },
  ],
  interval: 'month',
};

const sampleInsights = {
  insights: [
    {
      category: 'strength' as const,
      title: 'High conversion rate',
      description: 'Your conversion rate is above team average.',
      actionable_recommendation: 'Keep following up with qualified leads promptly.',
      priority: 1,
    },
  ],
};

const sampleGoals = {
  goals: [
    {
      id: 'goal-1',
      goal_type: 'revenue',
      target_value: 500000,
      current_value: 350000,
      progress_percent: 70,
      period_type: 'monthly',
      period_start: '2024-01-01',
      period_end: '2024-01-31',
      is_achieved: false,
      days_remaining: 10,
    },
  ],
};

const sampleTopPerformers = {
  performers: [{ agent_id: 'a1', agent_name: 'Alice', metric_value: 25, rank: 1 }],
  metric: 'deals',
  period_days: 30,
};

const sampleAgentsNeedingSupport = {
  agents: [
    {
      agent_id: 'a5',
      agent_name: 'Bob',
      days_without_deal: 45,
      total_leads: 10,
      conversion_rate: 0.05,
      suggested_actions: ['Review lead follow-up process'],
    },
  ],
  threshold_days: 30,
};

const sampleDeal = {
  id: 'deal-1',
  lead_id: 'lead-1',
  agent_id: 'agent-1',
  property_id: 'prop-1',
  deal_type: 'sale',
  deal_value: 300000,
  currency: 'USD',
  status: 'offer_accepted',
  offer_submitted_at: '2024-01-10T00:00:00Z',
  created_at: '2024-01-10T00:00:00Z',
};

const sampleDealList = {
  items: [sampleDeal],
  total: 1,
  page: 1,
  page_size: 20,
};

const sampleAgentProfile = {
  id: 'agent-1',
  user_id: 'user-1',
  name: 'John Doe',
  email: 'john@example.com',
  agency_name: 'Best Realty',
  license_number: 'LIC-123',
  specialties: ['residential', 'luxury'],
  service_areas: ['Krakow', 'Warsaw'],
  average_rating: 4.5,
  total_reviews: 30,
  total_sales: 50,
  total_rentals: 20,
  is_verified: true,
  is_active: true,
  created_at: '2023-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const sampleAgentProfileList = {
  items: [sampleAgentProfile],
  total: 1,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

const sampleAgentListings = {
  items: [
    {
      id: 'listing-1',
      agent_id: 'agent-1',
      property_id: 'prop-1',
      listing_type: 'sale',
      is_primary: true,
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
    },
  ],
  total: 1,
};

const sampleInquiry = {
  id: 'inq-1',
  agent_id: 'agent-1',
  name: 'Jane Smith',
  email: 'jane@example.com',
  inquiry_type: 'property',
  message: 'I am interested in this property.',
  status: 'new',
  created_at: '2024-01-15T00:00:00Z',
};

const sampleAppointment = {
  id: 'apt-1',
  agent_id: 'agent-1',
  client_name: 'Jane Smith',
  client_email: 'jane@example.com',
  proposed_datetime: '2024-02-01T10:00:00Z',
  duration_minutes: 60,
  status: 'requested',
  created_at: '2024-01-15T00:00:00Z',
  updated_at: '2024-01-15T00:00:00Z',
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('agents.ts API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockReset();
  });

  // =========================================================================
  // Agent Performance Analytics (Task #56)
  // =========================================================================

  describe('getAgentMetrics', () => {
    it('fetches agent metrics without params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleAgentMetrics));

      const result = await getAgentMetrics();

      expect(mockFetch).toHaveBeenCalledTimes(1);
      expectCalledWithPath(`${API_BASE}/agent-analytics/me`);
      expect(result.total_leads).toBe(42);
      expect(result.closed_deals).toBe(7);
    });

    it('appends period query params when provided', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleAgentMetrics));

      await getAgentMetrics({ period_start: '2024-01-01', period_end: '2024-01-31' });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('period_start=2024-01-01');
      expect(calledUrl).toContain('period_end=2024-01-31');
    });

    it('throws ApiError on non-2xx response', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Unauthorized', 401));

      await expect(getAgentMetrics()).rejects.toThrow(ApiError);
    });
  });

  describe('getTeamComparison', () => {
    it('fetches team comparison without params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleTeamComparison));

      const result = await getTeamComparison();

      expectCalledWithPath(`${API_BASE}/agent-analytics/me/comparison`);
      expect(result.rank_by_deals).toBe(3);
    });

    it('appends period query params when provided', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleTeamComparison));

      await getTeamComparison({ period_start: '2024-01-01' });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('period_start=2024-01-01');
      expect(calledUrl).not.toContain('period_end');
    });

    it('throws on server error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Internal Server Error', 500));

      await expect(getTeamComparison()).rejects.toThrow(ApiError);
    });
  });

  describe('getPerformanceTrends', () => {
    it('fetches trends with interval and periods params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleTrends));

      const result = await getPerformanceTrends({ interval: 'week', periods: 12 });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('interval=week');
      expect(calledUrl).toContain('periods=12');
      expect(result.interval).toBe('month');
    });

    it('fetches trends without params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleTrends));

      await getPerformanceTrends();

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/agent-analytics/me/trends?`);
    });
  });

  describe('getCoachingInsights', () => {
    it('fetches coaching insights', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleInsights));

      const result = await getCoachingInsights();

      expectCalledWithPath(`${API_BASE}/agent-analytics/me/insights`);
      expect(result.insights).toHaveLength(1);
      expect(result.insights[0].category).toBe('strength');
    });
  });

  describe('getGoalProgress', () => {
    it('fetches goal progress', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleGoals));

      const result = await getGoalProgress();

      expectCalledWithPath(`${API_BASE}/agent-analytics/me/goals`);
      expect(result.goals).toHaveLength(1);
      expect(result.goals[0].goal_type).toBe('revenue');
    });
  });

  describe('getTopPerformers', () => {
    it('fetches top performers with all params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleTopPerformers));

      const result = await getTopPerformers({ metric: 'revenue', limit: 5, period_days: 90 });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('metric=revenue');
      expect(calledUrl).toContain('limit=5');
      expect(calledUrl).toContain('period_days=90');
      expect(result.metric).toBe('deals');
    });

    it('fetches top performers without params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleTopPerformers));

      await getTopPerformers();
      expectCalledWithPath(`${API_BASE}/agent-analytics/top-performers`);
    });
  });

  describe('getAgentsNeedingSupport', () => {
    it('fetches agents needing support with threshold', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleAgentsNeedingSupport));

      const result = await getAgentsNeedingSupport({ threshold_days: 60 });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('threshold_days=60');
      expect(result.agents).toHaveLength(1);
    });

    it('fetches agents needing support without params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleAgentsNeedingSupport));

      await getAgentsNeedingSupport();
      expectCalledWithPath(`${API_BASE}/agent-analytics/needs-support`);
    });
  });

  // =========================================================================
  // Deals
  // =========================================================================

  describe('createDeal', () => {
    it('creates a deal via POST', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleDeal));

      const dealData = {
        lead_id: 'lead-1',
        deal_type: 'sale' as const,
        deal_value: 300000,
      };
      const result = await createDeal(dealData);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      expectCalledWithPath(`${API_BASE}/agent-analytics/deals`);

      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual(dealData);
      expect(result.id).toBe('deal-1');
    });
  });

  describe('getMyDeals', () => {
    it('fetches deals with status and pagination params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleDealList));

      const result = await getMyDeals({ status: 'offer_accepted', page: 2, page_size: 10 });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('status=offer_accepted');
      expect(calledUrl).toContain('page=2');
      expect(calledUrl).toContain('page_size=10');
      expect(result.items).toHaveLength(1);
    });

    it('fetches deals without params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleDealList));

      await getMyDeals();
      expectCalledWithPath(`${API_BASE}/agent-analytics/deals`);
    });
  });

  describe('getDeal', () => {
    it('fetches a specific deal by ID', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleDeal));

      const result = await getDeal('deal-1');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/agent-analytics/deals/deal-1`);
      expect(result.id).toBe('deal-1');
    });

    it('encodes deal ID with special characters', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleDeal));

      await getDeal('deal/slash');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('deal%2Fslash');
    });
  });

  describe('updateDeal', () => {
    it('updates a deal via PATCH', async () => {
      const updatedDeal = { ...sampleDeal, status: 'contract_signed' };
      mockFetch.mockResolvedValueOnce(createMockResponse(updatedDeal));

      const result = await updateDeal('deal-1', { status: 'contract_signed' });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/agent-analytics/deals/deal-1`);

      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('PATCH');
      expect(JSON.parse(init.body as string)).toEqual({ status: 'contract_signed' });
      expect(result.status).toBe('contract_signed');
    });

    it('updates deal value and notes', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleDeal));

      await updateDeal('deal-1', { deal_value: 350000, notes: 'Price updated' });

      const init = mockFetch.mock.calls[0][1] as RequestInit;
      const body = JSON.parse(init.body as string);
      expect(body.deal_value).toBe(350000);
      expect(body.notes).toBe('Price updated');
    });
  });

  // =========================================================================
  // Agent/Broker API (Task #45)
  // =========================================================================

  describe('getAgents', () => {
    it('fetches agents without filters', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleAgentProfileList));

      const result = await getAgents();

      expectCalledWithPath(`${API_BASE}/agents`);
      expect(result.items).toHaveLength(1);
    });

    it('appends all filter params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleAgentProfileList));

      await getAgents({
        page: 2,
        page_size: 10,
        city: 'Krakow',
        specialty: 'luxury',
        min_rating: 4,
        agency_id: 'agency-1',
        sort_by: 'rating',
        is_verified: true,
        is_active: true,
      });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('page=2');
      expect(calledUrl).toContain('page_size=10');
      expect(calledUrl).toContain('city=Krakow');
      expect(calledUrl).toContain('specialty=luxury');
      expect(calledUrl).toContain('min_rating=4');
      expect(calledUrl).toContain('agency_id=agency-1');
      expect(calledUrl).toContain('sort_by=rating');
      expect(calledUrl).toContain('is_verified=true');
      expect(calledUrl).toContain('is_active=true');
    });

    it('omits undefined optional params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleAgentProfileList));

      await getAgents({ city: 'Warsaw' });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('city=Warsaw');
      expect(calledUrl).not.toContain('specialty');
      expect(calledUrl).not.toContain('page_size');
    });
  });

  describe('getAgent', () => {
    it('fetches a single agent by ID', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleAgentProfile));

      const result = await getAgent('agent-1');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/agents/agent-1`);
      expect(result.name).toBe('John Doe');
    });

    it('encodes agent ID', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleAgentProfile));

      await getAgent('agent with spaces');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('agent%20with%20spaces');
    });
  });

  describe('getAgentListings', () => {
    it('fetches agent listings without params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleAgentListings));

      const result = await getAgentListings('agent-1');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/agents/agent-1/listings`);
      expect(result.total).toBe(1);
    });

    it('appends listing_type and pagination params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleAgentListings));

      await getAgentListings('agent-1', { listing_type: 'rent', page: 1, page_size: 5 });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('listing_type=rent');
      expect(calledUrl).toContain('page=1');
      expect(calledUrl).toContain('page_size=5');
    });
  });

  describe('contactAgent', () => {
    it('sends an inquiry via POST', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleInquiry));

      const data = {
        name: 'Jane Smith',
        email: 'jane@example.com',
        inquiry_type: 'property' as const,
        message: 'I am interested in this property.',
      };
      const result = await contactAgent('agent-1', data);

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/agents/agent-1/contact`);

      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual(data);
      expect(result.id).toBe('inq-1');
    });
  });

  describe('scheduleViewing', () => {
    it('schedules a viewing via POST', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleAppointment));

      const data = {
        property_id: 'prop-1',
        proposed_datetime: '2024-02-01T10:00:00Z',
        client_name: 'Jane Smith',
        client_email: 'jane@example.com',
      };
      const result = await scheduleViewing('agent-1', data);

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/agents/agent-1/schedule-viewing`);

      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual(data);
      expect(result.id).toBe('apt-1');
    });
  });

  describe('getOwnAgentProfile', () => {
    it('fetches own profile', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleAgentProfile));

      const result = await getOwnAgentProfile();

      expectCalledWithPath(`${API_BASE}/agents/profile`);
      expect(result?.name).toBe('John Doe');
    });

    it('returns null when profile not found', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(null));

      const result = await getOwnAgentProfile();
      expect(result).toBeNull();
    });
  });

  describe('createAgentProfile', () => {
    it('creates agent profile via POST', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleAgentProfile));

      const data = {
        agency_name: 'Best Realty',
        specialties: ['residential'],
      };
      const result = await createAgentProfile(data);

      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual(data);
      expect(result.id).toBe('agent-1');
    });
  });

  describe('updateOwnAgentProfile', () => {
    it('updates own profile via PATCH', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleAgentProfile));

      const data = { bio: 'Updated bio text' };
      const result = await updateOwnAgentProfile(data);

      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('PATCH');
      expect(JSON.parse(init.body as string)).toEqual(data);
      expect(result.id).toBe('agent-1');
    });
  });

  describe('getOwnInquiries', () => {
    it('fetches inquiries without params', async () => {
      mockFetch.mockResolvedValueOnce(
        createMockResponse({
          items: [sampleInquiry],
          total: 1,
          page: 1,
          page_size: 20,
          total_pages: 1,
        })
      );

      const result = await getOwnInquiries();

      expectCalledWithPath(`${API_BASE}/agents/inquiries`);
      expect(result.items).toHaveLength(1);
    });

    it('appends status and pagination params', async () => {
      mockFetch.mockResolvedValueOnce(
        createMockResponse({ items: [], total: 0, page: 1, page_size: 10, total_pages: 0 })
      );

      await getOwnInquiries({ status: 'new', page: 2, page_size: 10 });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('status=new');
      expect(calledUrl).toContain('page=2');
      expect(calledUrl).toContain('page_size=10');
    });
  });

  describe('updateInquiry', () => {
    it('updates an inquiry via PATCH', async () => {
      const updated = { ...sampleInquiry, status: 'read' };
      mockFetch.mockResolvedValueOnce(createMockResponse(updated));

      const result = await updateInquiry('inq-1', { status: 'read' });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/agents/inquiries/inq-1`);

      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('PATCH');
      expect(JSON.parse(init.body as string)).toEqual({ status: 'read' });
      expect(result.status).toBe('read');
    });
  });

  describe('getOwnAppointments', () => {
    it('fetches appointments without params', async () => {
      mockFetch.mockResolvedValueOnce(
        createMockResponse({
          items: [sampleAppointment],
          total: 1,
          page: 1,
          page_size: 20,
          total_pages: 1,
        })
      );

      const result = await getOwnAppointments();

      expectCalledWithPath(`${API_BASE}/agents/appointments`);
      expect(result.items).toHaveLength(1);
    });

    it('appends status and pagination params', async () => {
      mockFetch.mockResolvedValueOnce(
        createMockResponse({ items: [], total: 0, page: 1, page_size: 5, total_pages: 0 })
      );

      await getOwnAppointments({ status: 'confirmed', page: 3, page_size: 5 });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('status=confirmed');
      expect(calledUrl).toContain('page=3');
      expect(calledUrl).toContain('page_size=5');
    });
  });

  describe('updateAppointment', () => {
    it('updates an appointment via PATCH', async () => {
      const updated = { ...sampleAppointment, status: 'confirmed' };
      mockFetch.mockResolvedValueOnce(createMockResponse(updated));

      const result = await updateAppointment('apt-1', { status: 'confirmed' });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/agents/appointments/apt-1`);

      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('PATCH');
      expect(result.status).toBe('confirmed');
    });

    it('passes all update fields in the request body', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleAppointment));

      const updateData = {
        proposed_datetime: '2024-03-01T14:00:00Z',
        confirmed_datetime: '2024-03-01T14:00:00Z',
        duration_minutes: 90,
        status: 'confirmed' as const,
        notes: 'Client confirmed',
        cancellation_reason: undefined as unknown as string,
      };
      await updateAppointment('apt-1', updateData);

      const init = mockFetch.mock.calls[0][1] as RequestInit;
      const body = JSON.parse(init.body as string);
      expect(body.proposed_datetime).toBe('2024-03-01T14:00:00Z');
      expect(body.duration_minutes).toBe(90);
      expect(body.status).toBe('confirmed');
      expect(body.notes).toBe('Client confirmed');
    });
  });

  // =========================================================================
  // Error handling
  // =========================================================================

  describe('error handling', () => {
    it('propagates ApiError with correct properties on 404', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Not found', 404));

      try {
        await getAgent('nonexistent');
        fail('Expected ApiError to be thrown');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        const apiErr = error as ApiError;
        expect(apiErr.status).toBe(404);
        expect(apiErr.message).toBe('Not found');
        expect(apiErr.category).toBe('not_found');
      }
    });

    it('propagates ApiError on 500', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Server error', 500));

      await expect(getCoachingInsights()).rejects.toThrow(ApiError);
      await expect(getCoachingInsights()).rejects.toThrow();
    });

    it('propagates ApiError on 429 rate limit', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Rate limited', 429));

      try {
        await getGoalProgress();
        fail('Expected ApiError to be thrown');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).category).toBe('rate_limit');
        expect((error as ApiError).isRetryable).toBe(true);
      }
    });

    it('handles network failure (fetch throws)', async () => {
      mockFetch.mockRejectedValue(new TypeError('Failed to fetch'));

      try {
        await getAgentMetrics();
        fail('Expected ApiError');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).category).toBe('network');
        expect((error as ApiError).status).toBe(0);
      }
    });

    it('handles non-JSON error response body', async () => {
      const response = {
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        headers: new Headers(),
        json: async () => {
          throw new Error('Not JSON');
        },
        text: async () => 'Something went terribly wrong',
      } as Response;
      mockFetch.mockResolvedValueOnce(response);

      try {
        await getTeamComparison();
        fail('Expected ApiError');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).message).toBe('Something went terribly wrong');
      }
    });

    it('handles error response with non-string detail', async () => {
      const body = { detail: { field: 'email', msg: 'Invalid email' } };
      const response = {
        ok: false,
        status: 422,
        statusText: 'Unprocessable Entity',
        headers: new Headers(),
        json: async () => body,
        text: async () => JSON.stringify(body),
      } as Response;
      mockFetch.mockResolvedValueOnce(response);

      try {
        await createDeal({ lead_id: '1', deal_type: 'sale', deal_value: 100 });
        fail('Expected ApiError');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).category).toBe('validation');
        // detail is not a string, so the stringified version should be used
        expect((error as ApiError).message).toContain('field');
      }
    });

    it('handles error response with no detail field', async () => {
      const body = { error: 'unknown' };
      const response = {
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        headers: new Headers(),
        json: async () => body,
        text: async () => JSON.stringify(body),
      } as Response;
      mockFetch.mockResolvedValueOnce(response);

      try {
        await getAgents();
        fail('Expected ApiError');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        // When no detail field, the raw text is used as message
        expect((error as ApiError).message).toBe(JSON.stringify(body));
      }
    });
  });

  // =========================================================================
  // Request shape verification
  // =========================================================================

  describe('request shape', () => {
    it('includes credentials: include in all requests', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleAgentMetrics));

      await getAgentMetrics();

      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.credentials).toBe('include');
    });

    it('includes Content-Type: application/json header', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleAgentMetrics));

      await getAgentMetrics();

      const init = mockFetch.mock.calls[0][1] as RequestInit;
      const headers = init.headers as Record<string, string>;
      expect(headers['Content-Type']).toBe('application/json');
    });

    it('uses GET method for read operations', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleAgentMetrics));

      await getAgentMetrics();

      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('GET');
    });

    it('uses POST method for create operations', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleInquiry));

      await contactAgent('agent-1', {
        name: 'Test',
        email: 'test@example.com',
        inquiry_type: 'general',
        message: 'Hello',
      });

      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
    });

    it('uses PATCH method for update operations', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse(sampleDeal));

      await updateDeal('deal-1', { notes: 'updated' });

      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('PATCH');
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
      expect(err.status).toBe(500);
    });
  });
});
