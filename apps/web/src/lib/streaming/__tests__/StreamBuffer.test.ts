/**
 * Tests for StreamBuffer.
 *
 * Task #74: Response Streaming Improvements
 */

import { StreamBuffer } from '../StreamBuffer';

// Mock sessionStorage
const mockStorage: Record<string, string> = {};
const mockSessionStorage = {
  getItem: jest.fn((key: string) => mockStorage[key] || null),
  setItem: jest.fn((key: string, value: string) => {
    mockStorage[key] = value;
  }),
  removeItem: jest.fn((key: string) => {
    delete mockStorage[key];
  }),
  clear: jest.fn(() => {
    Object.keys(mockStorage).forEach((key) => delete mockStorage[key]);
  }),
};

Object.defineProperty(window, 'sessionStorage', {
  value: mockSessionStorage,
});

describe('StreamBuffer', () => {
  let buffer: StreamBuffer;

  beforeEach(() => {
    jest.clearAllMocks();
    Object.keys(mockStorage).forEach((key) => delete mockStorage[key]);
    buffer = new StreamBuffer('test-session', 'test-request');
  });

  describe('add', () => {
    it('should add chunks with sequence numbers', () => {
      const seq1 = buffer.add('chunk1');
      const seq2 = buffer.add('chunk2');
      const seq3 = buffer.add('chunk3');

      expect(seq1).toBe(0);
      expect(seq2).toBe(1);
      expect(seq3).toBe(2);
    });

    it('should enforce max chunks limit', () => {
      const smallBuffer = new StreamBuffer('test', undefined, { maxChunks: 3 });

      smallBuffer.add('chunk1');
      smallBuffer.add('chunk2');
      smallBuffer.add('chunk3');
      smallBuffer.add('chunk4'); // Should push out chunk1

      const content = smallBuffer.getBufferedContent();
      expect(content).toBe('chunk2chunk3chunk4');
    });
  });

  describe('getBufferedContent', () => {
    it('should return empty string when no chunks', () => {
      expect(buffer.getBufferedContent()).toBe('');
    });

    it('should concatenate all chunks', () => {
      buffer.add('Hello ');
      buffer.add('World');
      buffer.add('!');

      expect(buffer.getBufferedContent()).toBe('Hello World!');
    });
  });

  describe('getLastSequence', () => {
    it('should return 0 when no chunks', () => {
      expect(buffer.getLastSequence()).toBe(0);
    });

    it('should return last sequence number', () => {
      buffer.add('a');
      buffer.add('b');
      buffer.add('c');

      expect(buffer.getLastSequence()).toBe(2);
    });
  });

  describe('getStats', () => {
    it('should return correct statistics', () => {
      buffer.add('hello');
      buffer.add('world');

      const stats = buffer.getStats();

      expect(stats.totalChunks).toBe(2);
      expect(stats.totalBytes).toBe(10); // "hello" + "world" = 10 bytes
      expect(stats.oldestChunk).toBeDefined();
      expect(stats.newestChunk).toBeDefined();
    });
  });

  describe('clear', () => {
    it('should clear all chunks', () => {
      buffer.add('test');
      buffer.clear();

      expect(buffer.getBufferedContent()).toBe('');
      expect(buffer.getLastSequence()).toBe(0);
    });
  });

  describe('persist and restore', () => {
    it('should persist to sessionStorage', () => {
      buffer.add('persisted');
      buffer.add('content');
      buffer.persist();

      expect(mockSessionStorage.setItem).toHaveBeenCalled();
    });

    it('should restore from sessionStorage', () => {
      // First, persist some data
      buffer.add('restored');
      buffer.persist();

      // Create new buffer and restore
      const newBuffer = new StreamBuffer('test-session');
      const restored = newBuffer.restore();

      expect(restored).toBe(true);
      expect(newBuffer.getBufferedContent()).toBe('restored');
    });

    it('should return false when no data to restore', () => {
      const newBuffer = new StreamBuffer('no-data-session');
      const restored = newBuffer.restore();

      expect(restored).toBe(false);
    });
  });

  describe('static methods', () => {
    it('hasRecoverableBuffer should detect existing buffer', () => {
      buffer.add('test');
      buffer.persist();

      expect(StreamBuffer.hasRecoverableBuffer('test-session')).toBe(true);
      expect(StreamBuffer.hasRecoverableBuffer('no-session')).toBe(false);
    });

    it('getRecoverableContent should return content', () => {
      buffer.add('recoverable');
      buffer.persist();

      const content = StreamBuffer.getRecoverableContent('test-session');
      expect(content).toBe('recoverable');
    });

    it('clearRecoverableBuffer should remove buffer', () => {
      buffer.add('to-clear');
      buffer.persist();

      StreamBuffer.clearRecoverableBuffer('test-session');

      expect(StreamBuffer.hasRecoverableBuffer('test-session')).toBe(false);
    });
  });
});
