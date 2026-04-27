/**
 * Tests for leads.ts — Lead CRUD, scoring, bulk operations, export, delete.
 */

import { jest } from '@jest/globals';
import type {
  LeadListResponse,
  LeadWithScore,
  LeadDetailResponse,
  LeadScoreBreakdown,
  Lead,
  AgentAssignment,
  BulkOperationResponse,
  RecalculateScoresResponse,
  ScoringStatistics,
} from '../../types';
import { ApiError } from '../client';

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
  getLeads,
  getHighValueLeads,
  getLead,
  getLeadScoreBreakdown,
  updateLead,
  updateLeadStatus,
  assignAgentToLead,
  bulkAssignLeads,
  bulkUpdateLeadStatus,
  recalculateScores,
  getScoringStatistics,
  exportLeads,
  deleteLead,
} from '../leads';

beforeEach(() => {
  jest.clearAllMocks();
});

// =============================================================================
// getLeads
// =============================================================================
describe('getLeads', () => {
  const sampleList: LeadListResponse = {
    items: [],
    total: 0,
    page: 1,
    page_size: 20,
    total_pages: 0,
  };

  it('fetches leads without params', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(sampleList));

    const result = await getLeads();

    expect(result.total).toBe(0);
    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('/leads');
    expect(url).not.toContain('?');
  });

  it('passes page and page_size', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(sampleList));

    await getLeads({ page: 2, page_size: 10 });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('page=2');
    expect(url).toContain('page_size=10');
  });

  it('passes all filter params', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(sampleList));

    await getLeads({
      status: 'new',
      score_min: 50,
      score_max: 90,
      source: 'web',
      has_email: true,
      agent_id: 'agent-1',
      sort_by: 'score',
      sort_order: 'desc',
    });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('status=new');
    expect(url).toContain('score_min=50');
    expect(url).toContain('score_max=90');
    expect(url).toContain('source=web');
    expect(url).toContain('has_email=true');
    expect(url).toContain('agent_id=agent-1');
    expect(url).toContain('sort_by=score');
    expect(url).toContain('sort_order=desc');
  });

  it('omits undefined optional params', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(sampleList));

    await getLeads({ status: 'qualified' });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('status=qualified');
    expect(url).not.toContain('score_min');
    expect(url).not.toContain('score_max');
    expect(url).not.toContain('source');
    expect(url).not.toContain('has_email');
    expect(url).not.toContain('agent_id');
  });

  it('returns leads with items', async () => {
    const leadItem: LeadWithScore = {
      id: 'lead-1',
      visitor_id: 'v-1',
      status: 'new',
      current_score: 75,
      first_seen_at: '2024-01-01T00:00:00Z',
      last_activity_at: '2024-01-02T00:00:00Z',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-02T00:00:00Z',
      consent_given: true,
      interaction_count: 5,
      total_score: 75,
      search_activity_score: 30,
      engagement_score: 25,
      intent_score: 20,
    };
    const data: LeadListResponse = {
      items: [leadItem],
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    };
    mockFetch.mockResolvedValueOnce(okResponse(data));

    const result = await getLeads();
    expect(result.items).toHaveLength(1);
    expect(result.items[0].id).toBe('lead-1');
  });

  it('throws on error response', async () => {
    mockFetch.mockResolvedValueOnce(errorResponse(500, 'Server error'));

    await expect(getLeads()).rejects.toThrow(ApiError);
  });
});

// =============================================================================
// getHighValueLeads
// =============================================================================
describe('getHighValueLeads', () => {
  it('uses default threshold=70 and limit=50', async () => {
    mockFetch.mockResolvedValueOnce(okResponse([]));

    await getHighValueLeads();

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('threshold=70');
    expect(url).toContain('limit=50');
  });

  it('passes custom threshold and limit', async () => {
    mockFetch.mockResolvedValueOnce(okResponse([]));

    await getHighValueLeads(90, 10);

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('threshold=90');
    expect(url).toContain('limit=10');
  });

  it('returns high-value leads', async () => {
    const leads: LeadWithScore[] = [
      {
        id: 'lead-hv',
        visitor_id: 'v-1',
        status: 'qualified',
        current_score: 92,
        first_seen_at: '2024-01-01T00:00:00Z',
        last_activity_at: '2024-01-05T00:00:00Z',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-05T00:00:00Z',
        consent_given: true,
        interaction_count: 10,
        total_score: 92,
        search_activity_score: 35,
        engagement_score: 30,
        intent_score: 27,
      },
    ];
    mockFetch.mockResolvedValueOnce(okResponse(leads));

    const result = await getHighValueLeads();
    expect(result).toHaveLength(1);
    expect(result[0].total_score).toBe(92);
  });
});

