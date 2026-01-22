import { SearchResultItem } from "@/lib/types";

export type PropertyMapPoint = {
  id: string;
  lat: number;
  lon: number;
  title?: string;
  city?: string;
  country?: string;
  price?: number;
};

export function extractMapPoints(results: SearchResultItem[]): PropertyMapPoint[] {
  return results.reduce<PropertyMapPoint[]>((acc, item, index) => {
    const prop = item.property;
    const lat = prop.latitude;
    const lon = prop.longitude;
    if (typeof lat !== "number" || typeof lon !== "number") return acc;
    const id = prop.id ?? `unknown-${index}`;
    acc.push({
      id,
      lat,
      lon,
      title: prop.title ?? undefined,
      city: prop.city ?? undefined,
      country: prop.country ?? undefined,
      price: prop.price ?? undefined,
    });
    return acc;
  }, []);
}

export type MapBounds = [[number, number], [number, number]];

export function computeBounds(points: PropertyMapPoint[]): MapBounds | null {
  if (!points.length) return null;
  const lats = points.map((p) => p.lat);
  const lons = points.map((p) => p.lon);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  return [
    [minLat, minLon],
    [maxLat, maxLon],
  ];
}

export function computeCenter(points: PropertyMapPoint[]): { lat: number; lon: number } | null {
  if (!points.length) return null;
  const sum = points.reduce(
    (acc, p) => ({ lat: acc.lat + p.lat, lon: acc.lon + p.lon }),
    { lat: 0, lon: 0 }
  );
  return { lat: sum.lat / points.length, lon: sum.lon / points.length };
}
