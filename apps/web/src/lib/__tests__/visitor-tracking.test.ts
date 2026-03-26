import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  generateVisitorId,
  getVisitorIdFromCookies,
  setVisitorIdCookie,
  getOrCreateVisitorId,
  trackInteraction,
  trackSearch,
  trackPropertyView,
  trackFavorite,
  trackInquiry,
  trackContactRequest,
  trackViewingScheduled,
  trackSavedSearch,
  trackReportDownload,
  trackPropertyShare,
  trackLogin,
  trackRegister,
  trackProfileUpdate,
} from '../visitor-tracking';

import type { InteractionType } from '../visitor-tracking';
import { VISITOR_ID_COOKIE, VISITOR_ID_MAX_AGE } from '../visitor-tracking';

// Mock crypto
vi.mock('crypto', () => ({
  randomUUID: vi.fn(),
}));

describe('generateVisitorId', () => {
  it('should use crypto.randomUUID when available', () => {
    vi.mocked(crypto.randomUUID).mockReturnValue('test-uuid-123');
    const id = generateVisitorId();
    expect(id).toBe('test-uuid-123');
  });

  it('should fallback to UUIDv4 when crypto is not available', () => {
    vi.stub(crypto, 'undefined');
    const id = generateVisitorId();
    expect(id).toMatch(/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}$/);
    expect(id).toHaveLength(36);
  });
});

describe('getVisitorIdFromCookies', () => {
  it('should return null for empty cookie header', () => {
    expect(getVisitorIdFromCookies(null)).toBeNull();
    expect(getVisitorIdFromCookies('')).toBeNull();
    expect(getVisitorIdFromCookies(undefined)).toBeNull();
  });

  it('should extract visitor_id from cookie header', () => {
    const cookieHeader = 'session=abc123; visitor_id=test-id-456; other=value';
    expect(getVisitorIdFromCookies(cookieHeader)).toBe('test-id-456');
  });

  it('should return null when visitor_id cookie is not present', () => {
    const cookieHeader = 'session=abc123; other=value';
    expect(getVisitorIdFromCookies(cookieHeader)).toBeNull();
  });

  it('should handle malformed cookies', () => {
    const cookieHeader = 'visitor_id=; other=value'; // missing value
    expect(getVisitorIdFromCookies(cookieHeader)).toBeNull();
  });
});

describe('setVisitorIdCookie', () => {
  it('should return properly formatted cookie string', () => {
    const result = setVisitorIdCookie('test-id-123');
    expect(result).toContain('visitor_id=test-id-123');
    expect(result).toContain('Path=/');
    expect(result).toContain('Max-Age=31536000');
    expect(result).toContain('SameSite=Lax');
  });
});

describe('getOrCreateVisitorId', () => {
  let originalDocument: typeof document;

  beforeEach(() => {
    originalDocument = global.document;
    vi.stub(crypto, 'randomUUID').mockReturnValue('new-uuid-123');
  });

  afterEach(() => {
    global.document = originalDocument;
  });

  it('should return existing cookie if present', () => {
    Object.defineProperty(document, 'cookie', {
      value: 'visitor_id=existing-id',
      writable: true,
    });
    expect(getOrCreateVisitorId()).toBe('existing-id');
  });

  it('should create new visitor ID if no cookie exists', () => {
    Object.defineProperty(document, 'cookie', {
      value: '',
      writable: true,
    });
    const id = getOrCreateVisitorId();
    expect(id).toBe('new-uuid-123');
  });

  it('should throw error on server side', () => {
    // @ts-expect-error - Testing server-side behavior
    expect(() => getOrCreateVisitorId()).toThrow('client components');
  });
});

describe('trackInteraction', () => {
  let mockFetch: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockFetch = vi.fn();
    global.fetch = mockFetch;
    vi.stub(crypto, 'randomUUID').mockReturnValue('test-visitor');
  });

  it('should send POST request to track endpoint', async () => {
    mockFetch.mockResolvedValue({ ok: true });

    await trackInteraction({
      interaction_type: 'search',
      search_query: 'test query',
    });

    expect(mockFetch).toHaveBeenCalledWith('/api/v1/leads/track', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: expect.stringContaining('test-visitor'),
    });
  });

  it('should include all event properties', async () => {
    mockFetch.mockResolvedValue({ ok: true });

    await trackInteraction({
      interaction_type: 'view',
      property_id: 'prop-123',
      metadata: { test: true },
      time_spent_seconds: 60,
    });

    expect(mockFetch).toHaveBeenCalled();
    const call = mockFetch.mock.calls[0][1];
    const body = JSON.parse(call.body);
    expect(body.property_id).toBe('prop-123');
    expect(body.metadata).toEqual({ test: true });
    expect(body.time_spent_seconds).toBe(60);
  });

  it('should silently fail on error', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'));

    // Should not throw
    await trackInteraction({
      interaction_type: 'search',
      search_query: 'test',
    });
  });
});

