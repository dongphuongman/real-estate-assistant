"""
Unit tests for RankingExplainer.

"""

import pytest
from langchain_core.documents import Document

from services.ranking_config_service import RankingWeights
from services.ranking_explainer import (
    RankingExplainer,
    create_ranking_explainer,
)


@pytest.fixture
def explainer() -> RankingExplainer:
    """Create a RankingExplainer instance."""
    return RankingExplainer()


@pytest.fixture
def sample_document() -> Document:
    """Create a sample property document for testing."""
    return Document(
        page_content="Beautiful 3-bedroom apartment in Warsaw city center. "
        "Modern kitchen, spacious living area, and great location.",
        metadata={
            "id": "prop-123",
            "title": "Modern Apartment Warsaw Center",
            "city": "Warsaw",
            "price": 850000,
            "rooms": 3,
            "area_sqm": 75,
            "property_type": "apartment",
            "has_images": True,
            "lat": 52.2297,
            "lon": 21.0122,
        },
    )


class TestRankingExplainerInit:
    """Test RankingExplainer initialization."""

    def test_default_weights(self, explainer: RankingExplainer):
        assert explainer.weights is not None
        weights = explainer.weights
        assert weights.alpha == 0.7  # Default alpha
        assert weights.boost_exact_match == 1.5
        assert weights.boost_metadata_match == 1.3
        assert weights.boost_quality_signals == 1.2
        assert weights.diversity_penalty == 0.9
        assert weights.personalization_enabled is False  # Disabled by default
        assert weights.personalization_weight == 0.2
        assert weights.weight_recency == 0.1
        assert weights.weight_price_match == 0.15
        assert weights.weight_location == 0.1
        assert weights.config_id is None
        assert weights.config_name is None

    def test_custom_weights(self):
        """Test RankingExplainer with custom weights."""
        custom_weights = RankingWeights(
            alpha=0.8,
            boost_exact_match=2.0,
            boost_metadata_match=1.8,
            boost_quality_signals=1.5,
            diversity_penalty=0.85,
            personalization_enabled=False,
            personalization_weight=0.0,
            weight_recency=0.15,
            weight_price_match=0.2,
            weight_location=0.15,
        )
        explainer = RankingExplainer(ranking_weights=custom_weights)
        assert explainer.weights.alpha == 0.8
        assert explainer.weights.boost_exact_match == 2.0
        assert explainer.weights.personalization_enabled is False
        assert explainer.weights.personalization_weight == 0.0

    def test_factory_function(self):
        """Test the create_ranking_explainer factory function."""
        explainer = create_ranking_explainer()
        assert isinstance(explainer, RankingExplainer)
        assert explainer.weights is not None

        custom_weights = RankingWeights(alpha=0.5)
        explainer2 = create_ranking_explainer(custom_weights)
        assert explainer2.weights.alpha == 0.5


class TestCalculateExactMatchScore:
    """Test calculate_exact_match_score method."""

    def test_full_match(self, explainer: RankingExplainer, sample_document: Document):
        score = explainer.calculate_exact_match_score(
            query="3 bedroom apartment Warsaw",
            document=sample_document,
        )
        assert 0 < score <= 1
        assert score > 0.5  # Should have high match

    def test_partial_match(self, explainer: RankingExplainer, sample_document: Document):
        score = explainer.calculate_exact_match_score(
            query="cheap house Krakow",
            document=sample_document,
        )
        # "Krakow" doesn't appear in document, "house" doesn't match "apartment"
        # Score may be 0 if no terms match
        assert 0 <= score <= 1

    def test_no_match(self, explainer: RankingExplainer, sample_document: Document):
        score = explainer.calculate_exact_match_score(
            query="luxury villa Gdansk pool",
            document=sample_document,
        )
        assert score == 0.0

    def test_stop_words_filtered(self, explainer: RankingExplainer, sample_document: Document):
        score = explainer.calculate_exact_match_score(
            query="show me the a beautiful property",
            document=sample_document,
        )
        # Stop words should be filtered out, so we focus on content words
        assert 0 < score <= 1
        # Should match "beautiful" and "apartment" or "Warsaw"


