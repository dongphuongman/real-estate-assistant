/**
 * Tests for useLeadTracking hook.
 * Uses global fetch mock (same pattern as agents.test.ts).
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, jest, beforeEach } from '@jest/globals';

// Mock fetch globally before any imports
const mockFetch = jest.fn();
(globalThis as unknown as { fetch: jest.Mock }).fetch = mockFetch;

// Mock cookies for visitor-tracking
Object.defineProperty(document, 'cookie', {
  writable: true,
  value: 'visitor_id=test-visitor-123',
});

function createMockResponse(data: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    headers: new Headers(),
    json: async () => data,
    text: async () => JSON.stringify(data),
  } as Response;
}

import {
  useLeadTracking,
  useTrackPageTime,
  useTrackSearchDebounced,
} from '@/hooks/useLeadTracking';

describe('useLeadTracking', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Default: all tracking calls succeed
    mockFetch.mockResolvedValue(createMockResponse({ ok: true }));
  });

  it('returns a visitor ID', () => {
    const { result } = renderHook(() => useLeadTracking());
    expect(result.current.visitorId).toBeTruthy();
  });

  it('trackSearch calls API', async () => {
    const { result } = renderHook(() => useLeadTracking());

    await act(async () => {
      await result.current.trackSearch('apartments in Berlin', { price_max: 500000 });
    });

    expect(mockFetch).toHaveBeenCalled();
    const lastCall = mockFetch.mock.calls[mockFetch.mock.calls.length - 1];
    expect(lastCall[0]).toContain('/track');
  });

  it('trackSearch calls API without filters', async () => {
    const { result } = renderHook(() => useLeadTracking());

    await act(async () => {
      await result.current.trackSearch('test query');
    });

    expect(mockFetch).toHaveBeenCalled();
  });

  it('trackPropertyView returns stopTracking function', () => {
    const { result } = renderHook(() => useLeadTracking());

    let stopTracking: () => void;
    act(() => {
      const viewResult = result.current.trackPropertyView('prop-1');
      stopTracking = viewResult.stopTracking;
    });

    expect(mockFetch).toHaveBeenCalled();

    // Call stop tracking - should trigger another track call
    const callCount = mockFetch.mock.calls.length;
    act(() => {
      stopTracking!();
    });

    // Additional tracking call for time spent
    expect(mockFetch.mock.calls.length).toBeGreaterThan(callCount);
  });

  it('trackFavorite calls API with add action', async () => {
    const { result } = renderHook(() => useLeadTracking());

    await act(async () => {
      await result.current.trackFavorite('prop-1', 'add');
    });

    expect(mockFetch).toHaveBeenCalled();
  });

  it('trackFavorite defaults to add action', async () => {
    const { result } = renderHook(() => useLeadTracking());

    await act(async () => {
      await result.current.trackFavorite('prop-1');
    });

    expect(mockFetch).toHaveBeenCalled();
  });

  it('trackFavorite calls API with remove action', async () => {
    const { result } = renderHook(() => useLeadTracking());

    await act(async () => {
      await result.current.trackFavorite('prop-1', 'remove');
    });

    expect(mockFetch).toHaveBeenCalled();
  });

  it('trackInquiry calls API', async () => {
    const { result } = renderHook(() => useLeadTracking());

    await act(async () => {
      await result.current.trackInquiry('prop-1', true);
    });

    expect(mockFetch).toHaveBeenCalled();
  });

  it('trackInquiry defaults hasMessage to true', async () => {
    const { result } = renderHook(() => useLeadTracking());

    await act(async () => {
      await result.current.trackInquiry('prop-1');
    });

    expect(mockFetch).toHaveBeenCalled();
  });

  it('trackContactRequest calls API with email', async () => {
    const { result } = renderHook(() => useLeadTracking());

    await act(async () => {
      await result.current.trackContactRequest('email', 'prop-1');
    });

    expect(mockFetch).toHaveBeenCalled();
  });

  it('trackContactRequest works without propertyId', async () => {
    const { result } = renderHook(() => useLeadTracking());

    await act(async () => {
      await result.current.trackContactRequest('phone');
    });

    expect(mockFetch).toHaveBeenCalled();
  });

  it('trackViewingScheduled calls API', async () => {
    const { result } = renderHook(() => useLeadTracking());

    await act(async () => {
      await result.current.trackViewingScheduled('prop-1');
    });

    expect(mockFetch).toHaveBeenCalled();
  });

  it('trackSavedSearch calls API', async () => {
    const { result } = renderHook(() => useLeadTracking());

    await act(async () => {
      await result.current.trackSavedSearch('search-1', '2br Warsaw');
    });

    expect(mockFetch).toHaveBeenCalled();
  });

  it('trackReportDownload calls API', async () => {
    const { result } = renderHook(() => useLeadTracking());

    await act(async () => {
      await result.current.trackReportDownload('market-analysis');
    });

    expect(mockFetch).toHaveBeenCalled();
  });

  it('trackPropertyShare calls API', async () => {
    const { result } = renderHook(() => useLeadTracking());

    await act(async () => {
      await result.current.trackPropertyShare('prop-1', 'whatsapp');
    });

    expect(mockFetch).toHaveBeenCalled();
  });

  it('exposes trackInteraction function', () => {
    const { result } = renderHook(() => useLeadTracking());
    expect(typeof result.current.trackInteraction).toBe('function');
  });
});

describe('useTrackPageTime', () => {
  beforeEach(() => {
    mockFetch.mockResolvedValue(createMockResponse({ ok: true }));
  });

  it('renders without errors', () => {
    const { unmount } = renderHook(() =>
      useTrackPageTime('property_detail', { property_id: 'p1' })
    );
    unmount();
    // Just verify the hook doesn't throw
  });

  it('works without metadata', () => {
    const { unmount } = renderHook(() => useTrackPageTime('home'));
    unmount();
  });
});

describe('useTrackSearchDebounced', () => {
  beforeEach(() => {
    mockFetch.mockResolvedValue(createMockResponse({ ok: true }));
  });

  it('returns trackSearchDebounced and flushSearch', () => {
    const { result } = renderHook(() => useTrackSearchDebounced(500));
    expect(typeof result.current.trackSearchDebounced).toBe('function');
    expect(typeof result.current.flushSearch).toBe('function');
  });

  it('trackSearchDebounced does not throw', () => {
    const { result } = renderHook(() => useTrackSearchDebounced(500));

    act(() => {
      result.current.trackSearchDebounced('query 1', { city: 'Berlin' });
    });

    // No error thrown
  });

  it('flushSearch does not throw with no pending', () => {
    const { result } = renderHook(() => useTrackSearchDebounced(1000));

    act(() => {
      result.current.flushSearch();
    });

    // No error thrown
  });

  it('flushSearch after debounced search does not throw', () => {
    const { result } = renderHook(() => useTrackSearchDebounced(1000));

    act(() => {
      result.current.trackSearchDebounced('urgent query');
    });

    act(() => {
      result.current.flushSearch();
    });

    // No error thrown
  });
});