describe('trackSearch', () => {
  it('should track search with filters', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    global.fetch = mockFetch;

    await trackSearch('apartments in Berlin', { city: 'Berlin' });

    const call = mockFetch.mock.calls[0][1];
    const body = JSON.parse(call.body);
    expect(body.interaction_type).toBe('search');
    expect(body.search_query).toBe('apartments in Berlin');
    expect(body.metadata.filters).toEqual({ city: 'Berlin' });
  });
});

describe('trackPropertyView', () => {
  it('should track property view with time spent', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    global.fetch = mockFetch;

    await trackPropertyView('prop-123', 120);

    const call = mockFetch.mock.calls[0][1];
    const body = JSON.parse(call.body);
    expect(body.interaction_type).toBe('view');
    expect(body.property_id).toBe('prop-123');
    expect(body.time_spent_seconds).toBe(120);
  });
});

describe('trackFavorite', () => {
  it('should track favorite add', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    global.fetch = mockFetch;

    await trackFavorite('prop-123', 'add');

    const call = mockFetch.mock.calls[0][1];
    const body = JSON.parse(call.body);
    expect(body.interaction_type).toBe('favorite');
  });

  it('should track favorite remove', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    global.fetch = mockFetch;

    await trackFavorite('prop-123', 'remove');

    const call = mockFetch.mock.calls[0][1];
    const body = JSON.parse(call.body);
    expect(body.interaction_type).toBe('unfavorite');
  });
});

describe('trackInquiry', () => {
  it('should track inquiry with message flag', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    global.fetch = mockFetch;

    await trackInquiry('prop-123', true);

    const call = mockFetch.mock.calls[0][1];
    const body = JSON.parse(call.body);
    expect(body.interaction_type).toBe('inquiry');
    expect(body.metadata.has_message).toBe(true);
  });
});

describe('trackContactRequest', () => {
  it('should track contact request', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    global.fetch = mockFetch;

    await trackContactRequest('email', 'prop-123');

    const call = mockFetch.mock.calls[0][1];
    const body = JSON.parse(call.body);
    expect(body.interaction_type).toBe('contact');
    expect(body.property_id).toBe('prop-123');
    expect(body.metadata.contact_type).toBe('email');
  });
});

describe('trackViewingScheduled', () => {
  it('should track viewing scheduled', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    global.fetch = mockFetch;

    await trackViewingScheduled('prop-123');

    const call = mockFetch.mock.calls[0][1];
    const body = JSON.parse(call.body);
    expect(body.interaction_type).toBe('schedule_viewing');
  });
});

describe('trackSavedSearch', () => {
  it('should track saved search', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    global.fetch = mockFetch;

    await trackSavedSearch('search-123', 'test query');

    const call = mockFetch.mock.calls[0][1];
    const body = JSON.parse(call.body);
    expect(body.interaction_type).toBe('save_search');
    expect(body.metadata.search_id).toBe('search-123');
  });
});

describe('trackReportDownload', () => {
  it('should track report download', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    global.fetch = mockFetch;

    await trackReportDownload('investment');

    const call = mockFetch.mock.calls[0][1];
    const body = JSON.parse(call.body);
    expect(body.interaction_type).toBe('download_report');
    expect(body.metadata.report_type).toBe('investment');
  });
});

describe('trackPropertyShare', () => {
  it('should track property share', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    global.fetch = mockFetch;

    await trackPropertyShare('prop-123', 'email');

    const call = mockFetch.mock.calls[0][1];
    const body = JSON.parse(call.body);
    expect(body.interaction_type).toBe('share');
    expect(body.metadata.share_method).toBe('email');
  });
});

describe('trackLogin', () => {
  it('should track login', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    global.fetch = mockFetch;

    await trackLogin();

    const call = mockFetch.mock.calls[0][1];
    const body = JSON.parse(call.body);
    expect(body.interaction_type).toBe('login');
  });
});

describe('trackRegister', () => {
  it('should track register', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    global.fetch = mockFetch;

    await trackRegister();

    const call = mockFetch.mock.calls[0][1];
    const body = JSON.parse(call.body);
    expect(body.interaction_type).toBe('register');
  });
});

describe('trackProfileUpdate', () => {
  it('should track profile update', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    global.fetch = mockFetch;

    await trackProfileUpdate(['email', 'name']);

    const call = mockFetch.mock.calls[0][1];
    const body = JSON.parse(call.body);
    expect(body.interaction_type).toBe('profile_update');
    expect(body.metadata.updated_fields).toEqual(['email', 'name']);
  });
});
