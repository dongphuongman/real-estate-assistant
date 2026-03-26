import { describe, it, expect, vi, beforeEach } from '@jest/globals';
import {
  generateVisitorId,
  getVisitorIdFromCookies,
  setVisitorIdCookie,
} from '../visitor-tracking';

import { VISITOR_ID_COOKIE, VISITOR_ID_MAX_AGE } from '../visitor-tracking';

// Mock crypto
const mockRandomUUID = vi.fn();

Object.defineProperty(global, 'crypto', {
  value: { randomUUID: mockRandomUUID },
  writable: true,
});

describe('visitor-tracking', () => {
  describe('generateVisitorId', () => {
    beforeEach(() => {
      mockRandomUUID.mockClear();
    });

    it('should use crypto.randomUUID when available', () => {
      mockRandomUUID.mockReturnValue('test-uuid-123');
      const id = generateVisitorId();
      expect(id).toBe('test-uuid-123');
    });

    it('should fallback to UUIDv4 when crypto is not available', () => {
      Object.defineProperty(global, 'crypto', { value: undefined, writable: true });
      const id = generateVisitorId();
      expect(id).toMatch(/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}$/);
      expect(id).toHaveLength(36);
      // Restore crypto
      Object.defineProperty(global, 'crypto', {
        value: { randomUUID: mockRandomUUID },
        writable: true,
      });
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
      const cookieHeader = 'visitor_id=; other=value';
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

  describe('constants', () => {
    it('should have correct cookie name', () => {
      expect(VISITOR_ID_COOKIE).toBe('visitor_id');
    });

    it('should have correct max age (1 year)', () => {
      expect(VISITOR_ID_MAX_AGE).toBe(365 * 24 * 60 * 60);
    });
  });
});
