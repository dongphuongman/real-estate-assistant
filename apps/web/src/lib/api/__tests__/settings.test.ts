/**
 * Tests for settings.ts API module.
 * Covers notification settings, model catalog, model preferences,
 * per-task model preferences, system defaults, cost estimate, unsubscribe.
 */

import { describe, it, expect, jest, beforeEach } from '@jest/globals';

// Mock fetch globally before any imports
const mockFetch = jest.fn();
(globalThis as unknown as { fetch: jest.Mock }).fetch = mockFetch;

import {
  getNotificationSettings,
  updateNotificationSettings,
  sendNotificationPreview,
  unsubscribeByToken,
  getModelsCatalog,
  testModelRuntime,
  getModelPreferences,
  updateModelPreferences,
  getTaskModelPreferences,
  getTaskModelPreference,
  createTaskModelPreference,
  updateTaskModelPreference,
  deleteTaskModelPreference,
  getSystemModelDefaults,
  getModelCostEstimate,
  ApiError,
} from '@/lib/api/settings';

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

function expectCalledWithPath(pathPrefix: string) {
  const calledUrl = mockFetch.mock.calls[0][0] as string;
  expect(calledUrl).toContain(pathPrefix);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('settings.ts API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockReset();
  });

  // =========================================================================
  // getNotificationSettings
  // =========================================================================

  describe('getNotificationSettings', () => {
    it('fetches notification settings via GET', async () => {
      const result = { email_notifications: true, push_notifications: false, frequency: 'daily' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getNotificationSettings();

      expectCalledWithPath(`${API_BASE}/settings/notifications`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('GET');
      expect(response.email_notifications).toBe(true);
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Unauthorized', 401));

      await expect(getNotificationSettings()).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // updateNotificationSettings
  // =========================================================================

  describe('updateNotificationSettings', () => {
    it('updates notification settings via PUT', async () => {
      const result = { email_notifications: false, push_notifications: true, frequency: 'weekly' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const input = { email_notifications: false, push_notifications: true, frequency: 'weekly' };
      const response = await updateNotificationSettings(input);

      expectCalledWithPath(`${API_BASE}/settings/notifications`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('PUT');
      expect(JSON.parse(init.body as string)).toEqual(input);
      expect(response.frequency).toBe('weekly');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Bad request', 400));

      await expect(updateNotificationSettings({})).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // sendNotificationPreview
  // =========================================================================

  describe('sendNotificationPreview', () => {
    it('sends notification preview via POST', async () => {
      const result = { success: true, message: 'Preview sent' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const input = { channel: 'email', template_name: 'test' };
      const response = await sendNotificationPreview(input);

      expectCalledWithPath(`${API_BASE}/settings/notifications/preview`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual(input);
      expect(response.success).toBe(true);
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(sendNotificationPreview({ channel: 'bad' })).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // unsubscribeByToken
  // =========================================================================

  describe('unsubscribeByToken', () => {
    it('unsubscribes with token only via POST', async () => {
      const result = { success: true, message: 'Unsubscribed' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await unsubscribeByToken('token-abc');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/settings/notifications/unsubscribe/token-abc`);
      expect(calledUrl).not.toContain('notification_type');
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(response.success).toBe(true);
    });

    it('appends notification_type when provided', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ success: true, message: 'OK' }));

      await unsubscribeByToken('token-abc', 'market_report');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('notification_type=market_report');
    });

    it('encodes notification_type with special characters', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ success: true, message: 'OK' }));

      await unsubscribeByToken('tok', 'type with spaces');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('notification_type=type%20with%20spaces');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Invalid token', 400));

      await expect(unsubscribeByToken('bad-token')).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // getModelsCatalog
  // =========================================================================

  describe('getModelsCatalog', () => {
    it('fetches models catalog via GET', async () => {
      const result = [{ provider: 'openai', models: [{ name: 'gpt-4', available: true }] }];
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getModelsCatalog();

      expectCalledWithPath(`${API_BASE}/settings/models`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('GET');
      expect(response).toHaveLength(1);
      expect(response[0].provider).toBe('openai');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Server error', 500));

      await expect(getModelsCatalog()).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // testModelRuntime
  // =========================================================================

  describe('testModelRuntime', () => {
    it('tests model runtime via GET', async () => {
      const result = { provider: 'openai', status: 'ok', latency_ms: 150 };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await testModelRuntime('openai');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/settings/test-runtime?`);
      expect(calledUrl).toContain('provider=openai');
      expect(response.status).toBe('ok');
    });

    it('encodes provider name', async () => {
      mockFetch.mockResolvedValueOnce(
        createMockResponse({ provider: 'test provider', status: 'ok' })
      );

      await testModelRuntime('test provider');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('provider=test%20provider');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(testModelRuntime('bad')).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // getModelPreferences
  // =========================================================================

  describe('getModelPreferences', () => {
    it('fetches model preferences via GET', async () => {
      const result = { default_provider: 'openai', default_model: 'gpt-4' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getModelPreferences();

      expectCalledWithPath(`${API_BASE}/settings/model-preferences`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('GET');
      expect(response.default_provider).toBe('openai');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Unauthorized', 401));

      await expect(getModelPreferences()).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // updateModelPreferences
  // =========================================================================

  describe('updateModelPreferences', () => {
    it('updates model preferences via PUT', async () => {
      const result = { default_provider: 'anthropic', default_model: 'claude-3' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const input = { default_provider: 'anthropic' };
      const response = await updateModelPreferences(input);

      expectCalledWithPath(`${API_BASE}/settings/model-preferences`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('PUT');
      expect(JSON.parse(init.body as string)).toEqual(input);
      expect(response.default_provider).toBe('anthropic');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Bad request', 400));

      await expect(updateModelPreferences({})).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // getTaskModelPreferences
  // =========================================================================

  describe('getTaskModelPreferences', () => {
    it('fetches all task model preferences via GET', async () => {
      const result = {
        preferences: [{ task_type: 'query_analysis', provider: 'gemini' }],
        total: 1,
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getTaskModelPreferences();

      expectCalledWithPath(`${API_BASE}/model-preferences`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('GET');
      expect(response.preferences).toHaveLength(1);
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(getTaskModelPreferences()).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // getTaskModelPreference
  // =========================================================================

  describe('getTaskModelPreference', () => {
    it('fetches a single task model preference via GET', async () => {
      const result = { task_type: 'query_analysis', provider: 'openai', model: 'gpt-4' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getTaskModelPreference('query_analysis');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/model-preferences/query_analysis`);
      expect(response.task_type).toBe('query_analysis');
    });

    it('encodes task type with special characters', async () => {
      mockFetch.mockResolvedValueOnce(
        createMockResponse({ task_type: 'query analysis', provider: 'x' })
      );

      await getTaskModelPreference('query analysis' as 'query_analysis');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('query%20analysis');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Not found', 404));

      await expect(getTaskModelPreference('bad_task')).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // createTaskModelPreference
  // =========================================================================

  describe('createTaskModelPreference', () => {
    it('creates a task model preference via POST', async () => {
      const result = { id: 'pref-1', task_type: 'query_analysis', provider: 'openai' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const input = { task_type: 'query_analysis' as const, provider: 'openai', model: 'gpt-4' };
      const response = await createTaskModelPreference(input);

      expectCalledWithPath(`${API_BASE}/model-preferences`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual(input);
      expect(response.id).toBe('pref-1');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Bad request', 400));

      await expect(
        createTaskModelPreference({
          task_type: 'query_analysis' as const,
          provider: 'bad',
        })
      ).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // updateTaskModelPreference
  // =========================================================================

  describe('updateTaskModelPreference', () => {
    it('updates a task model preference via PUT', async () => {
      const result = { id: 'pref-1', task_type: 'query_analysis', provider: 'anthropic' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const input = { provider: 'anthropic', model: 'claude-3' };
      const response = await updateTaskModelPreference('pref-1', input);

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/model-preferences/pref-1`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('PUT');
      expect(JSON.parse(init.body as string)).toEqual(input);
      expect(response.provider).toBe('anthropic');
    });

    it('encodes preferenceId', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ id: 'a/b', provider: 'x' }));

      await updateTaskModelPreference('a/b', {});

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('a%2Fb');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Not found', 404));

      await expect(updateTaskModelPreference('bad', {})).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // deleteTaskModelPreference
  // =========================================================================

  describe('deleteTaskModelPreference', () => {
    it('deletes a preference (204 No Content) without error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
        statusText: 'No Content',
        headers: new Headers(),
        json: async () => null,
        text: async () => '',
      } as Response);

      await deleteTaskModelPreference('pref-1');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/model-preferences/pref-1`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('DELETE');
    });

    it('throws on non-204 error response', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Not found', 404));

      await expect(deleteTaskModelPreference('bad')).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // getSystemModelDefaults
  // =========================================================================

  describe('getSystemModelDefaults', () => {
    it('fetches system defaults via GET', async () => {
      const result = { defaults: { query_analysis: { provider: 'gemini', model: 'flash' } } };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getSystemModelDefaults();

      expectCalledWithPath(`${API_BASE}/model-preferences/system/defaults`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('GET');
      expect(response.defaults).toBeDefined();
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(getSystemModelDefaults()).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // getModelCostEstimate
  // =========================================================================

  describe('getModelCostEstimate', () => {
    it('fetches cost estimate with required params via GET', async () => {
      const result = { estimated_cost: 0.05, provider: 'openai', model: 'gpt-4' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getModelCostEstimate('openai', 'gpt-4');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/model-preferences/system/cost-estimate?`);
      expect(calledUrl).toContain('provider=openai');
      expect(calledUrl).toContain('model_name=gpt-4');
      expect(calledUrl).toContain('estimated_tokens=1000');
      expect(response.estimated_cost).toBe(0.05);
    });

    it('uses custom estimatedTokens', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ estimated_cost: 0.5 }));

      await getModelCostEstimate('openai', 'gpt-4', 5000);

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('estimated_tokens=5000');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(getModelCostEstimate('bad', 'bad')).rejects.toThrow(ApiError);
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
    });
  });
});
