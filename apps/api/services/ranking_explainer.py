"""
Service for explaining search result rankings.

This service provides transparency into why properties are ranked
the way they are, helping users understand the relevance scoring.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from langchain_core.documents import Document

from services.ranking_config_service import RankingWeights

logger = logging.getLogger(__name__)


@dataclass
class ScoreComponent:
    """A single component of the final ranking score."""

    name: str
    value: float  # Raw value
    weight: float  # Applied weight/boost
    contribution: float  # value * weight
    description: str  # Human-readable explanation


@dataclass
class RankingExplanation:
    """Complete ranking explanation for a single property."""

    property_id: str
    final_score: float
    rank: int

    # Score breakdown
    semantic_score: float
    keyword_score: float
    hybrid_score: float

    # Boost components
    exact_match_boost: float
    metadata_match_boost: float
    quality_boost: float
    personalization_boost: float

    # Penalty components
    diversity_penalty: float

    # All components as list
    components: list[ScoreComponent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "property_id": self.property_id,
            "final_score": round(self.final_score, 4),
            "rank": self.rank,
            "semantic_score": round(self.semantic_score, 4),
            "keyword_score": round(self.keyword_score, 4),
            "hybrid_score": round(self.hybrid_score, 4),
            "exact_match_boost": round(self.exact_match_boost, 4),
            "metadata_match_boost": round(self.metadata_match_boost, 4),
            "quality_boost": round(self.quality_boost, 4),
            "personalization_boost": round(self.personalization_boost, 4),
            "diversity_penalty": round(self.diversity_penalty, 4),
            "components": [
                {
                    "name": c.name,
                    "value": round(c.value, 4),
                    "weight": round(c.weight, 4),
                    "contribution": round(c.contribution, 4),
                    "description": c.description,
                }
                for c in self.components
            ],
        }


class RankingExplainer:
    """
    Service for generating ranking explanations.

    This class breaks down the ranking score into its components
    and provides human-readable explanations.
    """

    def __init__(self, ranking_weights: Optional[RankingWeights] = None):
        """
        Initialize the explainer.

        Args:
            ranking_weights: RankingWeights configuration for accurate explanations.
        """
        self.weights = ranking_weights or RankingWeights.default()

    def explain_ranking(
        self,
        document: Document,
        rank: int,
        final_score: float,
        query: str,
        semantic_score: Optional[float] = None,
        keyword_score: Optional[float] = None,
        exact_match_boost: float = 0.0,
        metadata_match_boost: float = 0.0,
        quality_boost: float = 0.0,
        personalization_boost: float = 0.0,
        diversity_penalty: float = 1.0,
    ) -> RankingExplanation:
        """
        Generate a complete ranking explanation for a property.

        Args:
            document: The property document.
            rank: Final rank position (1-indexed).
            final_score: Final calculated score.
            query: Original search query.
            semantic_score: Vector similarity score (0-1).
            keyword_score: BM25/keyword score (0-1).
            exact_match_boost: Boost factor for exact matches.
            metadata_match_boost: Boost factor for metadata matches.
            quality_boost: Boost factor for quality signals.
            personalization_boost: Boost from personalization.
            diversity_penalty: Penalty factor for diversity (1.0 = no penalty).

        Returns:
            RankingExplanation with complete breakdown.
        """
        property_id = str(document.metadata.get("id", "unknown"))
        components: list[ScoreComponent] = []

        # Calculate hybrid score if not provided
        if semantic_score is not None and keyword_score is not None:
            hybrid_score = (
                self.weights.alpha * semantic_score + (1 - self.weights.alpha) * keyword_score
            )
        else:
            hybrid_score = final_score
            semantic_score = hybrid_score
            keyword_score = 0.0

        # Semantic similarity component
        components.append(
            ScoreComponent(
                name="semantic_similarity",
                value=semantic_score or 0.0,
                weight=self.weights.alpha,
                contribution=(semantic_score or 0.0) * self.weights.alpha,
                description=f"Vector similarity score weighted at {self.weights.alpha:.0%}",
            )
        )

        # Keyword match component
        components.append(
            ScoreComponent(
                name="keyword_match",
                value=keyword_score or 0.0,
                weight=1 - self.weights.alpha,
                contribution=(keyword_score or 0.0) * (1 - self.weights.alpha),
                description=f"Keyword match (BM25) weighted at {(1 - self.weights.alpha):.0%}",
            )
        )

        # Exact match boost
        if exact_match_boost > 0:
            components.append(
                ScoreComponent(
                    name="exact_match",
                    value=exact_match_boost,
                    weight=self.weights.boost_exact_match,
                    contribution=exact_match_boost * self.weights.boost_exact_match,
                    description="Boost for exact keyword matches in title/description",
                )
            )

        # Metadata match boost
        if metadata_match_boost > 0:
            components.append(
                ScoreComponent(
                    name="metadata_match",
                    value=metadata_match_boost,
                    weight=self.weights.boost_metadata_match,
                    contribution=metadata_match_boost * self.weights.boost_metadata_match,
                    description="Boost for matching user criteria (city, rooms, etc.)",
                )
            )

        # Quality boost
        if quality_boost > 0:
            components.append(
                ScoreComponent(
                    name="quality_signals",
                    value=quality_boost,
                    weight=self.weights.boost_quality_signals,
                    contribution=quality_boost * self.weights.boost_quality_signals,
                    description="Boost for data completeness (price, area, images)",
                )
            )

        # Personalization boost
        if personalization_boost > 0:
            components.append(
                ScoreComponent(
                    name="personalization",
                    value=personalization_boost,
                    weight=self.weights.personalization_weight
                    if self.weights.personalization_enabled
                    else 0.0,
                    contribution=personalization_boost
                    * (
                        self.weights.personalization_weight
                        if self.weights.personalization_enabled
                        else 0.0
                    ),
                    description="Boost based on your viewing history and preferences",
                )
            )

        # Diversity penalty
        if diversity_penalty < 1.0:
            components.append(
                ScoreComponent(
                    name="diversity_penalty",
                    value=1.0 - diversity_penalty,
                    weight=1.0,
                    contribution=-(1.0 - diversity_penalty) * hybrid_score,
                    description="Small penalty to show diverse results (different cities/prices)",
                )
            )

        return RankingExplanation(
            property_id=property_id,
            final_score=final_score,
            rank=rank,
            semantic_score=semantic_score or 0.0,
            keyword_score=keyword_score or 0.0,
            hybrid_score=hybrid_score,
            exact_match_boost=exact_match_boost,
            metadata_match_boost=metadata_match_boost,
            quality_boost=quality_boost,
            personalization_boost=personalization_boost,
            diversity_penalty=diversity_penalty,
            components=components,
        )

    def calculate_exact_match_score(self, query: str, document: Document) -> float:
        """
        Calculate exact match score between query and document.

        Args:
            query: Search query.
            document: Property document.

        Returns:
            Match score (0-1).
        """
        text = (document.page_content + " " + document.metadata.get("title", "")).lower()

        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "show",
            "find",
            "me",
            "i",
            "want",
            "need",
            "looking",
        }

        query_terms = [t for t in query.lower().split() if len(t) > 2 and t not in stop_words]

        if not query_terms:
            return 0.0

        matches = sum(1 for term in query_terms if term in text)
        return matches / len(query_terms)

    def calculate_metadata_match_score(
        self,
        document: Document,
        user_criteria: Optional[dict[str, Any]] = None,
    ) -> float:
        """
        Calculate metadata match score.

        Args:
            document: Property document.
            user_criteria: User's search criteria.

        Returns:
            Match score (0-1).
        """
        if not user_criteria:
            return 0.0

        metadata = document.metadata
        total_criteria = 0
        matches = 0

        # City match
        if "city" in user_criteria and user_criteria["city"]:
            total_criteria += 1
            if metadata.get("city", "").lower() == user_criteria["city"].lower():
                matches += 1

        # Property type match
        if "property_type" in user_criteria and user_criteria["property_type"]:
            total_criteria += 1
            if metadata.get("property_type", "").lower() == user_criteria["property_type"].lower():
                matches += 1

        # Rooms match
        if "rooms" in user_criteria and user_criteria["rooms"]:
            total_criteria += 1
            if metadata.get("rooms") == user_criteria["rooms"]:
                matches += 1

        # Price range match
        if "min_price" in user_criteria or "max_price" in user_criteria:
            total_criteria += 1
            price = metadata.get("price")
            if price:
                min_ok = (
                    user_criteria.get("min_price") is None or price >= user_criteria["min_price"]
                )
                max_ok = (
                    user_criteria.get("max_price") is None or price <= user_criteria["max_price"]
                )
                if min_ok and max_ok:
                    matches += 1

        return matches / total_criteria if total_criteria > 0 else 0.0

    def calculate_quality_score(self, document: Document) -> float:
        """
        Calculate data quality/completeness score.

        Args:
            document: Property document.

        Returns:
            Quality score (0-1).
        """
        score = 0.0
        max_score = 0.0
        metadata = document.metadata

        # Bonus for having price
        max_score += 0.2
        if metadata.get("price"):
            score += 0.2

        # Bonus for having area
        max_score += 0.2
        if metadata.get("area_sqm"):
            score += 0.2

        # Bonus for having images
        max_score += 0.1
        if metadata.get("has_images", True):
            score += 0.1

        # Bonus for detailed description
        max_score += 0.2
        if len(document.page_content) > 200:
            score += 0.2

        # Bonus for location data
        max_score += 0.1
        if metadata.get("lat") and metadata.get("lon"):
            score += 0.1

        # Bonus for additional metadata
        max_score += 0.2
        extra_fields = [
            "has_parking",
            "has_garden",
            "floor",
            "building_type",
            "construction_year",
        ]
        extra_count = sum(1 for f in extra_fields if metadata.get(f) is not None)
        score += min(0.2, extra_count * 0.05)

        return score / max_score if max_score > 0 else 0.0

    def explain_results(
        self,
        results: list[tuple[Document, float]],
        query: str,
        user_criteria: Optional[dict[str, Any]] = None,
        semantic_scores: Optional[list[float]] = None,
        keyword_scores: Optional[list[float]] = None,
    ) -> list[RankingExplanation]:
        """
        Generate explanations for all results.

        Args:
            results: List of (document, score) tuples.
            query: Original search query.
            user_criteria: User's search criteria.
            semantic_scores: Optional list of semantic scores.
            keyword_scores: Optional list of keyword scores.

        Returns:
            List of RankingExplanation objects.
        """
        explanations = []

        for rank, (doc, score) in enumerate(results, 1):
            idx = rank - 1

            # Get individual scores if available
            sem_score = (
                semantic_scores[idx] if semantic_scores and idx < len(semantic_scores) else None
            )
            kw_score = keyword_scores[idx] if keyword_scores and idx < len(keyword_scores) else None

            # Calculate boost factors
            exact_match = self.calculate_exact_match_score(query, doc)
            metadata_match = self.calculate_metadata_match_score(doc, user_criteria)
            quality = self.calculate_quality_score(doc)

            explanation = self.explain_ranking(
                document=doc,
                rank=rank,
                final_score=score,
                query=query,
                semantic_score=sem_score,
                keyword_score=kw_score,
                exact_match_boost=exact_match,
                metadata_match_boost=metadata_match,
                quality_boost=quality,
            )

            explanations.append(explanation)

        return explanations


# Factory function
def create_ranking_explainer(
    ranking_weights: Optional[RankingWeights] = None,
) -> RankingExplainer:
    """
    Create a RankingExplainer instance.

    Args:
        ranking_weights: Optional RankingWeights configuration.

    Returns:
        Configured RankingExplainer.
    """
    return RankingExplainer(ranking_weights=ranking_weights)
