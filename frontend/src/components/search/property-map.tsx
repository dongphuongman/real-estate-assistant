"use client";

import { useEffect, useMemo } from "react";
import { divIcon, type LatLngBoundsExpression } from "leaflet";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";

import { computeBounds, computeCenter, type PropertyMapPoint } from "./property-map-utils";

function FitBounds({ bounds }: { bounds: LatLngBoundsExpression | null }) {
  const map = useMap();
  useEffect(() => {
    if (!bounds) return;
    map.fitBounds(bounds, { padding: [24, 24] });
  }, [bounds, map]);
  return null;
}

export default function PropertyMap({ points }: { points: PropertyMapPoint[] }) {
  const center = useMemo(() => computeCenter(points) ?? { lat: 52.2297, lon: 21.0122 }, [points]);
  const bounds = useMemo(() => computeBounds(points), [points]);

  const markerIcon = useMemo(
    () =>
      divIcon({
        className: "",
        html: `<div style="width:14px;height:14px;background:#2563eb;border-radius:9999px;border:2px solid white;box-shadow:0 1px 2px rgba(0,0,0,0.3)"></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      }),
    []
  );

  return (
    <div className="rounded-lg border bg-card text-card-foreground shadow-sm overflow-hidden">
      <div className="h-[420px] w-full" aria-label="Property map">
        <MapContainer
          center={[center.lat, center.lon]}
          zoom={12}
          scrollWheelZoom={false}
          className="h-full w-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FitBounds bounds={bounds as LatLngBoundsExpression | null} />
          {points.map((p) => (
            <Marker key={p.id} position={[p.lat, p.lon]} icon={markerIcon}>
              <Popup>
                <div className="space-y-1">
                  <div className="font-semibold">{p.title ?? "Untitled Property"}</div>
                  <div className="text-sm">
                    {[p.city, p.country].filter(Boolean).join(", ") || "Location unavailable"}
                  </div>
                  <div className="text-sm font-medium">
                    {typeof p.price === "number" ? `$${p.price.toLocaleString()}` : "Price on request"}
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}

