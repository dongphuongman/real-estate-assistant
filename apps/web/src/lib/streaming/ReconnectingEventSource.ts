/**
 * EventSource with automatic reconnection and exponential backoff.
 *
 * Task #74: Response Streaming Improvements
 */

/**
 * Configuration options for ReconnectingEventSource.
 */
export interface ReconnectingEventSourceOptions {
  /** Initial reconnection delay in milliseconds (default: 1000) */
  initialDelay?: number;
  /** Maximum reconnection delay in milliseconds (default: 30000) */
  maxDelay?: number;
  /** Backoff multiplier for exponential increase (default: 2.0) */
  backoffMultiplier?: number;
  /** Maximum reconnection attempts before giving up (default: 10) */
  maxRetries?: number;
  /** Jitter factor to randomize delays (default: 0.1) */
  jitterFactor?: number;
}

const DEFAULT_OPTIONS: Required<ReconnectingEventSourceOptions> = {
  initialDelay: 1000,
  maxDelay: 30000,
  backoffMultiplier: 2.0,
  maxRetries: 10,
  jitterFactor: 0.1,
};

/**
 * Event types for ReconnectingEventSource.
 */
export type ReconnectingEventSourceEventType =
  | 'open'
  | 'message'
  | 'error'
  | 'reconnecting'
  | 'connected'
  | 'maxretries';

/**
 * Event handler function type.
 */
export type EventHandler = (event: Event) => void;

/**
 * EventSource wrapper with automatic reconnection using exponential backoff.
 *
 * Features:
 * - Automatic reconnection on connection loss
 * - Exponential backoff with jitter to prevent thundering herd
 * - Respects server-sent retry directive
 * - Maximum retry limit with event notification
 * - Proper cleanup on explicit close
 */
export class ReconnectingEventSource {
  private _url: string;
  private options: Required<ReconnectingEventSourceOptions>;
  private eventSource: EventSource | null = null;
  private retryCount: number = 0;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private closed: boolean = false;
  private serverRetryMs: number | null = null;

  private eventHandlers: Map<string, Set<EventHandler>> = new Map();

  constructor(url: string, options?: ReconnectingEventSourceOptions) {
    this._url = url;
    this.options = { ...DEFAULT_OPTIONS, ...options };
    this.connect();
  }

  /**
   * Calculate backoff delay with exponential increase and jitter.
   */
  private calculateBackoff(): number {
    // Use server-provided retry if available
    if (this.serverRetryMs !== null) {
      return this.serverRetryMs;
    }

    const baseDelay =
      this.options.initialDelay * Math.pow(this.options.backoffMultiplier, this.retryCount);
    const cappedDelay = Math.min(baseDelay, this.options.maxDelay);
    // nosemgrep: weak-random.random — retry jitter, not security-sensitive
    const jitter = cappedDelay * this.options.jitterFactor * Math.random();

    return Math.floor(cappedDelay + jitter);
  }

  /**
   * Establish connection to the SSE endpoint.
   */
  private connect(): void {
    if (this.closed) {
      return;
    }

    this.eventSource = new EventSource(this._url);

    this.eventSource.onopen = () => {
      this.retryCount = 0;
      this.serverRetryMs = null;
      this.emit('open', new Event('open'));
      this.emit('connected', new Event('connected'));
    };

    this.eventSource.onmessage = (event: MessageEvent) => {
      // Check for retry directive in data
      if (event.data?.startsWith?.('retry:')) {
        const retryValue = parseInt(event.data.substring(6).trim(), 10);
        if (!isNaN(retryValue) && retryValue > 0) {
          this.serverRetryMs = retryValue;
        }
        return;
      }

      this.emit('message', event);
    };

    this.eventSource.onerror = () => {
      this.eventSource?.close();
      this.eventSource = null;

      if (this.closed) {
        return;
      }

      this.retryCount++;

      if (this.retryCount > this.options.maxRetries) {
        this.emit('maxretries', new Event('maxretries'));
        this.emit(
          'error',
          new CustomEvent('error', {
            detail: { maxRetriesExceeded: true },
          })
        );
        return;
      }

      // Emit reconnecting event with backoff info
      const backoffMs = this.calculateBackoff();
      this.emit(
        'reconnecting',
        new CustomEvent('reconnecting', {
          detail: {
            attempt: this.retryCount,
            delayMs: backoffMs,
            maxRetries: this.options.maxRetries,
          },
        })
      );

      // Schedule reconnection
      this.reconnectTimeout = setTimeout(() => {
        this.connect();
      }, backoffMs);
    };
  }

  /**
   * Register an event handler.
   */
  addEventListener(type: ReconnectingEventSourceEventType, handler: EventHandler): this {
    if (!this.eventHandlers.has(type)) {
      this.eventHandlers.set(type, new Set());
    }
    this.eventHandlers.get(type)!.add(handler);
    return this;
  }

  /**
   * Remove an event handler.
   */
  removeEventListener(type: ReconnectingEventSourceEventType, handler: EventHandler): this {
    const handlers = this.eventHandlers.get(type);
    if (handlers) {
      handlers.delete(handler);
    }
    return this;
  }

  /**
   * Set the onmessage handler.
   */
  set onmessage(handler: ((event: MessageEvent) => void) | null) {
    if (handler) {
      this.addEventListener('message', handler as EventHandler);
    }
  }

  /**
   * Set the onerror handler.
   */
  set onerror(handler: ((event: Event) => void) | null) {
    if (handler) {
      this.addEventListener('error', handler);
    }
  }

  /**
   * Set the onopen handler.
   */
  set onopen(handler: ((event: Event) => void) | null) {
    if (handler) {
      this.addEventListener('open', handler);
    }
  }

  /**
   * Emit an event to registered handlers.
   */
  private emit(type: string, event: Event): void {
    const handlers = this.eventHandlers.get(type);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(event);
        } catch {
          // Ignore handler errors
        }
      });
    }
  }

  /**
   * Close the connection and stop reconnection attempts.
   */
  close(): void {
    this.closed = true;

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    this.eventHandlers.clear();
  }

  /**
   * Check if connection is currently open.
   */
  get readyState(): number {
    return this.eventSource?.readyState ?? EventSource.CLOSED;
  }

  /**
   * Get the URL being connected to.
   */
  get url(): string {
    return this.eventSource?.url ?? this._url;
  }

  /**
   * Get current retry count.
   */
  getRetryCount(): number {
    return this.retryCount;
  }

  /**
   * Check if max retries have been exceeded.
   */
  hasExceededMaxRetries(): boolean {
    return this.retryCount > this.options.maxRetries;
  }
}

/**
 * Create a ReconnectingEventSource with default options.
 */
export function createReconnectingEventSource(
  url: string,
  options?: ReconnectingEventSourceOptions
): ReconnectingEventSource {
  return new ReconnectingEventSource(url, options);
}
