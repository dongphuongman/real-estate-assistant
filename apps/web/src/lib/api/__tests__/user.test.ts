/**
 * Tests for user.ts API module.
 * Covers RAG upload/reset/QA, CRM sync, prompt templates,
 * user activity analytics (summary, trends, CSV export),
 * user profile management (get, update, avatar, privacy, data export).
 */

import { describe, it, expect, jest, beforeEach } from '@jest/globals';

// Mock fetch globally before any imports
const mockFetch = jest.fn();
(globalThis as unknown as { fetch: jest.Mock }).fetch = mockFetch;

import {
  uploadRagDocuments,
  resetRagKnowledge,
  ragQa,
  crmSyncContactApi,
  listPromptTemplates,
  applyPromptTemplate,
  getUserActivitySummary,
  getUserActivityTrends,
  exportUserActivityCSV,
  getProfile,
  updateProfile,
  uploadAvatar,
  deleteAvatar,
  updatePrivacySettings,
  requestDataExport,
  getExportStatus,
} from '@/lib/api/user';

import { ApiError } from '@/lib/api/client';

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

describe('user.ts API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockReset();
  });

  // =========================================================================
  // RAG API
  // =========================================================================

  describe('uploadRagDocuments', () => {
    it('uploads files via POST with FormData', async () => {
      const result = { uploaded: 2, errors: [] };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const file1 = new File(['content1'], 'doc1.pdf', { type: 'application/pdf' });
      const file2 = new File(['content2'], 'doc2.txt', { type: 'text/plain' });
      const response = await uploadRagDocuments([file1, file2]);

      expectCalledWithPath(`${API_BASE}/rag/upload`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      // body should be FormData, not a string
      expect(init.body).toBeInstanceOf(FormData);
      expect(response.uploaded).toBe(2);
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Bad request', 400));

      await expect(uploadRagDocuments([])).rejects.toThrow(ApiError);
    });
  });

  describe('resetRagKnowledge', () => {
    it('resets RAG knowledge via POST', async () => {
      const result = { success: true, message: 'Knowledge base reset' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await resetRagKnowledge();

      expectCalledWithPath(`${API_BASE}/rag/reset`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(response.success).toBe(true);
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(resetRagKnowledge()).rejects.toThrow(ApiError);
    });
  });

  describe('ragQa', () => {
    it('asks a question via POST', async () => {
      const result = { answer: 'Yes, the property has parking.', sources: [] };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const input = { question: 'Does the property have parking?' };
      const response = await ragQa(input);

      expectCalledWithPath(`${API_BASE}/rag/qa`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual(input);
      expect(response.answer).toBe('Yes, the property has parking.');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Bad request', 400));

      await expect(ragQa({ question: '' })).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // CRM Sync
  // =========================================================================

  describe('crmSyncContactApi', () => {
    it('syncs contact via POST with name, phone, email', async () => {
      const result = { id: 'contact-1' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await crmSyncContactApi('John Doe', '+48123456789', 'john@example.com');

      expectCalledWithPath(`${API_BASE}/tools/crm-sync-contact`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual({
        name: 'John Doe',
        phone: '+48123456789',
        email: 'john@example.com',
      });
      expect(response.id).toBe('contact-1');
    });

    it('syncs contact with name only', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ id: 'contact-2' }));

      await crmSyncContactApi('Jane');

      const body = JSON.parse((mockFetch.mock.calls[0][1] as RequestInit).body as string);
      expect(body.name).toBe('Jane');
      expect(body.phone).toBeUndefined();
      expect(body.email).toBeUndefined();
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(crmSyncContactApi('x')).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // Prompt Templates
  // =========================================================================

  describe('listPromptTemplates', () => {
    it('lists templates via GET', async () => {
      const result = [{ id: 'tpl-1', name: 'Property Description', variables: [] }];
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await listPromptTemplates();

      expectCalledWithPath(`${API_BASE}/prompt-templates`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('GET');
      expect(response).toHaveLength(1);
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(listPromptTemplates()).rejects.toThrow(ApiError);
    });
  });

  describe('applyPromptTemplate', () => {
    it('applies template via POST with templateId and variables', async () => {
      const result = { applied_template: 'tpl-1', output: 'Generated content' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await applyPromptTemplate('tpl-1', { city: 'Krakow', rooms: 3 });

      expectCalledWithPath(`${API_BASE}/prompt-templates/apply`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual({
        template_id: 'tpl-1',
        variables: { city: 'Krakow', rooms: 3 },
      });
      expect(response.output).toBe('Generated content');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Not found', 404));

      await expect(applyPromptTemplate('bad', {})).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // User Activity Analytics
  // =========================================================================

  describe('getUserActivitySummary', () => {
    it('fetches summary without params via GET with credentials', async () => {
      const result = { total_searches: 50, total_views: 200, period: 'all_time' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getUserActivitySummary();

      expectCalledWithPath(`${API_BASE}/user-activity/summary`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('GET');
      expect(init.credentials).toBe('include');
      expect(response.total_searches).toBe(50);
    });

    it('appends date range params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({}));

      await getUserActivitySummary({ period_start: '2024-01-01', period_end: '2024-06-30' });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('period_start=2024-01-01');
      expect(calledUrl).toContain('period_end=2024-06-30');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Unauthorized', 401));

      await expect(getUserActivitySummary()).rejects.toThrow(ApiError);
    });

    it('handles network failure (safeFetch wraps)', async () => {
      mockFetch.mockRejectedValue(new TypeError('Failed to fetch'));

      try {
        await getUserActivitySummary();
        fail('Expected ApiError');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).category).toBe('network');
      }
      mockFetch.mockReset();
    });
  });

  describe('getUserActivityTrends', () => {
    it('fetches trends without params', async () => {
      const result = { trends: [{ period: '2024-01', searches: 10 }], interval: 'month' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getUserActivityTrends();

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/user-activity/trends?`);
      expect(response.interval).toBe('month');
    });

    it('appends interval and periods params', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ trends: [], interval: 'week' }));

      await getUserActivityTrends({ interval: 'week', periods: 12 });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('interval=week');
      expect(calledUrl).toContain('periods=12');
    });
  });

  describe('exportUserActivityCSV', () => {
    it('exports CSV as Blob on success', async () => {
      const blob = new Blob(['csv,data'], { type: 'text/csv' });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: 'OK',
        headers: new Headers(),
        json: async () => null,
        text: async () => 'csv,data',
        blob: async () => blob,
      } as Response);

      const response = await exportUserActivityCSV();

      expectCalledWithPath(`${API_BASE}/user-activity/export`);
      expect(response).toBeInstanceOf(Blob);
    });

    it('appends date range params to export URL', async () => {
      const blob = new Blob([''], { type: 'text/csv' });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: 'OK',
        headers: new Headers(),
        json: async () => null,
        text: async () => '',
        blob: async () => blob,
      } as Response);

      await exportUserActivityCSV({ period_start: '2024-01-01', period_end: '2024-12-31' });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('period_start=2024-01-01');
      expect(calledUrl).toContain('period_end=2024-12-31');
    });

    it('throws ApiError on non-ok response', async () => {
      const errorBody = { detail: 'Export failed' };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Error',
        headers: new Headers(),
        json: async () => errorBody,
        text: async () => JSON.stringify(errorBody),
        blob: async () => new Blob(),
      } as Response);

      await expect(exportUserActivityCSV()).rejects.toThrow(ApiError);
    });

    it('throws ApiError with default message when json parse fails', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Error',
        headers: new Headers(),
        json: async () => {
          throw new Error('Not JSON');
        },
        text: async () => 'Not JSON',
        blob: async () => new Blob(),
      } as Response);

      try {
        await exportUserActivityCSV();
        fail('Expected ApiError');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).message).toBe('Export failed');
        expect((error as ApiError).status).toBe(500);
      }
    });
  });

  // =========================================================================
  // User Profile Management
  // =========================================================================

  describe('getProfile', () => {
    it('fetches profile via GET with credentials', async () => {
      const result = { id: 'user-1', email: 'john@example.com', name: 'John' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getProfile();

      expectCalledWithPath(`${API_BASE}/profile`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('GET');
      expect(init.credentials).toBe('include');
      expect(response.email).toBe('john@example.com');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Unauthorized', 401));

      await expect(getProfile()).rejects.toThrow(ApiError);
    });
  });

  describe('updateProfile', () => {
    it('updates profile via PUT with credentials', async () => {
      const result = { id: 'user-1', email: 'john@example.com', name: 'John Updated' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const input = { name: 'John Updated' };
      const response = await updateProfile(input);

      expectCalledWithPath(`${API_BASE}/profile`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('PUT');
      expect(init.credentials).toBe('include');
      expect(JSON.parse(init.body as string)).toEqual(input);
      expect(response.name).toBe('John Updated');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Bad request', 400));

      await expect(updateProfile({})).rejects.toThrow(ApiError);
    });
  });

  describe('uploadAvatar', () => {
    it('uploads avatar file via POST with FormData and credentials', async () => {
      const result = { url: 'https://cdn.example.com/avatar.jpg' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const file = new File(['avatar-data'], 'avatar.jpg', { type: 'image/jpeg' });
      const response = await uploadAvatar(file);

      expectCalledWithPath(`${API_BASE}/profile/avatar`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(init.credentials).toBe('include');
      expect(init.body).toBeInstanceOf(FormData);
      expect(response.url).toBe('https://cdn.example.com/avatar.jpg');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('File too large', 413));

      const file = new File(['big'], 'big.jpg', { type: 'image/jpeg' });
      await expect(uploadAvatar(file)).rejects.toThrow(ApiError);
    });
  });

  describe('deleteAvatar', () => {
    it('deletes avatar via DELETE without error on success', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
        statusText: 'No Content',
        headers: new Headers(),
        json: async () => null,
        text: async () => '',
      } as Response);

      await deleteAvatar();

      expectCalledWithPath(`${API_BASE}/profile/avatar`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('DELETE');
      expect(init.credentials).toBe('include');
    });

    it('throws ApiError on non-ok response', async () => {
      const errorBody = { detail: 'Not found' };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        headers: new Headers(),
        json: async () => errorBody,
        text: async () => JSON.stringify(errorBody),
      } as Response);

      try {
        await deleteAvatar();
        fail('Expected ApiError');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).message).toBe('Not found');
        expect((error as ApiError).status).toBe(404);
      }
    });

    it('throws ApiError with default message when json parse fails', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Error',
        headers: new Headers(),
        json: async () => {
          throw new Error('Not JSON');
        },
        text: async () => 'Server error',
      } as Response);

      try {
        await deleteAvatar();
        fail('Expected ApiError');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).message).toBe('Failed to delete avatar');
      }
    });
  });

  describe('updatePrivacySettings', () => {
    it('updates privacy settings via PUT with credentials', async () => {
      const result = { id: 'user-1', email: 'john@example.com', privacy: 'private' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const input = { profile_visibility: 'private', show_activity: false };
      const response = await updatePrivacySettings(input);

      expectCalledWithPath(`${API_BASE}/profile/privacy`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('PUT');
      expect(init.credentials).toBe('include');
      expect(JSON.parse(init.body as string)).toEqual(input);
      expect(response.id).toBe('user-1');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Bad request', 400));

      await expect(updatePrivacySettings({})).rejects.toThrow(ApiError);
    });
  });

  describe('requestDataExport', () => {
    it('requests data export via POST with credentials', async () => {
      const result = { export_id: 'export-1', status: 'processing', estimated_time_minutes: 5 };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const input = { format: 'json' as const };
      const response = await requestDataExport(input);

      expectCalledWithPath(`${API_BASE}/profile/export`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(init.credentials).toBe('include');
      expect(JSON.parse(init.body as string)).toEqual(input);
      expect(response.export_id).toBe('export-1');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(requestDataExport({})).rejects.toThrow(ApiError);
    });
  });

  describe('getExportStatus', () => {
    it('fetches export status via GET with credentials', async () => {
      const result = {
        export_id: 'export-1',
        status: 'completed',
        download_url: 'https://cdn.example.com/export.zip',
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getExportStatus('export-1');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/profile/export/export-1`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('GET');
      expect(init.credentials).toBe('include');
      expect(response.status).toBe('completed');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Not found', 404));

      await expect(getExportStatus('bad-id')).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // Re-exports
  // =========================================================================

  describe('ApiError', () => {
    it('is available from client module', () => {
      expect(ApiError).toBeDefined();
      const err = new ApiError('test', 500);
      expect(err).toBeInstanceOf(Error);
      expect(err.name).toBe('ApiError');
    });
  });
});
