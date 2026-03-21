/**
 * Stream buffer for interrupted stream recovery.
 *
 * Task #74: Response Streaming Improvements
 */

/**
 * A single buffered chunk with metadata.
 */
export interface BufferedChunk {
  /** The chunk content */
  content: string;
  /** Timestamp when chunk was received */
  timestamp: number;
  /** Sequence number for ordering */
  sequence: number;
}

/**
 * Serialized buffer state for persistence.
 */
export interface BufferState {
  /** Session ID this buffer belongs to */
  sessionId: string;
  /** Request ID for correlation */
  requestId?: string;
  /** Buffered chunks */
  chunks: BufferedChunk[];
  /** Timestamp when buffer was created */
  createdAt: number;
  /** Timestamp when buffer was last updated */
  updatedAt: number;
}

/**
 * Configuration for StreamBuffer.
 */
export interface StreamBufferConfig {
  /** Maximum number of chunks to buffer */
  maxChunks: number;
  /** Key for sessionStorage persistence */
  storageKey: string;
}

const DEFAULT_CONFIG: StreamBufferConfig = {
  maxChunks: 1000,
  storageKey: 'stream_buffer',
};

/**
 * Buffer for storing stream chunks to enable recovery after interruption.
 * Supports persistence to sessionStorage for page refresh recovery.
 */
export class StreamBuffer {
  private chunks: BufferedChunk[] = [];
  private sequence: number = 0;
  private readonly sessionId: string;
  private readonly requestId?: string;
  private readonly config: StreamBufferConfig;
  private createdAt: number;

  constructor(
    sessionId: string,
    requestId?: string,
    config?: Partial<StreamBufferConfig>
  ) {
    this.sessionId = sessionId;
    this.requestId = requestId;
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.createdAt = Date.now();
  }

  /**
   * Add a chunk to the buffer.
   *
   * @param content - The chunk content
   * @returns The sequence number assigned to this chunk
   */
  add(content: string): number {
    // Enforce max chunks limit
    if (this.chunks.length >= this.config.maxChunks) {
      this.chunks.shift();
    }

    const chunk: BufferedChunk = {
      content,
      timestamp: Date.now(),
      sequence: this.sequence,
    };

    this.chunks.push(chunk);
    return this.sequence++;
  }

  /**
   * Get all buffered content concatenated.
   */
  getBufferedContent(): string {
    return this.chunks.map((c) => c.content).join('');
  }

  /**
   * Get the last sequence number.
   */
  getLastSequence(): number {
    return this.sequence > 0 ? this.sequence - 1 : 0;
  }

  /**
   * Get all chunks.
   */
  getChunks(): BufferedChunk[] {
    return [...this.chunks];
  }

  /**
   * Get buffer statistics.
   */
  getStats(): {
    totalChunks: number;
    totalBytes: number;
    oldestChunk?: number;
    newestChunk?: number;
  } {
    const totalBytes = this.chunks.reduce(
      (sum, c) => sum + new Blob([c.content]).size,
      0
    );

    return {
      totalChunks: this.chunks.length,
      totalBytes,
      oldestChunk: this.chunks[0]?.timestamp,
      newestChunk: this.chunks[this.chunks.length - 1]?.timestamp,
    };
  }

  /**
   * Clear the buffer.
   */
  clear(): void {
    this.chunks = [];
    this.sequence = 0;
    this.removeFromStorage();
  }

  /**
   * Persist buffer to sessionStorage.
   */
  persist(): void {
    if (typeof sessionStorage === 'undefined') {
      return;
    }

    const state: BufferState = {
      sessionId: this.sessionId,
      requestId: this.requestId,
      chunks: this.chunks,
      createdAt: this.createdAt,
      updatedAt: Date.now(),
    };

    try {
      sessionStorage.setItem(
        `${this.config.storageKey}_${this.sessionId}`,
        JSON.stringify(state)
      );
    } catch {
      // Storage full or unavailable, ignore silently
    }
  }

  /**
   * Restore buffer from sessionStorage.
   *
   * @returns true if buffer was restored, false otherwise
   */
  restore(): boolean {
    if (typeof sessionStorage === 'undefined') {
      return false;
    }

    try {
      const stored = sessionStorage.getItem(
        `${this.config.storageKey}_${this.sessionId}`
      );
      if (!stored) {
        return false;
      }

      const state: BufferState = JSON.parse(stored);

      // Validate restored data
      if (
        !state ||
        !Array.isArray(state.chunks) ||
        state.sessionId !== this.sessionId
      ) {
        return false;
      }

      this.chunks = state.chunks;
      this.sequence =
        state.chunks.length > 0
          ? Math.max(...state.chunks.map((c) => c.sequence)) + 1
          : 0;
      this.createdAt = state.createdAt;

      return this.chunks.length > 0;
    } catch {
      return false;
    }
  }

  /**
   * Remove buffer from sessionStorage.
   */
  private removeFromStorage(): void {
    if (typeof sessionStorage === 'undefined') {
      return;
    }

    try {
      sessionStorage.removeItem(
        `${this.config.storageKey}_${this.sessionId}`
      );
    } catch {
      // Ignore errors
    }
  }

  /**
   * Check if there's a recoverable buffer for a session.
   */
  static hasRecoverableBuffer(
    sessionId: string,
    storageKey: string = DEFAULT_CONFIG.storageKey
  ): boolean {
    if (typeof sessionStorage === 'undefined') {
      return false;
    }

    try {
      const stored = sessionStorage.getItem(`${storageKey}_${sessionId}`);
      if (!stored) {
        return false;
      }

      const state: BufferState = JSON.parse(stored);
      return Array.isArray(state.chunks) && state.chunks.length > 0;
    } catch {
      return false;
    }
  }

  /**
   * Get recoverable buffer content for a session.
   */
  static getRecoverableContent(
    sessionId: string,
    storageKey: string = DEFAULT_CONFIG.storageKey
  ): string | null {
    if (typeof sessionStorage === 'undefined') {
      return null;
    }

    try {
      const stored = sessionStorage.getItem(`${storageKey}_${sessionId}`);
      if (!stored) {
        return null;
      }

      const state: BufferState = JSON.parse(stored);
      if (!Array.isArray(state.chunks) || state.chunks.length === 0) {
        return null;
      }

      return state.chunks.map((c) => c.content).join('');
    } catch {
      return null;
    }
  }

  /**
   * Clear recoverable buffer for a session.
   */
  static clearRecoverableBuffer(
    sessionId: string,
    storageKey: string = DEFAULT_CONFIG.storageKey
  ): void {
    if (typeof sessionStorage === 'undefined') {
      return;
    }

    try {
      sessionStorage.removeItem(`${storageKey}_${sessionId}`);
    } catch {
      // Ignore errors
    }
  }
}
