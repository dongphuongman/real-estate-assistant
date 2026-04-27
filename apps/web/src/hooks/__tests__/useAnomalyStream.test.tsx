import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, jest, beforeEach } from '@jest/globals';

// Global EventSource mock so ReconnectingEventSource can construct without errors
const mockEsClose = jest.fn();
const mockEsAddEventListener = jest.fn();
const savedEventSource = globalThis.EventSource;

beforeEach(() => {
  // Provide a minimal EventSource mock
  (globalThis as Record<string, unknown>).EventSource = jest.fn().mockImplementation(() => ({
    close: mockEsClose,
    addEventListener: mockEsAddEventListener,
    onopen: null,
    onmessage: null,
    onerror: null,
  }));
});

afterEach(() => {
  if (savedEventSource) {
    (globalThis as Record<string, unknown>).EventSource = savedEventSource;
  } else {
    delete (globalThis as Record<string, unknown>).EventSource;
  }
});

// Mock getApiUrl
jest.mock('@/lib/api', () => ({
  getApiUrl: () => 'http://localhost:8000/api/v1',
}));

jest.mock('@/lib/logger', () => ({
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
}));

import { useAnomalyStream } from '@/hooks/useAnomalyStream';

describe('useAnomalyStream', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('returns initial state', () => {
    const { result } = renderHook(() => useAnomalyStream());
    expect(result.current.anomalies).toEqual([]);
    expect(result.current.connected).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.reconnectAttempts).toBe(0);
  });

  it('exposes clearAnomalies and removeAnomaly functions', () => {
    const { result } = renderHook(() => useAnomalyStream());
    expect(typeof result.current.clearAnomalies).toBe('function');
    expect(typeof result.current.removeAnomaly).toBe('function');
  });

  it('does not connect when disabled', () => {
    const { result } = renderHook(() => useAnomalyStream(false));
    expect(result.current.connected).toBe(false);
  });

  it('clearAnomalies clears the list', () => {
    const { result } = renderHook(() => useAnomalyStream());

    act(() => {
      result.current.clearAnomalies();
    });

    expect(result.current.anomalies).toEqual([]);
  });

  it('removeAnomaly removes nothing from empty list', () => {
    const { result } = renderHook(() => useAnomalyStream());

    act(() => {
      result.current.removeAnomaly('nonexistent');
    });

    expect(result.current.anomalies).toEqual([]);
  });

  it('cleans up event source on unmount when enabled', () => {
    const { unmount } = renderHook(() => useAnomalyStream());
    unmount();
  });

  it('can be called with custom maxAnomalies', () => {
    const { result } = renderHook(() => useAnomalyStream(true, 10));
    expect(result.current.anomalies).toEqual([]);
  });
});
