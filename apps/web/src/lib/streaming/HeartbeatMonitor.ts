/**
 * Heartbeat monitor for detecting stalled SSE connections.
 *
 * Task #74: Response Streaming Improvements
 */

/**
 * Configuration options for the heartbeat monitor.
 */
export interface HeartbeatMonitorConfig {
  /** Timeout in milliseconds before considering connection stalled */
  timeoutMs: number;
  /** Callback fired when connection is considered stalled */
  onTimeout: () => void;
  /** Optional callback for heartbeat received */
  onHeartbeat?: () => void;
}

/**
 * Monitors SSE connections for health by tracking activity.
 * Detects stalled connections when no data is received within timeout period.
 */
export class HeartbeatMonitor {
  private lastActivity: number;
  private readonly timeoutMs: number;
  private readonly onTimeout: () => void;
  private readonly onHeartbeat?: () => void;
  private timedOut: boolean = false;

  constructor(config: HeartbeatMonitorConfig) {
    this.timeoutMs = config.timeoutMs;
    this.onTimeout = config.onTimeout;
    this.onHeartbeat = config.onHeartbeat;
    this.lastActivity = Date.now();
  }

  /**
   * Record activity (called when data is received).
   * Resets the stalled detection timer.
   */
  recordActivity(): void {
    this.lastActivity = Date.now();
    this.timedOut = false;
  }

  /**
   * Handle SSE heartbeat comment from server.
   * Called when ':' comment line is received.
   */
  handleHeartbeat(): void {
    this.recordActivity();
    this.onHeartbeat?.();
  }

  /**
   * Check if connection is stalled.
   * Should be called periodically to verify connection health.
   *
   * @returns true if connection is considered stalled
   */
  check(): boolean {
    if (this.timedOut) {
      return true;
    }

    const elapsed = Date.now() - this.lastActivity;
    if (elapsed >= this.timeoutMs) {
      this.timedOut = true;
      this.onTimeout();
      return true;
    }

    return false;
  }

  /**
   * Get time since last activity in milliseconds.
   */
  getElapsedMs(): number {
    return Date.now() - this.lastActivity;
  }

  /**
   * Check if currently timed out.
   */
  isTimedOut(): boolean {
    return this.timedOut;
  }

  /**
   * Reset the monitor state.
   */
  reset(): void {
    this.lastActivity = Date.now();
    this.timedOut = false;
  }
}

/**
 * Create a heartbeat monitor with default configuration.
 *
 * @param timeoutSeconds - Timeout in seconds (default: 45)
 * @param onTimeout - Callback for timeout
 */
export function createHeartbeatMonitor(
  timeoutSeconds: number,
  onTimeout: () => void
): HeartbeatMonitor {
  return new HeartbeatMonitor({
    timeoutMs: timeoutSeconds * 1000,
    onTimeout,
  });
}
