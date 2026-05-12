import {
  clusterMapPoints,
  analyzeClusterTypes,
  PROPERTY_TYPE_COLORS,
} from '../property-map-clustering';

describe('property-map-clustering', () => {
  it('returns points without clustering for small inputs', () => {
    const items = clusterMapPoints(
      [
        { id: 'a', lat: 52.23, lon: 21.01 },
        { id: 'b', lat: 52.24, lon: 21.02 },
      ],
      12
    );

    expect(items).toHaveLength(2);
    expect(items.every((i) => i.kind === 'point')).toBe(true);
  });

  it('clusters dense points into a single cluster', () => {
    const points = Array.from({ length: 80 }, (_, idx) => ({
      id: `p-${idx}`,
      lat: 52.23,
      lon: 21.01,
      title: `P${idx}`,
    }));

    const items = clusterMapPoints(points, 12);

    expect(items).toHaveLength(1);
    expect(items[0].kind).toBe('cluster');
    if (items[0].kind === 'cluster') {
      expect(items[0].count).toBe(80);
      expect(items[0].id).toMatch(/^cluster-\d+-\d+$/);
      expect(items[0].lat).toBeCloseTo(52.23, 6);
      expect(items[0].lon).toBeCloseTo(21.01, 6);
    }
  });

  it('does not cluster when zoom is high', () => {
    const points = Array.from({ length: 80 }, (_, idx) => ({
      id: `p-${idx}`,
      lat: 52.23,
      lon: 21.01,
    }));

    const items = clusterMapPoints(points, 18);
    expect(items).toHaveLength(80);
    expect(items.every((i) => i.kind === 'point')).toBe(true);
  });

  it('splits distant dense points into multiple clusters', () => {
    const groupA = Array.from({ length: 40 }, (_, idx) => ({
      id: `a-${idx}`,
      lat: 52.23,
      lon: 21.01,
    }));
    const groupB = Array.from({ length: 40 }, (_, idx) => ({
      id: `b-${idx}`,
      lat: 48.8566,
      lon: 2.3522,
    }));
    const points = [...groupA, ...groupB];

    const items = clusterMapPoints(points, 12);

    const counts = items.map((i) => (i.kind === 'cluster' ? i.count : 1));
    expect(counts.reduce((acc, v) => acc + v, 0)).toBe(80);
    expect(items.some((i) => i.kind === 'cluster')).toBe(true);
  });

  // New tests for cluster options
  describe('cluster options', () => {
    it('respects custom cellSizePx option', () => {
      const points = Array.from({ length: 100 }, (_, idx) => ({
        id: `p-${idx}`,
        lat: 52.23 + idx * 0.001, // Spread points slightly
        lon: 21.01 + idx * 0.001,
      }));

      // Smaller cell size = more clusters
      const smallCellItems = clusterMapPoints(points, 12, { cellSizePx: 30 });
      // Larger cell size = fewer clusters
      const largeCellItems = clusterMapPoints(points, 12, { cellSizePx: 120 });

      const smallCellClusters = smallCellItems.filter((i) => i.kind === 'cluster').length;
      const largeCellClusters = largeCellItems.filter((i) => i.kind === 'cluster').length;

      expect(smallCellClusters).toBeGreaterThanOrEqual(largeCellClusters);
    });

    it('respects maxZoomForClustering option', () => {
      const points = Array.from({ length: 80 }, (_, idx) => ({
        id: `p-${idx}`,
        lat: 52.23,
        lon: 21.01,
      }));

      // Default max zoom is 15, so at zoom 14 it should cluster
      const itemsAtZoom14 = clusterMapPoints(points, 14);
      expect(itemsAtZoom14[0].kind).toBe('cluster');

      // With max zoom of 12, at zoom 14 it should NOT cluster
      const itemsWithLowMaxZoom = clusterMapPoints(points, 14, { maxZoomForClustering: 12 });
      expect(itemsWithLowMaxZoom.every((i) => i.kind === 'point')).toBe(true);
    });
  });

  // Tests for property type analysis
  describe('property type analysis', () => {
    it('identifies dominant type when >50%', () => {
      const points = Array.from({ length: 80 }, (_, idx) => ({
        id: `p-${idx}`,
        lat: 52.23,
        lon: 21.01,
        property_type: idx < 50 ? 'apartment' : 'house', // 62.5% apartments
      }));

      const items = clusterMapPoints(points, 12);

      expect(items[0].kind).toBe('cluster');
      if (items[0].kind === 'cluster') {
        expect(items[0].dominantType).toBe('apartment');
        expect(items[0].isMixed).toBe(false);
        expect(items[0].typeDistribution.get('apartment')).toBeCloseTo(62.5, 1);
        expect(items[0].typeDistribution.get('house')).toBeCloseTo(37.5, 1);
      }
    });

    it('identifies mixed type when no type >50%', () => {
      const points = Array.from({ length: 100 }, (_, idx) => ({
        id: `p-${idx}`,
        lat: 52.23,
        lon: 21.01,
        property_type: idx < 40 ? 'apartment' : idx < 70 ? 'house' : 'studio', // 40%, 30%, 30%
      }));

      const items = clusterMapPoints(points, 12);

      expect(items[0].kind).toBe('cluster');
      if (items[0].kind === 'cluster') {
        expect(items[0].dominantType).toBe(null);
        expect(items[0].isMixed).toBe(true);
      }
    });

    it("handles empty property type as 'other'", () => {
      const points = Array.from({ length: 80 }, (_, idx) => ({
        id: `p-${idx}`,
        lat: 52.23,
        lon: 21.01,
        property_type: undefined,
      }));

      const items = clusterMapPoints(points, 12);

      expect(items[0].kind).toBe('cluster');
      if (items[0].kind === 'cluster') {
        expect(items[0].dominantType).toBe('other');
      }
    });
  });

  // Tests for edge cases
  describe('edge cases', () => {
    it('handles very dense areas (1000+ points)', () => {
      // nosemgrep: weak-random.random — test data generation, not security-sensitive
      const points = Array.from({ length: 1500 }, (_, idx) => ({
        id: `p-${idx}`,
        lat: 52.23 + Math.random() * 0.01, // nosemgrep: weak-random.random
        lon: 21.01 + Math.random() * 0.01, // nosemgrep: weak-random.random
      }));

      const start = performance.now();
      const items = clusterMapPoints(points, 12);
      const duration = performance.now() - start;

      // Should complete in under 100ms
      expect(duration).toBeLessThan(100);

      // All points should be accounted for
      const totalCount = items.reduce((acc, item) => {
        if (item.kind === 'cluster') return acc + item.count;
        return acc + 1;
      }, 0);
      expect(totalCount).toBe(1500);
    });

    it('handles single point', () => {
      const items = clusterMapPoints([{ id: 'single', lat: 52.23, lon: 21.01 }], 12);

      expect(items).toHaveLength(1);
      expect(items[0].kind).toBe('point');
    });

    it('handles empty input', () => {
      const items = clusterMapPoints([], 12);
      expect(items).toHaveLength(0);
    });
  });
});