class TestCalculateMetadataMatchScore:
    """Test calculate_metadata_match_score method."""

    def test_city_match(self, explainer: RankingExplainer, sample_document: Document):
        score = explainer.calculate_metadata_match_score(
            document=sample_document,
            user_criteria={"city": "Warsaw"},
        )
        assert score == 1.0  # Full match

    def test_property_type_match(self, explainer: RankingExplainer, sample_document: Document):
        score = explainer.calculate_metadata_match_score(
            document=sample_document,
            user_criteria={"property_type": "apartment"},
        )
        assert score == 1.0

    def test_rooms_match(self, explainer: RankingExplainer, sample_document: Document):
        score = explainer.calculate_metadata_match_score(
            document=sample_document,
            user_criteria={"rooms": 3},
        )
        assert score == 1.0

    def test_price_range_match(self, explainer: RankingExplainer, sample_document: Document):
        # Price is 850000, within range
        score = explainer.calculate_metadata_match_score(
            document=sample_document,
            user_criteria={"min_price": 800000, "max_price": 900000},
        )
        assert score == 1.0
        # Price outside range
        score2 = explainer.calculate_metadata_match_score(
            document=sample_document,
            user_criteria={"min_price": 900000, "max_price": 1000000},
        )
        assert score2 == 0.0

    def test_no_user_criteria(self, explainer: RankingExplainer, sample_document: Document):
        score = explainer.calculate_metadata_match_score(
            document=sample_document,
            user_criteria=None,
        )
        assert score == 0.0

    def test_multiple_criteria(self, explainer: RankingExplainer, sample_document: Document):
        score = explainer.calculate_metadata_match_score(
            document=sample_document,
            user_criteria={
                "city": "Warsaw",
                "property_type": "apartment",
                "rooms": 3,
            },
        )
        assert score == 1.0  # All match
        score2 = explainer.calculate_metadata_match_score(
            document=sample_document,
            user_criteria={
                "city": "Warsaw",
                "property_type": "apartment",
                "rooms": 5,  # Wrong rooms
            },
        )
        assert 0 < score2 < 1.0
        assert score2 < 1.0


class TestCalculateQualityScore:
    """Test calculate_quality_score method."""

    def test_quality_full_score(self, explainer: RankingExplainer, sample_document: Document):
        score = explainer.calculate_quality_score(sample_document)
        assert 0 < score <= 1
        # Should have reasonable quality (price, area, images, location, description)
        # Score is normalized by max_score, so may not be as high as expected
        assert score > 0.5

    def test_quality_missing_fields(self, explainer: RankingExplainer):
        """Test quality score with missing fields."""
        doc = Document(
            page_content="Short description",
            metadata={"id": "prop-456"},
        )
        score = explainer.calculate_quality_score(doc)
        assert 0 < score < 1
        assert score < 0.5  # Should have lower quality


