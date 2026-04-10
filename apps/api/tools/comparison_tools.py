"""
Property comparison, price analysis, location analysis, and commute time tools.

Provides tools for comparing properties side-by-side, analyzing prices,
analyzing locations, and calculating commute times.
"""

import statistics
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr


class PropertyComparisonInput(BaseModel):
    """Input for property comparison tool."""

    property_ids: str = Field(
        description="Comma-separated list of property IDs to compare", min_length=1
    )


class PriceAnalysisInput(BaseModel):
    """Input for price analysis tool."""

    query: str = Field(
        description="Search query for price analysis (e.g., 'apartments in Madrid')", min_length=1
    )


class LocationAnalysisInput(BaseModel):
    """Input for location analysis tool."""

    property_id: str = Field(description="Property ID to analyze", min_length=1)


class PropertyComparisonTool(BaseTool):
    """Tool for comparing properties side-by-side."""

    name: str = "property_comparator"
    description: str = (
        "Compare multiple properties based on various criteria. "
        "Input should be a comma-separated list of property IDs (e.g., 'prop1, prop2'). "
        "Returns a detailed comparison table."
    )
    args_schema: type[PropertyComparisonInput] = PropertyComparisonInput

    _vector_store: Any = PrivateAttr()

    def __init__(self, vector_store: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._vector_store = vector_store

    def _run(self, property_ids: str) -> str:
        """
        Compare properties.

        Args:
            property_ids: Comma-separated list of property IDs
        """
        try:
            if self._vector_store is None:
                return (
                    "Property Comparison:\n"
                    "Provide a comma-separated list of property IDs to compare.\n"
                    "Comparison includes price, area, rooms, and key features."
                )

            # Parse IDs
            ids = [pid.strip() for pid in property_ids.split(",") if pid.strip()]

            if not ids:
                return "Please provide at least one property ID to compare."

            # Fetch properties
            if hasattr(self._vector_store, "get_properties_by_ids"):
                docs = self._vector_store.get_properties_by_ids(ids)
            else:
                return "Vector store does not support retrieving by IDs."

            if not docs:
                return f"No properties found for IDs: {property_ids}"

            # Build comparison
            comparison = ["Property Comparison:"]

            # Extract common fields
            fields = [
                "price",
                "price_per_sqm",
                "city",
                "rooms",
                "bathrooms",
                "area_sqm",
                "year_built",
                "property_type",
            ]

            # Header
            header = f"{'Feature':<20} | " + " | ".join(
                [f"{d.metadata.get('id', 'Unknown')[:10]:<15}" for d in docs]
            )
            comparison.append(header)
            comparison.append("-" * len(header))

            for field in fields:
                row = f"{field.replace('_', ' ').title():<20} | "
                values = []
                for doc in docs:
                    val = doc.metadata.get(field, "N/A")
                    if field == "price" and isinstance(val, (int, float)):
                        val = f"${val:,.0f}"
                    elif field == "price_per_sqm" and isinstance(val, (int, float)):
                        val = f"${val:,.0f}/m\u00b2"
                    elif field == "area_sqm" and isinstance(val, (int, float)):
                        val = f"{val} m\u00b2"
                    values.append(f"{str(val):<15}")
                row += " | ".join(values)
                comparison.append(row)

            # Add Pros/Cons placeholder or analysis
            comparison.append("\nSummary:")
            prices = [
                d.metadata.get("price", 0)
                for d in docs
                if isinstance(d.metadata.get("price"), (int, float))
            ]
            if prices:
                min_price = min(prices)
                max_price = max(prices)
                diff = max_price - min_price
                comparison.append(f"Price difference: ${diff:,.0f}")

            return "\n".join(comparison)

        except Exception as e:
            return f"Error comparing properties: {str(e)}"

    async def _arun(self, property_ids: str) -> str:
        """Async version."""
        return self._run(property_ids)


class PriceAnalysisTool(BaseTool):
    """Tool for analyzing property prices and market trends."""

    name: str = "price_analyzer"
    description: str = (
        "Analyze property prices for a given location or criteria. "
        "Input should be a search query (e.g., 'apartments in Madrid'). "
        "Returns statistical analysis of prices."
    )
    args_schema: type[PriceAnalysisInput] = PriceAnalysisInput

    _vector_store: Any = PrivateAttr()

    def __init__(self, vector_store: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._vector_store = vector_store

    def _run(self, query: str) -> str:
        """
        Analyze prices.

        Args:
            query: Search query
        """
        try:
            if self._vector_store is None:
                return (
                    f"Price Analysis for '{query}':\n"
                    "- Average: N/A\n"
                    "- Median: N/A\n"
                    "- Min: N/A\n"
                    "- Max: N/A\n"
                    "Provide a data source to compute statistics."
                )

            # Search for properties (fetch more for stats)
            results = self._vector_store.search(query, k=20)

            if not results:
                return f"No properties found for analysis: {query}"

            docs = [doc for doc, _ in results]

            # Extract prices
            prices: List[float] = []
            for d in docs:
                raw_price = d.metadata.get("price")
                if raw_price is None:
                    continue
                try:
                    prices.append(float(raw_price))
                except (TypeError, ValueError):
                    continue

            sqm_prices: List[float] = []
            for d in docs:
                raw_ppsqm = d.metadata.get("price_per_sqm")
                if raw_ppsqm is None:
                    continue
                try:
                    sqm_prices.append(float(raw_ppsqm))
                except (TypeError, ValueError):
                    continue

            if not prices:
                return "Found properties but no price data available."

            # Calculate stats
            stats_output = [f"Price Analysis for '{query}' (based on {len(prices)} listings):"]

            stats_output.append("\nTotal Prices:")
            stats_output.append(f"- Average: ${statistics.mean(prices):,.2f}")
            stats_output.append(f"- Median: ${statistics.median(prices):,.2f}")
            stats_output.append(f"- Min: ${min(prices):,.2f}")
            stats_output.append(f"- Max: ${max(prices):,.2f}")

            if sqm_prices:
                stats_output.append("\nPrice per m\u00b2:")
                stats_output.append(f"- Average: ${statistics.mean(sqm_prices):,.2f}/m\u00b2")
                stats_output.append(f"- Median: ${statistics.median(sqm_prices):,.2f}/m\u00b2")

            # Distribution by type
            types: Dict[str, int] = {}
            for d in docs:
                ptype = d.metadata.get("property_type", "Unknown")
                types[ptype] = types.get(ptype, 0) + 1

            stats_output.append("\nDistribution by Type:")
            for ptype, count in types.items():
                stats_output.append(f"- {ptype}: {count}")

            return "\n".join(stats_output)

        except Exception as e:
            return f"Error analyzing prices: {str(e)}"

    async def _arun(self, query: str) -> str:
        """Async version."""
        return self._run(query)


class LocationAnalysisTool(BaseTool):
    """Tool for analyzing property locations and proximity."""

    name: str = "location_analyzer"
    description: str = (
        "Analyze a specific property's location. "
        "Input should be a property ID. "
        "Returns location details and nearby properties info."
    )
    args_schema: type[LocationAnalysisInput] = LocationAnalysisInput

    _vector_store: Any = PrivateAttr()

    def __init__(self, vector_store: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._vector_store = vector_store

    def _run(self, property_id: str) -> str:
        """
        Analyze location.

        Args:
            property_id: Property ID
        """
        try:
            if self._vector_store is None:
                return (
                    f"Location Analysis for '{property_id}':\n"
                    "Neighborhood: N/A\n"
                    "Proximity: N/A\n"
                    "Provide a data source to compute distances and nearby listings."
                )

            # Get property
            if hasattr(self._vector_store, "get_properties_by_ids"):
                docs = self._vector_store.get_properties_by_ids([property_id])
            else:
                return "Vector store does not support retrieving by IDs."

            if not docs:
                return f"Property not found: {property_id}"

            target = docs[0]
            lat = target.metadata.get("lat")
            lon = target.metadata.get("lon")
            city = target.metadata.get("city", "Unknown")

            analysis = [f"Location Analysis for Property {property_id}:"]
            analysis.append(f"City: {city}")
            if target.metadata.get("neighborhood"):
                analysis.append(f"Neighborhood: {target.metadata.get('neighborhood')}")

            if lat and lon:
                analysis.append(f"Coordinates: {lat}, {lon}")

                # Find nearby properties (if hybrid search supports geo filtering)
                # We can't easily do a "nearby" query without a proper geo-filter constructed.
                # But we can try to search for properties in the same city.
                # Or if we had a dedicated "search_nearby" method.
                # For now, let's just return what we have.
                analysis.append("\nGeospatial data available. Use map view for nearby amenities.")
            else:
                analysis.append("Exact coordinates not available.")

            return "\n".join(analysis)

        except Exception as e:
            return f"Error analyzing location: {str(e)}"

    async def _arun(self, property_id: str) -> str:
        """Async version."""
        return self._run(property_id)


# TASK-021: Commute Time Analysis Tools


class CommuteTimeInput(BaseModel):
    """Input for commute time analysis tool."""

    property_id: str = Field(description="Property ID to analyze commute from")
    destination_lat: float = Field(description="Destination latitude", ge=-90, le=90)
    destination_lon: float = Field(description="Destination longitude", ge=-180, le=180)
    mode: str = Field(
        default="transit",
        description="Commute mode: 'driving', 'walking', 'bicycling', or 'transit'",
    )
    destination_name: Optional[str] = Field(default=None, description="Optional destination name")
    departure_time: Optional[str] = Field(
        default=None,
        description="Optional departure time as ISO string (e.g., '2024-01-15T08:30:00')",
    )


class CommuteRankingInput(BaseModel):
    """Input for commute-based property ranking tool."""

    property_ids: str = Field(description="Comma-separated list of property IDs to rank")
    destination_lat: float = Field(description="Destination latitude", ge=-90, le=90)
    destination_lon: float = Field(description="Destination longitude", ge=-180, le=180)
    mode: str = Field(
        default="transit",
        description="Commute mode: 'driving', 'walking', 'bicycling', or 'transit'",
    )
    destination_name: Optional[str] = Field(default=None, description="Optional destination name")
    departure_time: Optional[str] = Field(
        default=None,
        description="Optional departure time as ISO string (e.g., '2024-01-15T08:30:00')",
    )


class CommuteTimeAnalysisTool(BaseTool):
    """
    Tool for calculating commute time from a property to a destination.

    Uses Google Routes API to calculate accurate commute times including
    real-time traffic conditions and transit schedules.
    """

    name: str = "commute_time_analyzer"
    description: str = (
        "Calculate commute time from a property to a destination. "
        "Input: property_id, destination coordinates, mode (driving/walking/bicycling/transit). "
        "Returns: duration, distance, and route information for the commute."
    )
    args_schema: type[BaseModel] = CommuteTimeInput

    _vector_store: Any = PrivateAttr()

    def __init__(self, vector_store: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._vector_store = vector_store

    def _run(
        self,
        property_id: str,
        destination_lat: float,
        destination_lon: float,
        mode: str = "transit",
        destination_name: Optional[str] = None,
        departure_time: Optional[str] = None,
    ) -> str:
        """
        Calculate commute time from property to destination.

        Args:
            property_id: Property ID for the origin.
            destination_lat: Destination latitude.
            destination_lon: Destination longitude.
            mode: Travel mode - 'driving', 'walking', 'bicycling', or 'transit'.
            destination_name: Optional destination name for display.
            departure_time: Optional departure time for transit scheduling.

        Returns:
            Formatted string with commute time analysis.
        """
        try:
            from utils.commute_client import CommuteTimeClient

            # Get property coordinates
            if self._vector_store is None:
                return (
                    f"Commute Analysis for '{property_id}':\n"
                    "Error: Vector store not available. Cannot retrieve property coordinates."
                )

            docs = self._vector_store.get_properties_by_ids([property_id])
            if not docs:
                return f"Commute Analysis for '{property_id}':\nError: Property not found."

            md = docs[0].metadata or {}
            origin_lat = md.get("lat")
            origin_lon = md.get("lon")

            if origin_lat is None or origin_lon is None:
                return (
                    f"Commute Analysis for '{property_id}':\n"
                    "Error: Property coordinates not available."
                )

            # Parse departure time if provided
            parsed_departure_time = None
            if departure_time:
                try:
                    parsed_departure_time = datetime.fromisoformat(departure_time)
                except ValueError:
                    return (
                        "Error: Invalid departure_time format. "
                        "Use ISO format (e.g., '2024-01-15T08:30:00')."
                    )

            # Create client and calculate commute time
            client = CommuteTimeClient()

            import asyncio

            result = asyncio.run(
                client.get_commute_time(
                    property_id=property_id,
                    origin_lat=float(origin_lat),
                    origin_lon=float(origin_lon),
                    destination_lat=destination_lat,
                    destination_lon=destination_lon,
                    mode=mode,
                    destination_name=destination_name,
                    departure_time=parsed_departure_time,
                )
            )

            # Format output
            dest_display = destination_name or f"({destination_lat:.4f}, {destination_lon:.4f})"
            mode_display = mode.capitalize()

            output = [
                f"Commute Analysis for Property '{property_id}':",
                "",
                f"Destination: {dest_display}",
                f"Mode: {mode_display}",
                "",
                f"Duration: {result.duration_text}",
                f"Distance: {result.distance_text}",
            ]

            if result.arrival_time:
                output.append(f"Arrival: {result.arrival_time.strftime('%H:%M')}")

            # Add context for the commute duration
            minutes = result.duration_seconds // 60
            if minutes < 30:
                assessment = "Excellent commute time!"
            elif minutes < 45:
                assessment = "Reasonable commute time."
            elif minutes < 60:
                assessment = "Long commute - consider carefully."
            else:
                assessment = "Very long commute - may impact quality of life."

            output.append(f"\nAssessment: {assessment}")

            return "\n".join(output)

        except Exception as e:
            return (
                f"Commute Analysis for '{property_id}':\nError calculating commute time: {str(e)}"
            )

    async def _arun(self, **kwargs: Any) -> str:
        """Async version."""
        return self._run(**kwargs)


class CommuteRankingTool(BaseTool):
    """
    Tool for ranking multiple properties by commute time to a destination.

    Compares commute times from multiple properties to a common destination
    and returns a ranked list from shortest to longest commute.
    """

    name: str = "commute_ranking"
    description: str = (
        "Rank multiple properties by commute time to a destination. "
        "Input: comma-separated property_ids, destination coordinates, mode. "
        "Returns: ranked list of properties sorted by commute duration (shortest first)."
    )
    args_schema: type[BaseModel] = CommuteRankingInput

    _vector_store: Any = PrivateAttr()

    def __init__(self, vector_store: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._vector_store = vector_store

    def _run(
        self,
        property_ids: str,
        destination_lat: float,
        destination_lon: float,
        mode: str = "transit",
        destination_name: Optional[str] = None,
        departure_time: Optional[str] = None,
    ) -> str:
        """
        Rank properties by commute time to destination.

        Args:
            property_ids: Comma-separated list of property IDs.
            destination_lat: Destination latitude.
            destination_lon: Destination longitude.
            mode: Travel mode - 'driving', 'walking', 'bicycling', or 'transit'.
            destination_name: Optional destination name for display.
            departure_time: Optional departure time for transit scheduling.

        Returns:
            Formatted string with ranked property commute times.
        """
        try:
            from utils.commute_client import CommuteTimeClient

            if self._vector_store is None:
                return (
                    "Commute Ranking:\n"
                    "Error: Vector store not available. Cannot retrieve property coordinates."
                )

            # Parse property IDs
            pid_list = [pid.strip() for pid in property_ids.split(",") if pid.strip()]
            if not pid_list:
                return "Error: At least one property_id is required."

            # Get property coordinates
            docs = self._vector_store.get_properties_by_ids(pid_list)
            if not docs:
                return "Error: No properties found."

            properties_lat_lon = {}
            property_titles = {}
            for doc in docs:
                md = doc.metadata or {}
                pid = str(md.get("id", ""))
                lat = md.get("lat")
                lon = md.get("lon")
                title = md.get("title")

                if pid and lat is not None and lon is not None:
                    properties_lat_lon[pid] = (float(lat), float(lon))
                    if title:
                        property_titles[pid] = title

            if not properties_lat_lon:
                return "Error: No properties with valid coordinates found."

            # Parse departure time if provided
            parsed_departure_time = None
            if departure_time:
                try:
                    parsed_departure_time = datetime.fromisoformat(departure_time)
                except ValueError:
                    return (
                        "Error: Invalid departure_time format. "
                        "Use ISO format (e.g., '2024-01-15T08:30:00')."
                    )

            # Create client and rank properties
            client = CommuteTimeClient()

            import asyncio

            results = asyncio.run(
                client.rank_properties_by_commute(
                    property_ids=list(properties_lat_lon.keys()),
                    properties_lat_lon=properties_lat_lon,
                    destination_lat=destination_lat,
                    destination_lon=destination_lon,
                    mode=mode,
                    destination_name=destination_name,
                    departure_time=parsed_departure_time,
                )
            )

            if not results:
                return "Error: Unable to calculate commute times for any properties."

            # Format output
            dest_display = destination_name or f"({destination_lat:.4f}, {destination_lon:.4f})"
            mode_display = mode.capitalize()

            output = [
                f"Commute Ranking to {dest_display}",
                f"Mode: {mode_display}",
                "",
                f"{'Rank':<5} {'Property':<30} {'Duration':<12} {'Distance':<10}",
                f"{'-' * 5} {'-' * 30} {'-' * 12} {'-' * 10}",
            ]

            for i, result in enumerate(results, 1):
                pid = result.property_id
                title = property_titles.get(pid, pid)[:28]  # Truncate if too long
                duration = result.duration_text
                distance = result.distance_text

                output.append(f"{i:<5} {title:<30} {duration:<12} {distance:<10}")

            output.append("")
            output.append(f"Ranked {len(results)} properties by commute time.")

            # Add summary
            if results:
                fastest = results[0]
                slowest = results[-1]
                output.append("")
                output.append(f"Fastest: {fastest.duration_text}")
                output.append(f"Slowest: {slowest.duration_text}")

            return "\n".join(output)

        except Exception as e:
            return f"Commute Ranking:\nError: {str(e)}"

    async def _arun(self, **kwargs: Any) -> str:
        """Async version."""
        return self._run(**kwargs)