describe('PROPERTY_TYPE_COLORS', () => {
  it('has colors for all expected property types', () => {
    expect(PROPERTY_TYPE_COLORS.apartment).toBeDefined();
    expect(PROPERTY_TYPE_COLORS.house).toBeDefined();
    expect(PROPERTY_TYPE_COLORS.studio).toBeDefined();
    expect(PROPERTY_TYPE_COLORS.loft).toBeDefined();
    expect(PROPERTY_TYPE_COLORS.townhouse).toBeDefined();
    expect(PROPERTY_TYPE_COLORS.other).toBeDefined();
  });
});

describe('analyzeClusterTypes', () => {
  it('returns correct distribution for mixed types', () => {
    const points = [
      { lat: 52.23, lon: 21.01, property_type: 'apartment' },
      { lat: 52.23, lon: 21.01, property_type: 'apartment' },
      { lat: 52.23, lon: 21.01, property_type: 'apartment' },
      { lat: 52.23, lon: 21.01, property_type: 'house' },
      { lat: 52.23, lon: 21.01, property_type: 'studio' },
    ];

    const result = analyzeClusterTypes(points);

    expect(result.dominantType).toBe('apartment'); // 60% = dominant (>50%)
    expect(result.isMixed).toBe(false);
    expect(result.distribution.get('apartment')).toBe(60);
    expect(result.distribution.get('house')).toBe(20);
    expect(result.distribution.get('studio')).toBe(20);
  });
});
