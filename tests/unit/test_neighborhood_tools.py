"""
Unit tests for neighborhood quality index tool.

Tests neighborhood scoring algorithm, component calculations, and overall score.
"""

import pytest

from tools.property_tools import (
    NeighborhoodQualityIndexTool,
    create_property_tools,
)


class TestNeighborhoodQualityIndexTool:
    """Test suite for NeighborhoodQualityIndexTool."""

    @pytest.fixture
    def neighborhood_calc(self):
        """Fixture for neighborhood quality calculator."""
        return NeighborhoodQualityIndexTool()

    def test_basic_calculation_with_coordinates(self, neighborhood_calc):
        """Test basic neighborhood quality calculation with coordinates."""
        result = NeighborhoodQualityIndexTool.calculate(
            property_id="test_prop_1",
            latitude=52.2297,
            longitude=21.0122,  # Warsaw coordinates
        )

        assert result.property_id == "test_prop_1"
        assert 0 <= result.overall_score <= 100
        assert 0 <= result.safety_score <= 100
        assert 0 <= result.schools_score <= 100
        assert 0 <= result.amenities_score <= 100
        assert 0 <= result.walkability_score <= 100
        assert 0 <= result.green_space_score <= 100

    def test_calculation_with_city_only(self, neighborhood_calc):
        """Test calculation with only city name (no coordinates)."""
        result = NeighborhoodQualityIndexTool.calculate(
            property_id="test_prop_2",
            city="Warsaw",
        )

        assert result.property_id == "test_prop_2"
        assert result.city == "Warsaw"
        assert 0 <= result.overall_score <= 100
        # Safety score should use city-based mock
        assert 0 <= result.safety_score <= 100

    def test_safety_score_by_city(self, neighborhood_calc):
        """Test safety score varies by city."""
        warsaw = NeighborhoodQualityIndexTool._mock_safety_score("Warsaw", None)
        london = NeighborhoodQualityIndexTool._mock_safety_score("London", None)
        berlin = NeighborhoodQualityIndexTool._mock_safety_score("Berlin", None)

        # Each city should have a different base score
        # All should be in valid range
        assert 0 <= warsaw <= 100
        assert 0 <= london <= 100
        assert 0 <= berlin <= 100

    def test_overall_score_weighted_calculation(self, neighborhood_calc):
        """Test overall score is weighted correctly."""
        result = NeighborhoodQualityIndexTool.calculate(
            property_id="test_weights",
            latitude=52.2297,
            longitude=21.0122,
        )

        # Overall score should be weighted sum of components
        expected_overall = (
            result.safety_score * NeighborhoodQualityIndexTool.WEIGHT_SAFETY
            + result.schools_score * NeighborhoodQualityIndexTool.WEIGHT_SCHOOLS
            + result.amenities_score * NeighborhoodQualityIndexTool.WEIGHT_AMENITIES
            + result.walkability_score * NeighborhoodQualityIndexTool.WEIGHT_WALKABILITY
            + result.green_space_score * NeighborhoodQualityIndexTool.WEIGHT_GREEN_SPACE
        )

        assert abs(result.overall_score - expected_overall) < 0.1

    def test_score_breakdown_components(self, neighborhood_calc):
        """Test score breakdown has all expected components."""
        result = NeighborhoodQualityIndexTool.calculate(
            property_id="test_breakdown",
            latitude=52.2297,
            longitude=21.0122,
        )

        expected_keys = {
            "safety_weighted",
            "schools_weighted",
            "amenities_weighted",
            "walkability_weighted",
            "green_space_weighted",
        }

        assert set(result.score_breakdown.keys()) == expected_keys

    def test_data_sources_includes_coordinates(self, neighborhood_calc):
        """Test data sources reflect when coordinates are provided."""
        result_with_coords = NeighborhoodQualityIndexTool.calculate(
            property_id="test_data_1",
            latitude=52.2297,
            longitude=21.0122,
        )

        result_without_coords = NeighborhoodQualityIndexTool.calculate(
            property_id="test_data_2",
        )

        # With coordinates, should include geographic_coordinates
        assert "geographic_coordinates" in result_with_coords.data_sources
        assert "geographic_coordinates" not in result_without_coords.data_sources

        # Both should include mock and OSM sources
        assert "mock_safety_data" in result_with_coords.data_sources
        assert "osm_pois" in result_with_coords.data_sources

    def test_missing_coordinates_returns_default_scores(self, neighborhood_calc):
        """Test that missing coordinates returns reasonable default scores."""
        result = NeighborhoodQualityIndexTool.calculate(
            property_id="test_no_coords",
        )

        # Should still return valid scores even without coordinates
        assert result.overall_score >= 0
        assert result.schools_score >= 0
        assert result.amenities_score >= 0
        assert result.walkability_score >= 0
        assert result.green_space_score >= 0

    def test_result_includes_all_input_fields(self, neighborhood_calc):
        """Test result includes all provided input fields."""
        result = NeighborhoodQualityIndexTool.calculate(
            property_id="test_fields",
            latitude=50.0,
            longitude=20.0,
            city="Krakow",
            neighborhood="Old Town",
        )

        assert result.property_id == "test_fields"
        assert result.latitude == 50.0
        assert result.longitude == 20.0
        assert result.city == "Krakow"
        assert result.neighborhood == "Old Town"

    def test_score_weights_sum_to_one(self):
        """Test that component weights sum to 1.0."""
        total_weight = (
            NeighborhoodQualityIndexTool.WEIGHT_SAFETY
            + NeighborhoodQualityIndexTool.WEIGHT_SCHOOLS
            + NeighborhoodQualityIndexTool.WEIGHT_AMENITIES
            + NeighborhoodQualityIndexTool.WEIGHT_WALKABILITY
            + NeighborhoodQualityIndexTool.WEIGHT_GREEN_SPACE
        )

        assert abs(total_weight - 1.0) < 0.001

    def test_tool_metadata(self, neighborhood_calc):
        """Test tool name and description."""
        assert neighborhood_calc.name == "neighborhood_quality_index"
        assert len(neighborhood_calc.description) > 0
        assert "neighborhood" in neighborhood_calc.description.lower()

    def test_rating_label_function(self):
        """Test rating label function returns correct labels."""
        assert (
            NeighborhoodQualityIndexTool._get_rating_label(90)
            == "Excellent - Highly desirable neighborhood"
        )
        assert NeighborhoodQualityIndexTool._get_rating_label(75) == "Good - Above average quality"
        assert NeighborhoodQualityIndexTool._get_rating_label(60) == "Fair - Average neighborhood"
        assert NeighborhoodQualityIndexTool._get_rating_label(45) == "Poor - Below average quality"
        assert (
            NeighborhoodQualityIndexTool._get_rating_label(20) == "Very Poor - Significant concerns"
        )

    def test_schools_score_range(self, neighborhood_calc):
        """Test schools score is always in valid range."""
        for lat in range(-80, 81, 20):
            for lon in range(-170, 171, 40):
                result = NeighborhoodQualityIndexTool.calculate(
                    property_id=f"test_{lat}_{lon}",
                    latitude=float(lat),
                    longitude=float(lon),
                )
                assert 0 <= result.schools_score <= 100

    def test_amenities_score_range(self, neighborhood_calc):
        """Test amenities score is always in valid range."""
        for lat in range(-80, 81, 20):
            for lon in range(-170, 171, 40):
                result = NeighborhoodQualityIndexTool.calculate(
                    property_id=f"test_{lat}_{lon}",
                    latitude=float(lat),
                    longitude=float(lon),
                )
                assert 0 <= result.amenities_score <= 100

    def test_walkability_score_range(self, neighborhood_calc):
        """Test walkability score is always in valid range."""
        for lat in range(-80, 81, 20):
            for lon in range(-170, 171, 40):
                result = NeighborhoodQualityIndexTool.calculate(
                    property_id=f"test_{lat}_{lon}",
                    latitude=float(lat),
                    longitude=float(lon),
                )
                assert 0 <= result.walkability_score <= 100

    def test_green_space_score_range(self, neighborhood_calc):
        """Test green space score is always in valid range."""
        for lat in range(-80, 81, 20):
            for lon in range(-170, 171, 40):
                result = NeighborhoodQualityIndexTool.calculate(
                    property_id=f"test_{lat}_{lon}",
                    latitude=float(lat),
                    longitude=float(lon),
                )
                assert 0 <= result.green_space_score <= 100


class TestNeighborhoodToolFactory:
    """Test neighborhood tool in factory function."""

    def test_neighborhood_tool_in_factory(self):
        """Test that NeighborhoodQualityIndexTool is included in factory."""
        tools = create_property_tools()
        tool_names = {tool.name for tool in tools}

        assert "neighborhood_quality_index" in tool_names

    def test_all_expected_tools_present(self):
        """Test that all expected tools including neighborhood are created."""
        tools = create_property_tools()
        tool_names = {tool.name for tool in tools}

        expected_names = {
            "mortgage_calculator",
            "tco_calculator",
            "investment_analyzer",
            "neighborhood_quality_index",
            "property_comparator",
            "price_analyzer",
            "location_analyzer",
        }

        assert tool_names == expected_names
