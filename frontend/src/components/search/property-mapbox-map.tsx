"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import mapboxgl, { type LngLatBoundsLike, type Map as MapboxMap } from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import type { FeatureCollection, GeoJsonProperties, Geometry } from "geojson";

import { computeBounds, computeCenter, type PropertyMapPoint } from "./property-map-utils";
import { clusterMapPoints, type ClusteredMapItem } from "./property-map-clustering";

interface MapboxPropertyMapProps {
  points: PropertyMapPoint[];
  mapboxToken?: string;
  showHeatmap?: boolean;
  heatmapIntensity?: number;
  showClusters?: boolean;
  onMarkerClick?: (point: PropertyMapPoint) => void;
  className?: string;
}

const DEFAULT_CENTER: [number, number] = [21.0122, 52.2297]; // [lon, lat] for Warsaw

export default function PropertyMapboxMap({
  points,
  mapboxToken,
  showHeatmap = false,
  heatmapIntensity = 1,
  showClusters = true,
  onMarkerClick,
  className = "",
}: MapboxPropertyMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<MapboxMap | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [zoom, setZoom] = useState(12);

  const center = useMemo(() => {
    const computed = computeCenter(points);
    return computed ? [computed.lon, computed.lat] as [number, number] : DEFAULT_CENTER;
  }, [points]);

  const bounds = useMemo(() => {
    const computed = computeBounds(points);
    if (!computed) return null;
    return [[computed[0][1], computed[0][0]], [computed[1][1], computed[1][0]]] as LngLatBoundsLike;
  }, [points]);

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    if (!mapboxToken) {
      console.warn("Mapbox token not provided. Using fallback styling.");
    }

    mapboxgl.accessToken = mapboxToken || "";

    const mapInstance = new mapboxgl.Map({
      container: mapContainer.current,
      style: "mapbox://styles/mapbox/streets-v12",
      center,
      zoom: 12,
      scrollZoom: false,
    });

    mapInstance.on("load", () => {
      setMapLoaded(true);
      map.current = mapInstance;

      // Add navigation controls
      mapInstance.addControl(new mapboxgl.NavigationControl(), "top-right");
    });

    mapInstance.on("zoom", () => {
      setZoom(mapInstance.getZoom());
    });

    mapInstance.on("moveend", () => {
      setZoom(mapInstance.getZoom());
    });

    return () => {
      mapInstance.remove();
      map.current = null;
    };
  }, [mapboxToken, center]);

  // Fit bounds when points change
  useEffect(() => {
    if (!map.current || !bounds || !mapLoaded) return;
    map.current.fitBounds(bounds, { padding: 50, maxZoom: 15 });
  }, [bounds, mapLoaded]);

  // Update markers and heatmap when points or zoom changes
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    const mapInstance = map.current;

    // Remove existing sources and layers
    const existingSources = ["markers", "heatmap", "clusters"];
    existingSources.forEach((sourceId) => {
      if (mapInstance.getSource(sourceId)) {
        mapInstance.removeLayer(sourceId);
        mapInstance.removeSource(sourceId);
      }
    });

    // Remove existing markers
    const markers = document.querySelectorAll(".mapboxgl-marker");
    markers.forEach((marker) => marker.remove());

    if (points.length === 0) return;

    // Add heatmap layer if enabled
    if (showHeatmap && points.length > 1) {
      const heatData: FeatureCollection<Geometry, GeoJsonProperties> = {
        type: "FeatureCollection",
        features: points.map((point) => ({
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [point.lon, point.lat],
          },
          properties: {
            weight: point.price ? 1 / (point.price / 10000 + 1) : 0.5,
          },
        })),
      };

      mapInstance.addSource("heatmap", {
        type: "geojson",
        data: heatData,
      });

      mapInstance.addLayer({
        id: "heatmap",
        type: "heatmap",
        source: "heatmap",
        paint: {
          "heatmap-weight": ["get", "weight"],
          "heatmap-intensity": heatmapIntensity,
          "heatmap-radius": Math.max(10, 30 - zoom),
          "heatmap-opacity": 0.7,
          "heatmap-color": [
            "interpolate",
            ["linear"],
            ["heatmap-density"],
            0,
            "rgba(33, 102, 172, 0)",
            0.2,
            "rgb(103, 169, 207)",
            0.4,
            "rgb(209, 229, 240)",
            0.6,
            "rgb(253, 219, 199)",
            0.8,
            "rgb(239, 138, 98)",
            1,
            "rgb(178, 24, 43)",
          ],
        },
      });
    }

    // Add markers
    const items = showClusters ? clusterMapPoints(points, zoom) : points.map((point) => ({ kind: "point", point }));

    items.forEach((item) => {
      if (item.kind === "point") {
        const p = item.point;
        const el = document.createElement("div");
        el.className = "cursor-pointer";
        el.innerHTML = `<div style="width:14px;height:14px;background:#2563eb;border-radius:9999px;border:2px solid white;box-shadow:0 1px 2px rgba(0,0,0,0.3)"></div>`;
        el.addEventListener("click", () => onMarkerClick?.(p));

        new mapboxgl.Marker({ element: el })
          .setLngLat([p.lon, p.lat])
          .setPopup(
            new mapboxgl.Popup({ offset: 15 }).setHTML(`
              <div style="min-width:150px">
                <div class="font-semibold mb-1">${p.title ?? "Untitled Property"}</div>
                <div class="text-sm text-gray-600">${[p.city, p.country].filter(Boolean).join(", ") || "Location unavailable"}</div>
                <div class="text-sm font-medium mt-1">${typeof p.price === "number" ? `$${p.price.toLocaleString()}` : "Price on request"}</div>
              </div>
            `)
          )
          .addTo(mapInstance);
      } else {
        // Cluster
        const cluster = item as Extract<ClusteredMapItem, { kind: "cluster" }>;
        const el = document.createElement("div");
        el.className = "cursor-pointer";
        el.innerHTML = `<div style="min-width:30px;height:30px;padding:0 8px;background:#1d4ed8;color:white;border-radius:9999px;border:2px solid white;box-shadow:0 1px 2px rgba(0,0,0,0.35);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;line-height:1">${cluster.count}</div>`;
        el.addEventListener("click", () => {
          const clusterBounds = computeBounds(cluster.points);
          if (clusterBounds) {
            mapInstance.fitBounds(
              [[clusterBounds[0][1], clusterBounds[0][0]], [clusterBounds[1][1], clusterBounds[1][0]]],
              { padding: 50, maxZoom: Math.min(zoom + 2, 18) }
            );
          }
        });

        new mapboxgl.Marker({ element: el })
          .setLngLat([cluster.lon, cluster.lat])
          .setPopup(
            new mapboxgl.Popup({ offset: 15 }).setHTML(`
              <div style="min-width:150px">
                <div class="font-semibold mb-1">${cluster.count} properties in this area</div>
                <div class="text-sm text-gray-600">Click to zoom in</div>
              </div>
            `)
          )
          .addTo(mapInstance);
      }
    });
  }, [points, zoom, mapLoaded, showHeatmap, heatmapIntensity, showClusters, onMarkerClick]);

  return (
    <div className={`rounded-lg border bg-card text-card-foreground shadow-sm overflow-hidden ${className}`}>
      <div ref={mapContainer} className="h-[420px] w-full" aria-label="Property map with Mapbox" />
      {!mapboxToken && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted/50">
          <p className="text-sm text-muted-foreground">Mapbox token not configured. Add NEXT_PUBLIC_MAPBOX_TOKEN to your environment.</p>
        </div>
      )}
    </div>
  );
}
