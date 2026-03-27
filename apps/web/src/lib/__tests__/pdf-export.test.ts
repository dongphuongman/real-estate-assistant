import { describe, it, expect } from '@jest/globals';

/**
 * Tests for PDF export utilities
 *
 * Note: PDF generation requires DOM elements and jsPDF which cannot be fully
 * tested in jsdom. These tests verify the functions exist and have correct types.
 */

describe('pdf-export utilities', () => {
  describe('exportTCOToPDF', () => {
    it('should be a function', async () => {
      const { exportTCOToPDF } = await import('../pdf-export');
      expect(typeof exportTCOToPDF).toBe('function');
    });
  });

  describe('exportTCOComparisonToPDF', () => {
    it('should be a function', async () => {
      const { exportTCOComparisonToPDF } = await import('../pdf-export');
      expect(typeof exportTCOComparisonToPDF).toBe('function');
    });
  });

  describe('captureElementToPDF', () => {
    it('should be a function', async () => {
      const { captureElementToPDF } = await import('../pdf-export');
      expect(typeof captureElementToPDF).toBe('function');
    });
  });
});
