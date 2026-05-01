"""
Recommendation engine for personalized property suggestions.

This module provides intelligent recommendations based on:
- User preferences and search history
- Property features and value
- Similarity to viewed properties
- Market insights
"""

from typing import Any, Dict, List, Optional, Tuple

from langchain_core.documents import Document

from data.schemas import UserPreferences


class PropertyRecommendationEngine:
    """
    Recommendation engine for properties.

    Uses multiple signals:
    1. Explicit preferences (budget, location, amenities)
    2. Implicit preferences (viewed/favorited properties)
    3. Value score (price vs features)
    4. Popularity signals
    """

    def __init__(self) -> None:
        """Initialize recommendation engine."""
        self.weight_explicit = 0.4
        self.weight_value = 0.3
        self.weight_implicit = 0.2
        self.weight_popularity = 0.1

    def recommend(
        self,
        documents: List[Document],
        user_preferences: Optional[UserPreferences] = None,
        viewed_properties: Optional[List[str]] = None,
        favorited_properties: Optional[List[str]] = None,
        k: int = 5,
    ) -> List[Tuple[Document, float, Dict[str, Any]]]:
        """
        Generate personalized recommendations.

        Args:
            documents: Candidate properties
            user_preferences: User preferences
            viewed_properties: List of viewed property IDs
            favorited_properties: List of favorited property IDs
            k: Number of recommendations

        Returns:
            List of (document, score, explanation) tuples
        """
        if not documents:
            return []

        scored_docs = []

        for doc in documents:
            # Calculate recommendation score
            score, explanation = self._score_property(
                doc, user_preferences, documents, viewed_properties, favorited_properties
            )

            scored_docs.append((doc, score, explanation))

        # Sort by score
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # Return top k
        return scored_docs[:k]

    def _score_property(
        self,
        doc: Document,
        user_preferences: Optional[UserPreferences],
        documents: List[Document],
        viewed_properties: Optional[List[str]] = None,
        favorited_properties: Optional[List[str]] = None,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Score a property for recommendation.

        Returns:
            (score, explanation dict)
        """
        metadata: Dict[str, Any] = dict(doc.metadata)
        explanation: Dict[str, Any] = {}

        # 1. Explicit preference score
        explicit_score = 0.0
        if user_preferences:
            explicit_score = self._calculate_explicit_score(metadata, user_preferences)
            explanation["preference_match"] = f"{explicit_score:.2f}"

        # 2. Value score
        value_score = self._calculate_value_score(metadata)
        explanation["value_score"] = f"{value_score:.2f}"

        # 3. Implicit preference score (similarity to viewed/favorited)
        implicit_score = 0.0
        if viewed_properties or favorited_properties:
            implicit_score = self._calculate_implicit_score(
                metadata, documents, viewed_properties, favorited_properties
            )
            explanation["similar_to_favorites"] = implicit_score > 0.7

        # 4. Popularity score (placeholder - would use actual data)
        popularity_score = 0.5  # Neutral
        explanation["trending"] = False

        # Combine scores
        final_score = (
            self.weight_explicit * explicit_score
            + self.weight_value * value_score
            + self.weight_implicit * implicit_score
            + self.weight_popularity * popularity_score
        )

        # Add quality boost
        has_quality_amenities = sum(
            1
            for key in ["has_parking", "has_garden", "has_elevator", "has_balcony"]
            if bool(metadata.get(key, False))
        )
        if has_quality_amenities >= 3:
            final_score *= 1.1
            explanation["premium_amenities"] = True

        # Explanation summary
        explanation["recommendation_score"] = f"{final_score:.2f}"
        explanation["why_recommended"] = self._generate_recommendation_reason(
            explicit_score, value_score, implicit_score, metadata
        )

        return final_score, explanation

    def _calculate_explicit_score(
        self, metadata: Dict[str, Any], preferences: UserPreferences
    ) -> float:
        """Score based on explicit user preferences."""
        score = 0.0
        checks = 0

        # Budget match
        min_budget, max_budget = preferences.budget_range
        property_price_raw = metadata.get("price", 0)
        property_price = (
            float(property_price_raw) if isinstance(property_price_raw, (int, float)) else 0.0
        )

        if min_budget <= property_price <= max_budget:
            score += 1.0
            checks += 1
        elif property_price < max_budget * 1.1:  # Within 10% of budget
            score += 0.7
            checks += 1
        else:
            checks += 1

        # City match
        if preferences.preferred_cities:
            checks += 1
            city = metadata.get("city")
            if isinstance(city, str) and any(
                city.lower() == pref.lower() for pref in preferences.preferred_cities
            ):
                score += 1.0

        # Rooms match
        if preferences.preferred_rooms:
            checks += 1
            rooms = metadata.get("rooms")
            if isinstance(rooms, (int, float)) and float(rooms) in preferences.preferred_rooms:
                score += 1.0

        # Must-have amenities
        if preferences.must_have_amenities:
            for amenity in preferences.must_have_amenities:
                checks += 1
                if metadata.get(amenity, False):
                    score += 1.0

        # Neighborhood match
        if preferences.preferred_neighborhoods:
            checks += 1
            neighborhood = metadata.get("neighborhood")
            if isinstance(neighborhood, str) and any(
                neighborhood.lower() == pref.lower() for pref in preferences.preferred_neighborhoods
            ):
                score += 1.0

        # Normalize
        return score / checks if checks > 0 else 0.5

    def _calculate_value_score(self, metadata: Dict[str, Any]) -> float:
        """
        Score based on value for money.

        Considers:
        - Price relative to area
        - Amenities for the price
        - Location desirability
        """
        score = 0.5  # Neutral start

        # Price per sqm analysis
        price_per_sqm_raw = metadata.get("price_per_sqm")
        if isinstance(price_per_sqm_raw, (int, float)):
            price_per_sqm = float(price_per_sqm_raw)

            # Excellent value: under $20/sqm
            if price_per_sqm < 20:
                score += 0.3
            # Good value: $20-25/sqm
            elif price_per_sqm < 25:
                score += 0.2
            # Fair value: $25-30/sqm
            elif price_per_sqm < 30:
                score += 0.1
            # Poor value: $30+/sqm
            else:
                score -= 0.1

        # Amenity value
        amenity_count = sum(
            1
            for key in [
                "has_parking",
                "has_garden",
                "has_pool",
                "has_garage",
                "has_bike_room",
                "has_elevator",
                "has_balcony",
            ]
            if bool(metadata.get(key, False))
        )

        # Normalize amenities (0-7 range to 0-0.3)
        score += (amenity_count / 7) * 0.3

        # Cap score at 1.0
        return float(min(score, 1.0))

    def _extract_reference_properties(
        self,
        documents: List[Document],
        property_ids: List[str],
    ) -> List[Dict[str, Any]]:
        """Extract metadata dicts from documents whose IDs match property_ids."""
        id_set = {str(pid) for pid in property_ids}
        return [
            dict(doc.metadata) for doc in documents if str(doc.metadata.get("id", "")) in id_set
        ]

    # Amenity fields used for Jaccard similarity
    _AMENITY_KEYS = [
        "has_parking",
        "has_garden",
        "has_pool",
        "has_garage",
        "has_bike_room",
        "has_elevator",
        "has_balcony",
    ]

    def _calculate_feature_similarity(
        self,
        candidate: Dict[str, Any],
        reference: Dict[str, Any],
    ) -> float:
        """Weighted feature match between candidate and a single reference property."""
        # City (0.25) — exact match
        city_score = (
            1.0
            if str(candidate.get("city", "")).lower() == str(reference.get("city", "")).lower()
            else 0.0
        )

        # Rooms (0.20) — distance-based
        c_rooms = candidate.get("rooms")
        r_rooms = reference.get("rooms")
        if isinstance(c_rooms, (int, float)) and isinstance(r_rooms, (int, float)):
            max_range = 5.0
            rooms_score = max(0.0, 1.0 - abs(float(c_rooms) - float(r_rooms)) / max_range)
        else:
            rooms_score = 0.5

        # Price (0.20) — ratio-based
        c_price = candidate.get("price")
        r_price = reference.get("price")
        if (
            isinstance(c_price, (int, float))
            and isinstance(r_price, (int, float))
            and float(r_price) > 0
        ):
            price_score = max(0.0, 1.0 - abs(float(c_price) - float(r_price)) / float(r_price))
        else:
            price_score = 0.5

        # Property type (0.15) — exact match
        type_score = (
            1.0
            if str(candidate.get("property_type", "")) == str(reference.get("property_type", ""))
            else 0.0
        )

        # Amenities (0.20) — Jaccard
        c_amenities = {k for k in self._AMENITY_KEYS if bool(candidate.get(k, False))}
        r_amenities = {k for k in self._AMENITY_KEYS if bool(reference.get(k, False))}
        union = c_amenities | r_amenities
        amenity_score = len(c_amenities & r_amenities) / len(union) if union else 1.0

        return (
            0.25 * city_score
            + 0.20 * rooms_score
            + 0.20 * price_score
            + 0.15 * type_score
            + 0.20 * amenity_score
        )

    def _calculate_implicit_score(
        self,
        metadata: Dict[str, Any],
        documents: List[Document],
        viewed_properties: Optional[List[str]],
        favorited_properties: Optional[List[str]],
    ) -> float:
        """
        Score based on similarity to viewed/favorited properties.

        Uses weighted feature matching against reference properties
        extracted from the candidate document pool by ID.
        """
        viewed_ids = viewed_properties or []
        favorited_ids = favorited_properties or []

        if not viewed_ids and not favorited_ids:
            return 0.5

        # Extract reference properties from candidate pool
        viewed_refs = self._extract_reference_properties(documents, viewed_ids)
        favorited_refs = self._extract_reference_properties(documents, favorited_ids)

        if not viewed_refs and not favorited_refs:
            return 0.5

        # Compute weighted similarity scores (favorites 2x weight)
        weighted_sum = 0.0
        total_weight = 0

        for ref in viewed_refs:
            weighted_sum += self._calculate_feature_similarity(metadata, ref)
            total_weight += 1

        for ref in favorited_refs:
            weighted_sum += 2.0 * self._calculate_feature_similarity(metadata, ref)
            total_weight += 2

        return weighted_sum / total_weight if total_weight > 0 else 0.5

    def _generate_recommendation_reason(
        self,
        explicit_score: float,
        value_score: float,
        implicit_score: float,
        metadata: Dict[str, Any],
    ) -> str:
        """Generate human-readable recommendation reason."""
        reasons = []

        if explicit_score > 0.8:
            reasons.append("matches your preferences perfectly")
        elif explicit_score > 0.6:
            reasons.append("matches most of your preferences")

        if value_score > 0.8:
            reasons.append("excellent value for money")
        elif value_score > 0.6:
            reasons.append("good value for the price")

        if implicit_score > 0.7:
            reasons.append("similar to properties you liked")

        # Feature highlights
        highlights = []
        if metadata.get("has_parking"):
            highlights.append("parking")
        if metadata.get("has_garden"):
            highlights.append("garden")
        if metadata.get("has_pool"):
            highlights.append("pool")

        if highlights:
            reasons.append(f"features: {', '.join(highlights)}")

        if not reasons:
            reasons.append("good match for your search")

        return "; ".join(reasons).capitalize()


def create_recommendation_engine() -> PropertyRecommendationEngine:
    """
    Factory function to create recommendation engine.

    Returns:
        PropertyRecommendationEngine instance
    """
    return PropertyRecommendationEngine()
