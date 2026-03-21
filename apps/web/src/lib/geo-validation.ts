/**
 * Polygon validation utilities for geo-bounding box search.
 */

export type PolygonCoordinates = [number, number][]; // [lon, lat] pairs

export const POLYGON_LIMITS = {
  MAX_VERTICES: 100, // Prevent overly complex polygons
  MAX_AREA_SQKM: 10000, // ~100km radius max (roughly a small country)
  MIN_VERTICES: 3, // Triangle minimum
} as const;

export interface PolygonValidationResult {
  valid: boolean;
  error?: string;
  areaSqKm?: number;
  vertexCount?: number;
}

/**
 * Calculate the area of a polygon using the Shoelace formula.
 * Returns area in square kilometers.
 *
 * @param coordinates - Array of [lon, lat] coordinate pairs
 * @returns Area in square kilometers
 */
export function calculatePolygonArea(coordinates: PolygonCoordinates): number {
  if (!coordinates || coordinates.length < 3) return 0;

  const EARTH_RADIUS_KM = 6371;

  // Convert to radians and calculate area using spherical excess
  let area = 0;
  const n = coordinates.length;

  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    const lat1 = (coordinates[i][1] * Math.PI) / 180;
    const lat2 = (coordinates[j][1] * Math.PI) / 180;
    const lonDiff = ((coordinates[j][0] - coordinates[i][0]) * Math.PI) / 180;

    area += lonDiff * (2 + Math.sin(lat1) + Math.sin(lat2));
  }

  // Take absolute value and multiply by R^2 / 2
  area = Math.abs((area * EARTH_RADIUS_KM * EARTH_RADIUS_KM) / 2);

  return area;
}

/**
 * Validate a polygon for search operations.
 *
 * @param coordinates - Array of polygon rings (first ring is outer boundary)
 * @returns Validation result with error message if invalid
 */
export function validatePolygon(coordinates: PolygonCoordinates[]): PolygonValidationResult {
  // Check if coordinates exist
  if (!coordinates || coordinates.length === 0) {
    return {
      valid: false,
      error: 'No polygon coordinates provided',
      vertexCount: 0,
    };
  }

  // Get the outer ring (first array)
  const outerRing = coordinates[0];
  if (!outerRing || outerRing.length === 0) {
    return {
      valid: false,
      error: 'Polygon outer ring is empty',
      vertexCount: 0,
    };
  }

  const vertexCount = outerRing.length;

  // Check minimum vertices (triangle)
  if (vertexCount < POLYGON_LIMITS.MIN_VERTICES) {
    return {
      valid: false,
      error: `Polygon must have at least ${POLYGON_LIMITS.MIN_VERTICES} vertices`,
      vertexCount,
    };
  }

  // Check maximum vertices (prevent DoS)
  if (vertexCount > POLYGON_LIMITS.MAX_VERTICES) {
    return {
      valid: false,
      error: `Polygon has too many vertices (${vertexCount}/${POLYGON_LIMITS.MAX_VERTICES})`,
      vertexCount,
    };
  }

  // Calculate area
  const areaSqKm = calculatePolygonArea(outerRing);

  // Check maximum area
  if (areaSqKm > POLYGON_LIMITS.MAX_AREA_SQKM) {
    return {
      valid: false,
      error: `Area too large (${Math.round(areaSqKm).toLocaleString()} km², max ${POLYGON_LIMITS.MAX_AREA_SQKM.toLocaleString()} km²)`,
      areaSqKm,
      vertexCount,
    };
  }

  return {
    valid: true,
    areaSqKm,
    vertexCount,
  };
}

/**
 * Check if a point is inside a polygon using ray casting algorithm.
 *
 * @param lat - Latitude of the point
 * @param lon - Longitude of the point
 * @param polygon - Polygon coordinates (first ring)
 * @returns True if point is inside polygon
 */
export function pointInPolygon(
  lat: number,
  lon: number,
  polygon: PolygonCoordinates
): boolean {
  if (!polygon || polygon.length < 3) return false;

  let inside = false;
  const n = polygon.length;

  for (let i = 0, j = n - 1; i < n; j = i++) {
    const xi = polygon[i][0]; // lon
    const yi = polygon[i][1]; // lat
    const xj = polygon[j][0]; // lon
    const yj = polygon[j][1]; // lat

    const intersect =
      yi > lat !== yj > lat && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi;

    if (intersect) inside = !inside;
  }

  return inside;
}

/**
 * Serialize polygon coordinates to a URL-safe string.
 *
 * @param coordinates - Polygon coordinates (single ring)
 * @returns URL-safe string representation
 */
export function serializePolygonToUrl(coordinates: PolygonCoordinates): string {
  return JSON.stringify(coordinates);
}

/**
 * Deserialize polygon coordinates from URL string.
 *
 * @param paramString - URL parameter value
 * @returns Polygon coordinates or null if invalid
 */
export function deserializePolygonFromUrl(
  paramString: string | null
): PolygonCoordinates[] | null {
  if (!paramString) return null;

  try {
    const coords = JSON.parse(paramString);

    // Validate it's an array of coordinate pairs
    if (!Array.isArray(coords) || coords.length < 3) {
      return null;
    }

    // Validate each coordinate is [number, number]
    for (const coord of coords) {
      if (
        !Array.isArray(coord) ||
        coord.length !== 2 ||
        typeof coord[0] !== 'number' ||
        typeof coord[1] !== 'number'
      ) {
        return null;
      }
    }

    return [coords as PolygonCoordinates];
  } catch {
    return null;
  }
}