// =============================================================================
// getLead
// =============================================================================
describe('getLead', () => {
  it('fetches lead detail by id', async () => {
    const detail: LeadDetailResponse = {
      id: 'lead-1',
      visitor_id: 'v-1',
      status: 'new',
      current_score: 60,
      first_seen_at: '2024-01-01T00:00:00Z',
      last_activity_at: '2024-01-02T00:00:00Z',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-02T00:00:00Z',
      consent_given: true,
      interaction_count: 2,
      total_score: 60,
      search_activity_score: 20,
      engagement_score: 20,
      intent_score: 20,
      recent_interactions: [],
      score_history: [],
    };
    mockFetch.mockResolvedValueOnce(okResponse(detail));

    const result = await getLead('lead-1');

    expect(result.id).toBe('lead-1');
    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('/leads/lead-1');
  });

  it('encodes lead id', async () => {
    mockFetch.mockResolvedValueOnce(
      okResponse({
        id: 'lead/special',
        visitor_id: 'v-1',
        status: 'new',
        current_score: 0,
        first_seen_at: '',
        last_activity_at: '',
        created_at: '',
        updated_at: '',
        consent_given: false,
        interaction_count: 0,
        total_score: 0,
        search_activity_score: 0,
        engagement_score: 0,
        intent_score: 0,
        recent_interactions: [],
        score_history: [],
      })
    );

    await getLead('lead/special');

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('lead%2Fspecial');
  });
});

// =============================================================================
// getLeadScoreBreakdown
// =============================================================================
describe('getLeadScoreBreakdown', () => {
  it('fetches score breakdown for a lead', async () => {
    const breakdown: LeadScoreBreakdown = {
      total_score: 75,
      components: { search_activity: 30, engagement: 25, intent: 20 },
      factors: {},
      weights: { search_activity: 0.4, engagement: 0.35, intent: 0.25 },
      recommendations: ['Increase engagement'],
    };
    mockFetch.mockResolvedValueOnce(okResponse(breakdown));

    const result = await getLeadScoreBreakdown('lead-1');

    expect(result.total_score).toBe(75);
    expect(result.recommendations).toHaveLength(1);
    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('/leads/lead-1/score');
  });
});

// =============================================================================
// updateLead
// =============================================================================
describe('updateLead', () => {
  it('sends PATCH with partial data', async () => {
    const updated: Lead = {
      id: 'lead-1',
      visitor_id: 'v-1',
      status: 'contacted',
      current_score: 60,
      first_seen_at: '2024-01-01T00:00:00Z',
      last_activity_at: '2024-01-02T00:00:00Z',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-03T00:00:00Z',
      consent_given: true,
    };
    mockFetch.mockResolvedValueOnce(okResponse(updated));

    const result = await updateLead('lead-1', { status: 'contacted' });

    expect(result.status).toBe('contacted');
    const [, opts] = mockFetch.mock.calls[0];
    expect(opts.method).toBe('PATCH');
    expect(JSON.parse(opts.body)).toEqual({ status: 'contacted' });
  });

  it('throws on error', async () => {
    mockFetch.mockResolvedValueOnce(errorResponse(404, 'Lead not found'));

    await expect(updateLead('bad', { name: 'x' })).rejects.toThrow(ApiError);
  });
});

