'use client';

import { PROPERTY_TYPE_COLORS, type ClusterTypeAnalysis } from './property-map-clustering';

interface ClusterMarkerProps {
  count: number;
  dominantType: string | null;
  typeDistribution: Map<string, number>;
  isMixed: boolean;
}

/**
 * Get the color for a cluster based on dominant property type
 */
export function getClusterColor(dominantType: string | null, isMixed: boolean): string {
  if (isMixed) {
    return "#6b7280"; // gray for mixed clusters
  }
  return PROPERTY_TYPE_COLORS[dominantType || "other"] || PROPERTY_TYPE_COLORS.other;
}

/**
 * Generate a segmented bar for mixed-type clusters
 */
export function generateMixedTypeBar(distribution: Map<string, number>): string {
  const segments: string[] = [];
  let accumulatedWidth = 0;

  // Sort by percentage descending, take top 3
  const sortedTypes = Array.from(distribution.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);

  for (const [type, percentage] of sortedTypes) {
    const width = Math.round(percentage / 100 * 100); // percentage as width
    const color = PROPERTY_TYPE_COLORS[type] || PROPERTY_TYPE_COLORS.other;

    segments.push(
      `<div style="width:${width}%;height:100%;background:${color};display:inline-block;"></div>`
    );
    accumulatedWidth += width;
  }

  // Fill remaining space with gray
  if (accumulatedWidth < 100) {
    segments.push(
      `<div style="width:${100 - accumulatedWidth}%;height:100%;background:#6b7280;display:inline-block;"></div>`
    );
  }

  return `<div style="width:100%;height:4px;border-radius:2px;overflow:hidden;display:flex;">${segments.join("")}</div>`;
}

/**
 * ClusterMarker - Renders a styled cluster marker
 */
export default function ClusterMarker({ count, dominantType, typeDistribution, isMixed }: ClusterMarkerProps) {
  const backgroundColor = getClusterColor(dominantType, isMixed);
  const displayCount = count >= 1000 ? `${Math.floor(count / 1000)}K+` : count.toString();

  const mixedTypeBar = isMixed && typeDistribution.size > 1
    ? generateMixedTypeBar(typeDistribution)
    : "";

  return (
    <div
      className="mapbox-marker-cluster"
      style={{
        minWidth: count >= 100 ? "40px" : count >= 50 ? "35px" : "30px",
        height: count >= 100 ? "40px" : count >= 50 ? "35px" : "30px",
        padding: "0 8px",
        background: backgroundColor,
        color: "white",
        borderRadius: "9999px",
        border: "2px solid white",
        boxShadow: "0 2px 4px rgba(0,0,0,0.3)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontWeight: 700,
        fontSize: count >= 100 ? "13px" : "12px",
        lineHeight: 1,
        cursor: "pointer",
        transition: "transform 0.2s ease, box-shadow 0.2s ease",
      }}
    >
      <span>{displayCount}</span>
      {mixedTypeBar && (
        <div
          style={{ marginTop: "2px", width: "80%" }}
          dangerouslySetInnerHTML={{ __html: mixedTypeBar }}
        />
      )}
    </div>
  );
}

/**
 * Get cluster type summary for popup
 */
export function getClusterTypeSummary(distribution: Map<string, number>): string {
  const sortedTypes = Array.from(distribution.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  return sortedTypes
    .map(([type, percentage]) => `${type}: ${percentage.toFixed(0)}%`)
    .join(" • ");
}
