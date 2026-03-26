"""
Comparable property selection algorithm for CMA reports.

This module implements a multi-factor scoring system to identify and rank
comparable properties based on similarity to a subject property.

Scoring dimensions (total 100 points):
- Location: 25 points (geo-distance or city/district match)
- Property Type: 20 points (exact match vs compatible)
- Size: 15 points (area within percentage threshold)
- Rooms: 15 points (room count similarity)
- Recency: 15 points (listing age)
- Amenities: 10 points (amenity overlap)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

from analytics.market_insights import MarketInsights
from data.schemas import Property, PropertyCollection, PropertyType

logger = logging.getLogger(__name__)


@dataclass
class ComparableScore:
    """Scoring breakdown for a comparable property."""

    property_id: str
    total_score: float  # 0-100
    location_score: float  # 0-25
    type_score: float  # 0-20
    size_score: float  # 0-15
    rooms_score: float  # 0-15
    recency_score: float  # 0-15
    amenities_score: float  # 0-10
    distance_km: float
    price_per_sqm: float
    price: float
    score_breakdown: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        self.score_breakdown = {
            "location": self.location_score,
            "type": self.type_score,
            "size": self.size_score,
            "rooms": self.rooms_score,
            "recency": self.recency_score,
            "amenities": self.amenities_score,
        }


# Compatible property type mappings
COMPATIBLE_TYPES = {
    PropertyType.APARTMENT: [PropertyType.STUDIO, PropertyType.LOFT],
    PropertyType.STUDIO: [PropertyType.APARTMENT, PropertyType.LOFT],
    PropertyType.LOFT: [PropertyType.APARTMENT, PropertyType.STUDIO],
    PropertyType.HOUSE: [PropertyType.TOWNHOUSE],
    PropertyType.TOWNHOUSE: [PropertyType.HOUSE],
    PropertyType.OTHER: [],
}


class ComparableSelector:
    """
    Selects and scores comparable properties for CMA reports.

    Uses a multi-factor scoring algorithm to identify the most similar
    properties to a subject property for market analysis.
    """

    def __init__(self, properties: PropertyCollection):
        """
        Initialize the selector with a property collection.

        Args:
            properties: Collection of candidate properties to search
        """
        self.properties = properties
        self.market_insights = MarketInsights(properties)

    def find_comparables(
        self,
        subject: Property,
        max_distance_km: float = 5.0,
        min_score: float = 50.0,
        max_results: int = 10,
        exclude_subject: bool = True,
        require_same_listing_type: bool = True,
    ) -> List[ComparableScore]:
        """
        Find and score comparable properties.

        Args:
            subject: The subject property to find comparables for
            max_distance_km: Maximum distance in kilometers (if coords available)
            min_score: Minimum similarity score (0-100) to include
            max_results: Maximum number of comparables to return
            exclude_subject: Whether to exclude the subject property from results
            require_same_listing_type: Whether to require same listing type (rent/sale)

        Returns:
            List of ComparableScore objects sorted by score descending
        """
        candidates = self._filter_candidates(
            subject,
            max_distance_km,
            require_same_listing_type,
        )

        scores = []
        for prop in candidates:
            # Skip subject property
            if exclude_subject and prop.id == subject.id:
                continue

            score = self._score_property(subject, prop)
            if score.total_score >= min_score:
                scores.append(score)

        # Sort by total score descending
        scores.sort(key=lambda x: x.total_score, reverse=True)

        return scores[:max_results]

    def _filter_candidates(
        self,
        subject: Property,
        max_distance_km: float,
        require_same_listing_type: bool,
    ) -> List[Property]:
        """
        Pre-filter candidates to reduce scoring workload.

        Args:
            subject: Subject property
            max_distance_km: Maximum distance
            require_same_listing_type: Whether to require same listing type

        Returns:
            List of candidate properties
        """
        candidates = []

        for prop in self.properties.properties:
            # Same city is required
            if prop.city.lower() != subject.city.lower():
                continue

            # Same listing type if required
            if require_same_listing_type:
                if prop.listing_type != subject.listing_type:
                    continue

            # Price range filter (within 50% of subject price)
            if subject.price and prop.price:
                price_diff = abs(prop.price - subject.price) / subject.price
                if price_diff > 0.5:
                    continue

            candidates.append(prop)

        # If we have coordinates, further filter by geo distance
        if subject.latitude and subject.longitude:
            geo_filtered = []
            for prop in candidates:
                if prop.latitude and prop.longitude:
                    dist = self._calculate_distance_km(
                        subject.latitude, subject.longitude, prop.latitude, prop.longitude
                    )
                    if dist <= max_distance_km:
                        geo_filtered.append(prop)
            # If geo filtering yields enough results, use it
            if len(geo_filtered) >= 3:
                candidates = geo_filtered

        return candidates

    def _score_property(self, subject: Property, candidate: Property) -> ComparableScore:
        """
        Score a candidate property against the subject.

        Args:
            subject: Subject property
            candidate: Candidate property to score

        Returns:
            ComparableScore with full breakdown
        """
        # Calculate individual scores
        location_score = self._score_location(subject, candidate)
        type_score = self._score_type(subject, candidate)
        size_score = self._score_size(subject, candidate)
        rooms_score = self._score_rooms(subject, candidate)
        recency_score = self._score_recency(candidate)
        amenities_score = self._score_amenities(subject, candidate)

        # Calculate distance if coordinates available
        distance_km = 0.0
        if subject.latitude and subject.longitude and candidate.latitude and candidate.longitude:
            distance_km = self._calculate_distance_km(
                subject.latitude, subject.longitude, candidate.latitude, candidate.longitude
            )

        # Calculate price per sqm
        price_per_sqm = 0.0
        if candidate.area_sqm and candidate.area_sqm > 0 and candidate.price:
            price_per_sqm = candidate.price / candidate.area_sqm

        total_score = (
            location_score + type_score + size_score + rooms_score + recency_score + amenities_score
        )

        return ComparableScore(
            property_id=candidate.id or "",
            total_score=round(total_score, 1),
            location_score=round(location_score, 1),
            type_score=round(type_score, 1),
            size_score=round(size_score, 1),
            rooms_score=round(rooms_score, 1),
            recency_score=round(recency_score, 1),
            amenities_score=round(amenities_score, 1),
            distance_km=round(distance_km, 2),
            price_per_sqm=round(price_per_sqm, 2),
            price=candidate.price or 0.0,
        )

    def _score_location(self, subject: Property, candidate: Property) -> float:
        """
        Score location similarity (0-25 points).

        Uses geo-distance when coordinates available, otherwise falls back
        to district/neighborhood matching.
        """
        # If we have coordinates, use Haversine distance
        if subject.latitude and subject.longitude and candidate.latitude and candidate.longitude:
            dist_km = self._calculate_distance_km(
                subject.latitude, subject.longitude, candidate.latitude, candidate.longitude
            )
            if dist_km < 0.5:
                return 25.0
            elif dist_km < 1.0:
                return 20.0
            elif dist_km < 2.0:
                return 15.0
            elif dist_km < 3.0:
                return 10.0
            elif dist_km < 5.0:
                return 5.0
            else:
                return 0.0

        # Fallback: district/neighborhood matching
        score = 10.0  # Base score for same city (already filtered)

        if subject.district and candidate.district:
            if subject.district.lower() == candidate.district.lower():
                score += 10.0
                # Bonus for same neighborhood
                if subject.neighborhood and candidate.neighborhood:
                    if subject.neighborhood.lower() == candidate.neighborhood.lower():
                        score += 5.0

        return min(score, 25.0)

    def _score_type(self, subject: Property, candidate: Property) -> float:
        """
        Score property type match (0-20 points).

        Exact match = 20 pts
        Compatible type = 10 pts
        Different = 0 pts
        """
        subject_type = subject.property_type
        candidate_type = candidate.property_type

        if subject_type == candidate_type:
            return 20.0

        # Check compatibility
        compatible = COMPATIBLE_TYPES.get(subject_type, [])
        if candidate_type in compatible:
            return 10.0

        return 0.0

    def _score_size(self, subject: Property, candidate: Property) -> float:
        """
        Score size similarity (0-15 points).

        Within 10% = 15 pts
        Within 20% = 10 pts
        Within 30% = 5 pts
        Beyond 30% = 0 pts
        """
        if not subject.area_sqm or not candidate.area_sqm:
            return 5.0  # Neutral score if size unknown

        if subject.area_sqm <= 0:
            return 5.0

        diff_percent = abs(candidate.area_sqm - subject.area_sqm) / subject.area_sqm

        if diff_percent <= 0.10:
            return 15.0
        elif diff_percent <= 0.20:
            return 10.0
        elif diff_percent <= 0.30:
            return 5.0
        else:
            return 0.0

    def _score_rooms(self, subject: Property, candidate: Property) -> float:
        """
        Score room count similarity (0-15 points).

        Exact match = 15 pts
        +/- 1 room = 10 pts
        +/- 2 rooms = 5 pts
        Beyond = 0 pts
        """
        if subject.rooms is None or candidate.rooms is None:
            return 5.0  # Neutral score if rooms unknown

        diff = abs(candidate.rooms - subject.rooms)

        if diff == 0:
            return 15.0
        elif diff <= 1:
            return 10.0
        elif diff <= 2:
            return 5.0
        else:
            return 0.0

    def _score_recency(self, candidate: Property) -> float:
        """
        Score listing recency (0-15 points).

        Last 30 days = 15 pts
        60 days = 10 pts
        90 days = 5 pts
        Beyond 90 days = 2 pts
        """
        now = datetime.now()

        # Try scraped_at first, then last_updated
        listing_date = candidate.scraped_at or candidate.last_updated

        if not listing_date:
            return 5.0  # Neutral score if date unknown

        # Handle both datetime and date objects
        if hasattr(listing_date, "tzinfo") and listing_date.tzinfo:
            # Convert to naive datetime for comparison
            listing_date = listing_date.replace(tzinfo=None)

        age_days = (now - listing_date).days

        if age_days <= 30:
            return 15.0
        elif age_days <= 60:
            return 10.0
        elif age_days <= 90:
            return 5.0
        else:
            return 2.0

    def _score_amenities(self, subject: Property, candidate: Property) -> float:
        """
        Score amenity overlap (0-10 points).

        Calculates the percentage of matching amenities.
        """
        amenity_fields = [
            "has_parking",
            "has_garden",
            "has_pool",
            "has_garage",
            "has_bike_room",
            "is_furnished",
            "pets_allowed",
            "has_balcony",
            "has_elevator",
        ]

        matches = 0
        total = len(amenity_fields)

        for amenity_field in amenity_fields:
            subject_val = getattr(subject, amenity_field, False)
            candidate_val = getattr(candidate, amenity_field, False)

            if subject_val == candidate_val:
                matches += 1

        # Convert to 0-10 scale
        score = (matches / total) * 10.0
        return round(score, 1)

    @staticmethod
    def _calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great-circle distance between two points using Haversine formula.

        Args:
            lat1, lon1: First point coordinates (degrees)
            lat2, lon2: Second point coordinates (degrees)

        Returns:
            Distance in kilometers
        """
        import math

        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        # Earth's radius in km
        earth_radius_km = 6371.0

        return earth_radius_km * c


def find_best_comparables(
    properties: PropertyCollection,
    subject: Property,
    max_results: int = 6,
    min_score: float = 50.0,
) -> List[ComparableScore]:
    """
    Convenience function to find best comparables.

    Args:
        properties: Property collection to search
        subject: Subject property
        max_results: Maximum results to return
        min_score: Minimum score threshold

    Returns:
        List of ComparableScore objects
    """
    selector = ComparableSelector(properties)
    return selector.find_comparables(
        subject=subject,
        max_results=max_results,
        min_score=min_score,
    )