// =============================================================================
// updateLeadStatus
// =============================================================================
describe('updateLeadStatus', () => {
  it('sends PATCH with status param', async () => {
    mockFetch.mockResolvedValueOnce(
      okResponse({
        id: 'lead-1',
        visitor_id: 'v-1',
        status: 'qualified',
        current_score: 0,
        first_seen_at: '',
        last_activity_at: '',
        created_at: '',
        updated_at: '',
        consent_given: false,
      })
    );

    await updateLeadStatus('lead-1', 'qualified');

    const [url, opts] = mockFetch.mock.calls[0];
    expect(opts.method).toBe('PATCH');
    expect(url).toContain('status=qualified');
    expect(url).toContain('/leads/lead-1/status');
  });

  it('includes notes when provided', async () => {
    mockFetch.mockResolvedValueOnce(
      okResponse({
        id: 'lead-1',
        visitor_id: 'v-1',
        status: 'contacted',
        current_score: 0,
        first_seen_at: '',
        last_activity_at: '',
        created_at: '',
        updated_at: '',
        consent_given: false,
      })
    );

    await updateLeadStatus('lead-1', 'contacted', 'Left voicemail');

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('notes=Left');
  });

  it('omits notes when not provided', async () => {
    mockFetch.mockResolvedValueOnce(
      okResponse({
        id: 'lead-1',
        visitor_id: 'v-1',
        status: 'new',
        current_score: 0,
        first_seen_at: '',
        last_activity_at: '',
        created_at: '',
        updated_at: '',
        consent_given: false,
      })
    );

    await updateLeadStatus('lead-1', 'new');

    const [url] = mockFetch.mock.calls[0];
    expect(url).not.toContain('notes=');
  });
});

// =============================================================================
// assignAgentToLead
// =============================================================================
describe('assignAgentToLead', () => {
  const assignment: AgentAssignment = {
    id: 'aa-1',
    lead_id: 'lead-1',
    agent_id: 'agent-1',
    is_primary: true,
    is_active: true,
    assigned_at: '2024-01-01T00:00:00Z',
  };

  it('sends POST with agent_id and defaults', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(assignment));

    const result = await assignAgentToLead('lead-1', 'agent-1');

    expect(result.agent_id).toBe('agent-1');
    const [url, opts] = mockFetch.mock.calls[0];
    expect(opts.method).toBe('POST');
    expect(url).toContain('/leads/lead-1/assign');
    const body = JSON.parse(opts.body);
    expect(body.agent_id).toBe('agent-1');
    expect(body.is_primary).toBe(true);
  });

  it('passes notes and is_primary options', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(assignment));

    await assignAgentToLead('lead-1', 'agent-1', {
      notes: 'VIP lead',
      is_primary: false,
    });

    const [, opts] = mockFetch.mock.calls[0];
    const body = JSON.parse(opts.body);
    expect(body.notes).toBe('VIP lead');
    expect(body.is_primary).toBe(false);
  });

  it('defaults is_primary to true when options omitted', async () => {
    mockFetch.mockResolvedValueOnce(okResponse(assignment));

    await assignAgentToLead('lead-1', 'agent-1');

    const [, opts] = mockFetch.mock.calls[0];
    const body = JSON.parse(opts.body);
    expect(body.is_primary).toBe(true);
  });
});

// =============================================================================
// bulkAssignLeads
// =============================================================================
describe('bulkAssignLeads', () => {
  it('sends POST with lead_ids and agent_id', async () => {
    const response: BulkOperationResponse = {
      success_count: 2,
      failed_count: 0,
      message: 'OK',
    };
    mockFetch.mockResolvedValueOnce(okResponse(response));

    const result = await bulkAssignLeads({
      lead_ids: ['lead-1', 'lead-2'],
      agent_id: 'agent-1',
    });

    expect(result.success_count).toBe(2);
    const [url, opts] = mockFetch.mock.calls[0];
    expect(opts.method).toBe('POST');
    expect(url).toContain('/leads/bulk/assign');
  });

  it('includes notes in body', async () => {
    mockFetch.mockResolvedValueOnce(
      okResponse({ success_count: 1, failed_count: 0, message: 'OK' })
    );

    await bulkAssignLeads({
      lead_ids: ['lead-1'],
      agent_id: 'agent-1',
      notes: 'Bulk assignment',
    });

    const [, opts] = mockFetch.mock.calls[0];
    const body = JSON.parse(opts.body);
    expect(body.notes).toBe('Bulk assignment');
  });
});

// =============================================================================
// bulkUpdateLeadStatus
// =============================================================================
describe('bulkUpdateLeadStatus', () => {
  it('sends POST to /leads/bulk/status', async () => {
    const response: BulkOperationResponse = {
      success_count: 3,
      failed_count: 1,
      failed_ids: ['lead-3'],
      message: 'Partial success',
    };
    mockFetch.mockResolvedValueOnce(okResponse(response));

    const result = await bulkUpdateLeadStatus({
      lead_ids: ['lead-1', 'lead-2', 'lead-3'],
      status: 'contacted',
    });

    expect(result.success_count).toBe(3);
    expect(result.failed_count).toBe(1);
    const [url, opts] = mockFetch.mock.calls[0];
    expect(opts.method).toBe('POST');
    expect(url).toContain('/leads/bulk/status');
  });
});

