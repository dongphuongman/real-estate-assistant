import {
  aggregateByDistrict,
  pointInPolygon,
  getDistrictColor,
  loadDistrictBoundaries,
} from '../district-aggregation';
import type { PropertyMapPoint } from '@/components/search/property-map-utils';
import type { DistrictBoundary, DistrictStats } from '../district-aggregation';

describe('district-aggregation', () => {
  describe('aggregateByDistrict', () => {
    const mockPoints: PropertyMapPoint[] = [
      { id: '1', lat: 52.229, lon: 21.012, price: 500000, price_per_sqm: 10000 },
      { id: '2', lat: 52.235, lon: 21.018, price: 600000, price_per_sqm: 12000 },
      { id: '3', lat: 52.24, lon: 21.02, price: 700000, price_per_sqm: 14000 },
      // Point outside any district
      { id: '4', lat: 51.0, lon: 20.0, price: 400000, price_per_sqm: 8000 },
    ];

    const mockBoundaries: DistrictBoundary[] = [
      {
        id: 'district-1',
        name: 'Śródmieście',
        center: [52.23, 21.01],
        bounds: [
          [52.22, 21.0],
          [52.24, 21.02],
        ],
        polygon: [
          [21.0, 52.22],
          [21.02, 52.24],
          [21.0, 52.22], // Triangle
        ],
      },
      {
        id: 'district-2',
        name: 'Mokotów',
        center: [52.235, 21.018],
        bounds: [
          [52.23, 21.015],
          [52.24, 21.02],
        ],
        polygon: [
          [21.015, 52.23],
          [21.02, 52.24],
          [21.015, 52.23], // Triangle
        ],
      },
    ];

    it('should aggregate points by district', () => {
      const result = aggregateByDistrict(mockPoints, mockBoundaries);

      expect(result).toHaveLength(2);
      expect(result[0].name).toBe('Śródmieście');
      expect(result[0].count).toBe(3);
      expect(result[0].avgPrice).toBe(600000);
      expect(result[1].minPrice).toBe(500000);
      expect(result[1].maxPrice).toBe(700000);
      expect(result[1].avgPricePerSqm).toBe(12000);
    });

    it('should return only districts with points', () => {
      const emptyResult = aggregateByDistrict([], mockBoundaries);
      expect(emptyResult).toHaveLength(0);

      const noPointsResult = aggregateByDistrict(mockPoints, []);
      expect(noPointsResult).toHaveLength(0);
    });

    it('should handle points outside all districts', () => {
      const outsidePoints: PropertyMapPoint[] = [
        { id: '5', lat: 0, lon: 0, price: 100000, price_per_sqm: 2000 },
      ];
      const result = aggregateByDistrict(outsidePoints, mockBoundaries);
      expect(result).toHaveLength(0);
    });
  });

  describe('pointInPolygon', () => {
    it('should correctly identify points inside polygon', () => {
      const triangle = [
        [0, 0],
        [10, 0],
        [0, 10],
        [0, 0],
      ];
      expect(pointInPolygon(0, 0, triangle)).toBe(true);
      expect(pointInPolygon(5, 5, triangle)).toBe(false);
      expect(pointInPolygon(0, 5, triangle)).toBe(false);
    });

    it('should return false for polygon with less than 3 points', () => {
      expect(pointInPolygon(0, 0, [[0, 0]])).toBe(false);
      expect(
        pointInPolygon(0, 0, [
          [1, 0],
          [2, 0],
        ])
      ).toBe(false);
    });
  });

  describe('getDistrictColor', () => {
    it('should return gray for null avgPrice', () => {
      expect(getDistrictColor(null, 1000000)).toBe('rgba(156, 163, 175, 0.3)');
    });

    it('should return color based on ratio', () => {
      expect(getDistrictColor(50000, 100000)).toMatch(/rgba\.*0\.3\)$/);
      expect(getDistrictColor(75000, 100000)).toMatch(/rgba\.*0\.5\)$/);
    });
  });

  describe('loadDistrictBoundaries', () => {
    it('should return Warsaw districts for Warsaw', async () => {
      const result = await loadDistrictBoundaries('Warsaw');
      expect(result.length).toBeGreaterThan(0);
      expect(result[0].name).toBeDefined();
    });

    it('should return Warsaw districts for Warszawa', async () => {
      const result = await loadDistrictBoundaries('Warszawa');
      expect(result.length).toBeGreaterThan(1);
    });

    it('should return empty array for other cities', async () => {
      const result = await loadDistrictBoundaries('Berlin');
      expect(result).toEqual([]);
    });
  });
});
