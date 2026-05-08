"""
Unit tests for search router validation functions.

Tests cover:
- Polygon validation (_validate_polygon)
- Explanation conversion (_convert_explanation_to_response)
- Input sanitization integration
"""

from api.routers.search import (
    POLYGON_MAX_AREA_SQKM,
    POLYGON_MAX_VERTICES,
    _convert_explanation_to_response,
    _validate_polygon,
)


class TestPolygonValidation:
    """Test polygon validation logic."""

    def test_validate_polygon_empty_polygon(self):
        """Test that empty polygon returns error."""
        result = _validate_polygon([])
        assert result == "Polygon coordinates are empty"

    def test_validate_polygon_empty_outer_ring(self):
        """Test that polygon with empty outer ring returns error."""
        result = _validate_polygon([[]])
        assert result == "Polygon must have at least 3 vertices"

    def test_validate_polygon_two_vertices(self):
        """Test that polygon with only 2 vertices fails."""
        polygon = [[[50.0, 19.0], [50.1, 19.1]]]
        result = _validate_polygon(polygon)
        assert result == "Polygon must have at least 3 vertices"

    def test_validate_polygon_too_many_vertices(self):
        """Test that polygon exceeding max vertices fails."""
        # Create polygon with 101 vertices
        polygon = [[[50.0 + i * 0.001, 19.0 + i * 0.001] for i in range(101)]]
        result = _validate_polygon(polygon)
        assert "too many vertices" in result.lower()
        assert str(POLYGON_MAX_VERTICES) in result

    def test_validate_polygon_valid_triangle(self):
        """Test that valid triangle polygon passes."""
        polygon = [
            [
                [50.0, 19.9],
                [50.1, 19.9],
                [50.05, 20.0],
                [50.0, 19.9],  # Close the loop
            ]
        ]
        result = _validate_polygon(polygon)
        assert result is None

    def test_validate_polygon_valid_rectangle(self):
        """Test that valid rectangle polygon passes."""
        polygon = [
            [
                [50.0, 19.9],
                [50.1, 19.9],
                [50.1, 20.0],
                [50.0, 20.0],
                [50.0, 19.9],  # Close the loop
            ]
        ]
        result = _validate_polygon(polygon)
        assert result is None

    def test_validate_polygon_large_area(self):
        """Test that polygon exceeding max area fails."""
        # Create a polygon that's too large (simple large box)
        # Using coordinates that span a large area
        polygon = [[[0.0, 0.0], [100.0, 0.0], [100.0, 100.0], [0.0, 100.0], [0.0, 0.0]]]
        result = _validate_polygon(polygon)
        assert result is not None
        assert "area too large" in result.lower()


class TestExplanationConversion:
    """Test ranking explanation conversion to response model."""

    def test_convert_explanation_to_response_basic(self):
        """Test conversion of basic explanation without components."""

        # Create a mock dataclass explanation
        class MockComponent:
            def __init__(self, name, value, weight, contribution, description):
                self.name = name
                self.value = value
                self.weight = weight
                self.contribution = contribution
                self.description = description

        class MockDataExplanation:
            def __init__(self):
                self.property_id = "test-prop-1"
                self.final_score = 0.85
                self.rank = 1
                self.semantic_score = 0.9
                self.keyword_score = 0.8
                self.hybrid_score = 0.85
                self.exact_match_boost = 0.0
                self.metadata_match_boost = 0.0
                self.quality_boost = 0.0
                self.personalization_boost = 0.0
                self.diversity_penalty = 1.0
                self.components = [
                    MockComponent("semantic", 0.9, 0.5, 0.45, "Semantic similarity"),
                    MockComponent("price", 1000, 0.3, 300, "Price match"),
                ]

        explanation = MockDataExplanation()
        result = _convert_explanation_to_response(explanation)

        assert result.property_id == "test-prop-1"
        assert result.final_score == 0.85
        assert result.rank == 1
        assert result.semantic_score == 0.9
        assert len(result.components) == 2
        assert result.components[0].name == "semantic"
        assert result.components[0].value == 0.9

    def test_convert_explanation_to_response_empty_components(self):
        """Test conversion with no components."""

        class MockDataExplanation:
            def __init__(self):
                self.property_id = "test-prop-2"
                self.final_score = 0.75
                self.rank = 2
                self.semantic_score = 0.8
                self.keyword_score = 0.7
                self.hybrid_score = 0.75
                self.exact_match_boost = 0.0
                self.metadata_match_boost = 0.0
                self.quality_boost = 0.0
                self.personalization_boost = 0.0
                self.diversity_penalty = 1.0
                self.components = []

        explanation = MockDataExplanation()
        result = _convert_explanation_to_response(explanation)

        assert result.property_id == "test-prop-2"
        assert result.final_score == 0.75
        assert len(result.components) == 0

    def test_convert_explanation_to_response_all_boosts(self):
        """Test conversion with all boost/penalty fields."""

        class MockComponent:
            def __init__(self, name, value, weight, contribution, description):
                self.name = name
                self.value = value
                self.weight = weight
                self.contribution = contribution
                self.description = description

        class MockDataExplanation:
            def __init__(self):
                self.property_id = "test-prop-3"
                self.final_score = 0.92
                self.rank = 1
                self.semantic_score = 0.9
                self.keyword_score = 0.8
                self.hybrid_score = 0.85
                self.exact_match_boost = 0.05
                self.metadata_match_boost = 0.03
                self.quality_boost = 0.02
                self.personalization_boost = 0.01
                self.diversity_penalty = 0.98
                self.components = [MockComponent("test", 1.0, 1.0, 1.0, "Test")]

        explanation = MockDataExplanation()
        result = _convert_explanation_to_response(explanation)

        assert result.exact_match_boost == 0.05
        assert result.metadata_match_boost == 0.03
        assert result.quality_boost == 0.02
        assert result.personalization_boost == 0.01
        assert result.diversity_penalty == 0.98


class TestSearchConstants:
    """Test search router constants."""

    def test_polygon_max_vertices(self):
        """Test that max vertices constant is reasonable."""
        assert POLYGON_MAX_VERTICES == 100
        assert POLYGON_MAX_VERTICES > 3  # Minimum for polygon

    def test_polygon_max_area(self):
        """Test that max area constant is reasonable."""
        assert POLYGON_MAX_AREA_SQKM == 10000  # ~100km radius
        assert POLYGON_MAX_AREA_SQKM > 0

    def test_constants_are_positive_integers(self):
        """Test that constants are positive."""
        assert isinstance(POLYGON_MAX_VERTICES, int)
        assert isinstance(POLYGON_MAX_AREA_SQKM, int)
        assert POLYGON_MAX_VERTICES > 0
        assert POLYGON_MAX_AREA_SQKM > 0