class TestExplainRanking:
    """Test explain_ranking method."""

    def test_basic_explanation(self, explainer: RankingExplainer, sample_document: Document):
        explanation = explainer.explain_ranking(
            document=sample_document,
            rank=1,
            final_score=0.85,
            query="3 bedroom Warsaw",
            semantic_score=0.8,
            keyword_score=0.9,
        )
        assert explanation.property_id == "prop-123"
        assert explanation.rank == 1
        assert explanation.final_score == 0.85
        assert explanation.semantic_score == 0.8
        assert explanation.keyword_score == 0.9
        assert len(explanation.components) > 0
        # Check hybrid score calculation
        assert explanation.hybrid_score > 0

    def test_explanation_with_boosts(self, explainer: RankingExplainer, sample_document: Document):
        explanation = explainer.explain_ranking(
            document=sample_document,
            rank=1,
            final_score=0.95,
            query="3 bedroom Warsaw apartment",
            semantic_score=0.9,
            keyword_score=0.85,
            exact_match_boost=0.8,
            metadata_match_boost=0.7,
            quality_boost=0.6,
            personalization_boost=0.3,
        )
        assert explanation.exact_match_boost == 0.8
        assert explanation.metadata_match_boost == 0.7
        assert explanation.quality_boost == 0.6
        assert explanation.personalization_boost == 0.3
        # Check components list
        component_names = [c.name for c in explanation.components]
        assert "semantic_similarity" in component_names
        assert "keyword_match" in component_names
        assert "exact_match" in component_names
        assert "metadata_match" in component_names
        assert "quality_signals" in component_names
        assert "personalization" in component_names

    def test_explanation_with_diversity_penalty(
        self, explainer: RankingExplainer, sample_document: Document
    ):
        explanation = explainer.explain_ranking(
            document=sample_document,
            rank=1,
            final_score=0.75,
            query="3 bedroom Warsaw",
            semantic_score=0.8,
            keyword_score=0.7,
            diversity_penalty=0.9,  # 10% penalty
        )
        assert explanation.diversity_penalty == 0.9
        assert "diversity_penalty" in [c.name for c in explanation.components]

    def test_explanation_no_semantic_score(
        self, explainer: RankingExplainer, sample_document: Document
    ):
        """Test explanation when semantic score is not provided."""
        explanation = explainer.explain_ranking(
            document=sample_document,
            rank=2,
            final_score=0.6,
            query="Warsaw apartment",
            semantic_score=None,
            keyword_score=None,
        )
        assert explanation.semantic_score == 0.6  # Falls back to final_score
        assert explanation.keyword_score == 0.0

    def test_explanation_to_dict(self, explainer: RankingExplainer, sample_document: Document):
        """Test to_dict conversion."""
        explanation = explainer.explain_ranking(
            document=sample_document,
            rank=1,
            final_score=0.85,
            query="3 bedroom Warsaw",
            semantic_score=0.8,
            keyword_score=0.9,
        )
        result = explanation.to_dict()
        assert isinstance(result, dict)
        assert result["property_id"] == "prop-123"
        assert result["rank"] == 1
        assert result["final_score"] == 0.85
        assert "components" in result
        assert isinstance(result["components"], list)


class TestExplainResults:
    """Test explain_results method."""

    def test_explain_multiple_results(self, explainer: RankingExplainer, sample_document: Document):
        doc2 = Document(
            page_content="Luxury penthouse in Sopot",
            metadata={
                "id": "prop-456",
                "title": "Luxury Penthouse Sopot",
                "city": "Sopot",
                "price": 1200000,
                "rooms": 4,
            },
        )
        results = [
            (sample_document, 0.85),
            (doc2, 0.75),
        ]
        explanations = explainer.explain_results(
            results=results,
            query="apartment Warsaw",
            user_criteria={"city": "Warsaw"},
        )
        assert len(explanations) == 2
        assert explanations[0].property_id == "prop-123"
        assert explanations[1].property_id == "prop-456"
        assert explanations[0].rank == 1
        assert explanations[1].rank == 2
        # First result should have higher score
        assert explanations[0].final_score > explanations[1].final_score

    def test_explain_results_with_scores(
        self, explainer: RankingExplainer, sample_document: Document
    ):
        """Test explain_results with pre-computed semantic/keyword scores."""
        doc2 = Document(
            page_content="Budget studio in Krakow",
            metadata={"id": "prop-789", "title": "Studio Krakow", "city": "Krakow"},
        )
        results = [
            (sample_document, 0.85),
            (doc2, 0.75),
        ]
        explanations = explainer.explain_results(
            results=results,
            query="Warsaw apartment",
            semantic_scores=[0.9, 0.8],
            keyword_scores=[0.7, 0.6],
        )
        assert len(explanations) == 2
        assert explanations[0].semantic_score == 0.9
        assert explanations[0].keyword_score == 0.7
        assert explanations[1].semantic_score == 0.8
        assert explanations[1].keyword_score == 0.6