// =============================================================================
// recalculateScores
// =============================================================================
describe('recalculateScores', () => {
  it('sends POST with empty body when no request', async () => {
    const response: RecalculateScoresResponse = {
      recalculated_count: 10,
      failed_count: 0,
      duration_seconds: 2.5,
      message: 'Done',
    };
    mockFetch.mockResolvedValueOnce(okResponse(response));

    const result = await recalculateScores();

    expect(result.recalculated_count).toBe(10);
    const [url, opts] = mockFetch.mock.calls[0];
    expect(opts.method).toBe('POST');
    expect(url).toContain('/leads/scores/recalculate');
    expect(JSON.parse(opts.body)).toEqual({});
  });

  it('sends POST with request body', async () => {
    mockFetch.mockResolvedValueOnce(
      okResponse({ recalculated_count: 2, failed_count: 0, duration_seconds: 0.5, message: '' })
    );

    await recalculateScores({ lead_ids: ['lead-1'], force: true });

    const [, opts] = mockFetch.mock.calls[0];
    const body = JSON.parse(opts.body);
    expect(body.lead_ids).toEqual(['lead-1']);
    expect(body.force).toBe(true);
  });
});

// =============================================================================
// getScoringStatistics
// =============================================================================
describe('getScoringStatistics', () => {
  it('fetches scoring statistics', async () => {
    const stats: ScoringStatistics = {
      total_leads: 100,
      high_value_leads: 20,
      avg_score: 55,
      conversion_rate: 0.15,
      converted_leads: 15,
      new_leads_24h: 5,
      score_distribution: { high_80_100: 20, medium_50_79: 50, low_0_49: 30 },
      scores_calculated_today: 25,
      model_version: 'v1',
      weights: { search_activity: 0.4, engagement: 0.35, intent: 0.25 },
    };
    mockFetch.mockResolvedValueOnce(okResponse(stats));

    const result = await getScoringStatistics();

    expect(result.total_leads).toBe(100);
    const [url, opts] = mockFetch.mock.calls[0];
    expect(opts.method).toBe('GET');
    expect(url).toContain('/leads/scores/statistics');
  });
});

// =============================================================================
// exportLeads
// =============================================================================
describe('exportLeads', () => {
  it('fetches blob without params', async () => {
    const blob = new Blob(['csv data'], { type: 'text/csv' });
    mockFetch.mockResolvedValueOnce({
      ok: true,
      blob: async () => blob,
      status: 200,
    });

    const result = await exportLeads();

    expect(result).toBeInstanceOf(Blob);
    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('/leads/export');
    expect(url).not.toContain('?');
  });

  it('passes status and score_min params', async () => {
    const blob = new Blob(['csv data'], { type: 'text/csv' });
    mockFetch.mockResolvedValueOnce({
      ok: true,
      blob: async () => blob,
      status: 200,
    });

    await exportLeads({ status: 'qualified', score_min: 50 });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('status=qualified');
    expect(url).toContain('score_min=50');
  });

  it('throws ApiError on failure', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Export failed' }),
    });

    await expect(exportLeads()).rejects.toThrow(ApiError);
  });

  it('uses fallback message when json() rejects', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error('json failed');
      },
    });

    await expect(exportLeads()).rejects.toThrow('Export failed');
  });
});

// =============================================================================
// deleteLead
// =============================================================================
describe('deleteLead', () => {
  it('sends DELETE and returns message', async () => {
    mockFetch.mockResolvedValueOnce(okResponse({ message: 'Lead deleted' }));

    const result = await deleteLead('lead-1');

    expect(result.message).toBe('Lead deleted');
    const [url, opts] = mockFetch.mock.calls[0];
    expect(opts.method).toBe('DELETE');
    expect(url).toContain('/leads/lead-1');
  });

  it('encodes lead id', async () => {
    mockFetch.mockResolvedValueOnce(okResponse({ message: 'Deleted' }));

    await deleteLead('lead/special');

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('lead%2Fspecial');
  });

  it('throws on error', async () => {
    mockFetch.mockResolvedValueOnce(errorResponse(404, 'Not found'));

    await expect(deleteLead('bad-id')).rejects.toThrow(ApiError);
  });
});
