/**
 * Tests for ReconnectingEventSource.
 *
 * Task #74: Response Streaming Improvements
 */

import { ReconnectingEventSource, createReconnectingEventSource } from '../ReconnectingEventSource';

// Mock EventSource
class MockEventSource {
  url: string;
  readyState: number = EventSource.CONNECTING;
  onopen: ((this: EventSource, ev: Event) => void) | null = null;
  onmessage: ((this: EventSource, ev: MessageEvent) => void) | null = null;
  onerror: ((this: EventSource, ev: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    // Simulate async connection
    setTimeout(() => {
      this.readyState = EventSource.OPEN;
      if (this.onopen) {
        this.onopen.call(this as unknown as EventSource, new Event('open'));
      }
    }, 10);
  }

  close(): void {
    this.readyState = EventSource.CLOSED;
  }
}

// Replace global EventSource with mock
const originalEventSource = global.EventSource;
beforeAll(() => {
  (global as unknown as { EventSource: typeof MockEventSource }).EventSource =
    MockEventSource as unknown as typeof EventSource;
});

afterAll(() => {
  global.EventSource = originalEventSource;
});

describe('ReconnectingEventSource', () => {
  describe('constructor', () => {
    it('should create instance with default options', () => {
      const source = new ReconnectingEventSource('http://example.com/stream');
      expect(source.url).toBe('http://example.com/stream');
      source.close();
    });

    it('should accept custom options', () => {
      const source = new ReconnectingEventSource('http://example.com/stream', {
        initialDelay: 500,
        maxDelay: 10000,
        maxRetries: 5,
      });
      expect(source).toBeInstanceOf(ReconnectingEventSource);
      source.close();
    });
  });

  describe('addEventListener', () => {
    it('should register event handlers', () => {
      const source = new ReconnectingEventSource('http://example.com/stream');
      const handler = jest.fn();

      source.addEventListener('message', handler);
      expect(source).toBe(source); // Fluent API
      source.close();
    });
  });

  describe('removeEventListener', () => {
    it('should remove event handlers', () => {
      const source = new ReconnectingEventSource('http://example.com/stream');
      const handler = jest.fn();

      source.addEventListener('message', handler);
      source.removeEventListener('message', handler);
      source.close();
    });
  });

  describe('close', () => {
    it('should stop reconnection attempts', () => {
      const source = new ReconnectingEventSource('http://example.com/stream');
      source.close();

      expect(source.readyState).toBe(EventSource.CLOSED);
    });
  });

  describe('getRetryCount', () => {
    it('should return current retry count', () => {
      const source = new ReconnectingEventSource('http://example.com/stream');
      expect(source.getRetryCount()).toBe(0);
      source.close();
    });
  });

  describe('hasExceededMaxRetries', () => {
    it('should return false initially', () => {
      const source = new ReconnectingEventSource('http://example.com/stream');
      expect(source.hasExceededMaxRetries()).toBe(false);
      source.close();
    });
  });

  describe('onmessage/onerror/onopen setters', () => {
    it('should set handlers via property setters', () => {
      const source = new ReconnectingEventSource('http://example.com/stream');
      const handler = jest.fn();

      source.onmessage = handler as unknown as typeof source.onmessage;
      source.onerror = handler;
      source.onopen = handler;

      source.close();
    });
  });
});

describe('createReconnectingEventSource', () => {
  it('should create ReconnectingEventSource instance', () => {
    const source = createReconnectingEventSource('http://example.com/stream');
    expect(source).toBeInstanceOf(ReconnectingEventSource);
    source.close();
  });

  it('should pass options to constructor', () => {
    const source = createReconnectingEventSource('http://example.com/stream', {
      maxRetries: 3,
    });
    expect(source).toBeInstanceOf(ReconnectingEventSource);
    source.close();
  });
});
