/**
 * Unit tests for geo-validation utilities
 */

import {
  validatePolygon,
  calculatePolygonArea,
  pointInPolygon,
  serializePolygonToUrl,
  deserializePolygonFromUrl,
  POLYGON_LIMITS,
  type PolygonCoordinates,
} from '../geo-validation';

describe('geo-validation', () => {
  describe('validatePolygon', () => {
    it('should reject empty coordinates', () => {
      const result = validatePolygon([]);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('No polygon coordinates');
    });

    it('should reject empty outer ring', () => {
      const result = validatePolygon([[]]);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('empty');
    });

    it('should reject polygon with less than 3 vertices', () => {
      const polygon: PolygonCoordinates[] = [
        [
          [0, 0],
          [1, 1],
        ],
      ];
      const result = validatePolygon(polygon);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('at least 3 vertices');
    });

    it('should accept valid triangle', () => {
      const polygon: PolygonCoordinates[] = [
        [
          [0, 0],
          [1, 0],
          [0.5, 1],
          [0, 0], // closed
        ],
      ];
      const result = validatePolygon(polygon);
      expect(result.valid).toBe(true);
      expect(result.vertexCount).toBe(4);
    });

    it('should reject polygon with too many vertices', () => {
      const vertices: [number, number][] = [];
      for (let i = 0; i <= POLYGON_LIMITS.MAX_VERTICES; i++) {
        vertices.push([i * 0.01, i * 0.01]);
      }
      const polygon: PolygonCoordinates[] = [vertices];

      const result = validatePolygon(polygon);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('too many vertices');
    });

    it('should reject polygon with area too large', () => {
      // Create a polygon spanning a large portion of the globe
      const polygon: PolygonCoordinates[] = [
        [
          [-180, -80],
          [180, -80],
          [180, 80],
          [-180, 80],
          [-180, -80],
        ],
      ];

      const result = validatePolygon(polygon);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('Area too large');
    });

    it('should return area and vertex count for valid polygon', () => {
      // Small polygon in Berlin (~1km x 1km)
      const polygon: PolygonCoordinates[] = [
        [
          [13.4, 52.5],
          [13.41, 52.5],
          [13.41, 52.51],
          [13.4, 52.51],
          [13.4, 52.5],
        ],
      ];

      const result = validatePolygon(polygon);
      expect(result.valid).toBe(true);
      expect(result.areaSqKm).toBeDefined();
      expect(result.areaSqKm).toBeLessThan(10); // Should be small
      expect(result.vertexCount).toBe(5);
    });
  });

  describe('calculatePolygonArea', () => {
    it('should return 0 for empty coordinates', () => {
      expect(calculatePolygonArea([])).toBe(0);
    });

    it('should return 0 for less than 3 points', () => {
      const coords: PolygonCoordinates = [
        [0, 0],
        [1, 1],
      ];
      expect(calculatePolygonArea(coords)).toBe(0);
    });

    it('should calculate small area correctly', () => {
      // ~1km x 1km square in Berlin
      const coords: PolygonCoordinates = [
        [13.4, 52.5],
        [13.41, 52.5],
        [13.41, 52.51],
        [13.4, 52.51],
        [13.4, 52.5],
      ];

      const area = calculatePolygonArea(coords);
      // Should be approximately 1.1 km² (varies by latitude)
      expect(area).toBeGreaterThan(0.5);
      expect(area).toBeLessThan(2);
    });
  });

  describe('pointInPolygon', () => {
    const square: PolygonCoordinates = [
      [0, 0],
      [10, 0],
      [10, 10],
      [0, 10],
      [0, 0],
    ];

    it('should return true for point inside polygon', () => {
      expect(pointInPolygon(5, 5, square)).toBe(true);
    });

    it('should return false for point outside polygon', () => {
      expect(pointInPolygon(15, 15, square)).toBe(false);
    });

    it('should handle edge cases (ray-casting varies)', () => {
      // Ray-casting has undefined behavior on exact edges
      // This test verifies the function doesn't crash
      const result = pointInPolygon(0, 5, square);
      expect(typeof result).toBe('boolean');
    });

    it('should return false for empty polygon', () => {
      expect(pointInPolygon(5, 5, [])).toBe(false);
    });
  });

  describe('URL serialization', () => {
    const testPolygon: PolygonCoordinates = [
      [13.4, 52.5],
      [13.41, 52.5],
      [13.41, 52.51],
      [13.4, 52.51],
      [13.4, 52.5],
    ];

    it('should serialize and deserialize correctly', () => {
      const serialized = serializePolygonToUrl(testPolygon);
      const deserialized = deserializePolygonFromUrl(serialized);

      expect(deserialized).not.toBeNull();
      expect(deserialized![0]).toEqual(testPolygon);
    });

    it('should return null for invalid JSON', () => {
      const result = deserializePolygonFromUrl('not-json');
      expect(result).toBeNull();
    });

    it('should return null for non-array', () => {
      const result = deserializePolygonFromUrl('"string"');
      expect(result).toBeNull();
    });

    it('should return null for wrong coordinate format', () => {
      const result = deserializePolygonFromUrl('[[1, 2, 3]]'); // 3 elements instead of 2
      expect(result).toBeNull();
    });

    it('should return null for too few vertices', () => {
      const result = deserializePolygonFromUrl('[[1, 2], [3, 4]]');
      expect(result).toBeNull();
    });

    it('should return null for null input', () => {
      const result = deserializePolygonFromUrl(null);
      expect(result).toBeNull();
    });
  });
});
