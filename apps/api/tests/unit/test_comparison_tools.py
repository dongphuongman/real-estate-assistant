"""
Unit tests for tools/comparison_tools.py.

Covers PropertyComparisonTool, PriceAnalysisTool, LocationAnalysisTool,
CommuteTimeAnalysisTool, and CommuteRankingTool with mocked vector stores,
exercising all code paths including vector-store-backed logic, edge cases,
and error handling.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document
from pydantic_core import ValidationError as PydanticValidationError

from tools.comparison_tools import (
    CommuteRankingTool,
    CommuteTimeAnalysisTool,
    LocationAnalysisTool,
    PriceAnalysisTool,
    PropertyComparisonTool,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_doc(metadata: dict, content: str = "Test property") -> Document:
    """Create a Document with given metadata."""
    return Document(page_content=content, metadata=metadata)


def _property_docs() -> list[Document]:
    """Return a standard set of property documents for testing."""
    return [
        _make_doc(
            {
                "id": "prop1",
                "price": 500000,
                "price_per_sqm": 5000,
                "city": "Krakow",
                "rooms": 3,
                "bathrooms": 2,
                "area_sqm": 100,
                "year_built": 2015,
                "property_type": "apartment",
                "lat": 50.0647,
                "lon": 19.9450,
                "neighborhood": "Kazimierz",
            }
        ),
        _make_doc(
            {
                "id": "prop2",
                "price": 350000,
                "price_per_sqm": 7000,
                "city": "Warsaw",
                "rooms": 2,
                "bathrooms": 1,
                "area_sqm": 50,
                "year_built": 2020,
                "property_type": "apartment",
                "lat": 52.2297,
                "lon": 21.0122,
            }
        ),
        _make_doc(
            {
                "id": "prop3",
                "price": 200000,
                "price_per_sqm": 4000,
                "city": "Gdansk",
                "rooms": 4,
                "bathrooms": 2,
                "area_sqm": 120,
                "year_built": 2010,
                "property_type": "house",
                "lat": 54.3520,
                "lon": 18.6466,
                "neighborhood": "Old Town",
            }
        ),
    ]


def _mock_vector_store_with_get_by_ids(docs_map: dict[str, Document] | None = None):
    """Create a mock vector store that has get_properties_by_ids."""
    store = MagicMock()
    default_docs = {d.metadata["id"]: d for d in _property_docs()}
    docs_map = docs_map or default_docs

    def get_by_ids(ids):
        return [docs_map[id_] for id_ in ids if id_ in docs_map]

    store.get_properties_by_ids = MagicMock(side_effect=get_by_ids)
    return store


# ===========================================================================
# PropertyComparisonTool
# ===========================================================================


class TestPropertyComparisonTool:
    """Tests for PropertyComparisonTool with vector store."""

    def test_no_vector_store_returns_guidance(self):
        tool = PropertyComparisonTool(vector_store=None)
        result = tool._run("prop1,prop2")
        assert "Property Comparison" in result
        assert "IDs" in result

    def test_vector_store_without_get_by_ids(self):
        store = MagicMock(spec=[])  # no get_properties_by_ids attribute
        tool = PropertyComparisonTool(vector_store=store)
        result = tool._run("prop1")
        assert "does not support" in result

    def test_empty_property_ids_string(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = PropertyComparisonTool(vector_store=store)
        result = tool._run("   ,  ,  ")
        assert "at least one" in result.lower()

    def test_no_properties_found(self):
        store = _mock_vector_store_with_get_by_ids({})
        tool = PropertyComparisonTool(vector_store=store)
        result = tool._run("nonexistent1,nonexistent2")
        assert "No properties found" in result

    def test_single_property_comparison(self):
        docs = {d.metadata["id"]: d for d in _property_docs()}
        store = _mock_vector_store_with_get_by_ids({"prop1": docs["prop1"]})
        tool = PropertyComparisonTool(vector_store=store)
        result = tool._run("prop1")
        assert "Property Comparison" in result
        assert "Krakow" in result
        assert "$500,000" in result

    def test_multiple_property_comparison(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = PropertyComparisonTool(vector_store=store)
        result = tool._run("prop1, prop2")
        assert "Property Comparison" in result
        assert "Price difference" in result
        assert "$150,000" in result  # 500000 - 350000

    def test_comparison_table_has_all_fields(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = PropertyComparisonTool(vector_store=store)
        result = tool._run("prop1, prop2")
        # All 8 fields should appear in the output
        for field_label in [
            "Price",
            "Price Per Sqm",
            "City",
            "Rooms",
            "Bathrooms",
            "Area Sqm",
            "Year Built",
            "Property Type",
        ]:
            assert field_label in result, f"Missing field: {field_label}"

    def test_price_formatting_with_dollar_sign(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = PropertyComparisonTool(vector_store=store)
        result = tool._run("prop1")
        assert "$500,000" in result

    def test_price_per_sqm_formatting(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = PropertyComparisonTool(vector_store=store)
        result = tool._run("prop1")
        assert "$5,000/m" in result  # price_per_sqm=5000

    def test_area_sqm_formatting(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = PropertyComparisonTool(vector_store=store)
        result = tool._run("prop1")
        assert "100 m" in result

    def test_na_values_for_missing_fields(self):
        doc = _make_doc({"id": "bare_prop"})  # no price, rooms, etc.
        store = _mock_vector_store_with_get_by_ids({"bare_prop": doc})
        tool = PropertyComparisonTool(vector_store=store)
        result = tool._run("bare_prop")
        assert "N/A" in result

    def test_exception_handling(self):
        store = MagicMock()
        store.get_properties_by_ids.side_effect = RuntimeError("DB down")
        tool = PropertyComparisonTool(vector_store=store)
        result = tool._run("prop1")
        assert "Error comparing properties" in result

    def test_summary_with_three_properties(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = PropertyComparisonTool(vector_store=store)
        result = tool._run("prop1, prop2, prop3")
        assert "Price difference: $300,000" in result  # 500k - 200k

    def test_no_prices_in_metadata_no_summary_diff(self):
        docs = [
            _make_doc({"id": "np1", "rooms": 2}),
            _make_doc({"id": "np2", "rooms": 3}),
        ]
        docs_map = {d.metadata["id"]: d for d in docs}
        store = _mock_vector_store_with_get_by_ids(docs_map)
        tool = PropertyComparisonTool(vector_store=store)
        result = tool._run("np1, np2")
        assert "Property Comparison" in result
        # No price difference line since no valid prices
        assert "Price difference" not in result

    @pytest.mark.asyncio
    async def test_arun_delegates_to_run(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = PropertyComparisonTool(vector_store=store)
        sync_result = tool._run("prop1")
        async_result = await tool._arun("prop1")
        assert sync_result == async_result


# ===========================================================================
# PriceAnalysisTool
# ===========================================================================


class TestPriceAnalysisTool:
    """Tests for PriceAnalysisTool with vector store."""

    def test_no_vector_store_returns_guidance(self):
        tool = PriceAnalysisTool(vector_store=None)
        result = tool._run("Krakow apartments")
        assert "Price Analysis" in result
        assert "N/A" in result

    def test_search_returns_no_results(self):
        store = MagicMock()
        store.search.return_value = []
        tool = PriceAnalysisTool(vector_store=store)
        result = tool._run("nonexistent city")
        assert "No properties found" in result

    def test_search_returns_docs_without_prices(self):
        doc = _make_doc({"id": "noprice", "property_type": "studio"})
        store = MagicMock()
        store.search.return_value = [(doc, 0.9)]
        tool = PriceAnalysisTool(vector_store=store)
        result = tool._run("query")
        assert "no price data" in result.lower()

    def test_basic_price_statistics(self):
        docs = [
            _make_doc({"id": "p1", "price": 100000, "property_type": "apartment"}),
            _make_doc({"id": "p2", "price": 200000, "property_type": "apartment"}),
            _make_doc({"id": "p3", "price": 300000, "property_type": "house"}),
        ]
        store = MagicMock()
        store.search.return_value = [(d, 1.0) for d in docs]
        tool = PriceAnalysisTool(vector_store=store)
        result = tool._run("test query")
        assert "Price Analysis" in result
        assert "3 listings" in result
        assert "Average" in result
        assert "Median" in result
        assert "Min" in result
        assert "Max" in result

    def test_price_statistics_values(self):
        docs = [
            _make_doc({"id": "p1", "price": 100000, "property_type": "apartment"}),
            _make_doc({"id": "p2", "price": 200000, "property_type": "apartment"}),
            _make_doc({"id": "p3", "price": 300000, "property_type": "house"}),
        ]
        store = MagicMock()
        store.search.return_value = [(d, 1.0) for d in docs]
        tool = PriceAnalysisTool(vector_store=store)
        result = tool._run("test query")
        # Average = 200000, Median = 200000
        assert "$200,000.00" in result

    def test_price_per_sqm_statistics(self):
        docs = [
            _make_doc(
                {"id": "p1", "price": 100000, "price_per_sqm": 5000, "property_type": "apartment"}
            ),
            _make_doc(
                {"id": "p2", "price": 200000, "price_per_sqm": 6000, "property_type": "apartment"}
            ),
        ]
        store = MagicMock()
        store.search.return_value = [(d, 1.0) for d in docs]
        tool = PriceAnalysisTool(vector_store=store)
        result = tool._run("test query")
        assert "Price per m" in result
        assert "$5,500.00/m" in result  # mean of 5000 and 6000

    def test_distribution_by_type(self):
        docs = [
            _make_doc({"id": "p1", "price": 100, "property_type": "apartment"}),
            _make_doc({"id": "p2", "price": 200, "property_type": "apartment"}),
            _make_doc({"id": "p3", "price": 300, "property_type": "house"}),
        ]
        store = MagicMock()
        store.search.return_value = [(d, 1.0) for d in docs]
        tool = PriceAnalysisTool(vector_store=store)
        result = tool._run("test query")
        assert "Distribution by Type" in result
        assert "apartment: 2" in result
        assert "house: 1" in result

    def test_price_as_non_numeric_string_skipped(self):
        docs = [
            _make_doc({"id": "p1", "price": "not_a_number", "property_type": "apartment"}),
            _make_doc({"id": "p2", "price": 200000, "property_type": "apartment"}),
        ]
        store = MagicMock()
        store.search.return_value = [(d, 1.0) for d in docs]
        tool = PriceAnalysisTool(vector_store=store)
        result = tool._run("test query")
        assert "1 listings" in result
        assert "$200,000.00" in result

    def test_price_per_sqm_as_non_numeric_skipped(self):
        docs = [
            _make_doc(
                {"id": "p1", "price": 100000, "price_per_sqm": "bad", "property_type": "apartment"}
            ),
            _make_doc(
                {"id": "p2", "price": 200000, "price_per_sqm": 5000, "property_type": "apartment"}
            ),
        ]
        store = MagicMock()
        store.search.return_value = [(d, 1.0) for d in docs]
        tool = PriceAnalysisTool(vector_store=store)
        result = tool._run("test query")
        assert "Price per m" in result
        assert "$5,000.00/m" in result

    def test_missing_property_type_defaults_to_unknown(self):
        docs = [
            _make_doc({"id": "p1", "price": 100}),  # no property_type
        ]
        store = MagicMock()
        store.search.return_value = [(d, 1.0) for d in docs]
        tool = PriceAnalysisTool(vector_store=store)
        result = tool._run("test query")
        assert "Unknown: 1" in result

    def test_exception_handling(self):
        store = MagicMock()
        store.search.side_effect = RuntimeError("search failed")
        tool = PriceAnalysisTool(vector_store=store)
        result = tool._run("query")
        assert "Error analyzing prices" in result

    def test_search_called_with_k_20(self):
        store = MagicMock()
        store.search.return_value = []
        tool = PriceAnalysisTool(vector_store=store)
        tool._run("my query")
        store.search.assert_called_once_with("my query", k=20)

    def test_none_price_skipped(self):
        docs = [
            _make_doc({"id": "p1", "price": None, "property_type": "apartment"}),
            _make_doc({"id": "p2", "price": 150000, "property_type": "apartment"}),
        ]
        store = MagicMock()
        store.search.return_value = [(d, 1.0) for d in docs]
        tool = PriceAnalysisTool(vector_store=store)
        result = tool._run("test query")
        assert "1 listings" in result
        assert "$150,000.00" in result

    def test_none_price_per_sqm_skipped(self):
        docs = [
            _make_doc(
                {"id": "p1", "price": 100000, "price_per_sqm": None, "property_type": "apartment"}
            ),
            _make_doc(
                {"id": "p2", "price": 200000, "price_per_sqm": 5000, "property_type": "apartment"}
            ),
        ]
        store = MagicMock()
        store.search.return_value = [(d, 1.0) for d in docs]
        tool = PriceAnalysisTool(vector_store=store)
        result = tool._run("test query")
        assert "$5,000.00/m" in result

    def test_no_sqm_prices_section_omitted(self):
        docs = [
            _make_doc({"id": "p1", "price": 100000, "property_type": "apartment"}),
        ]
        store = MagicMock()
        store.search.return_value = [(d, 1.0) for d in docs]
        tool = PriceAnalysisTool(vector_store=store)
        result = tool._run("test query")
        assert "Price per m" not in result

    @pytest.mark.asyncio
    async def test_arun_delegates_to_run(self):
        store = MagicMock()
        store.search.return_value = []
        tool = PriceAnalysisTool(vector_store=store)
        sync_result = tool._run("query")
        async_result = await tool._arun("query")
        assert sync_result == async_result


# ===========================================================================
# LocationAnalysisTool
# ===========================================================================


class TestLocationAnalysisTool:
    """Tests for LocationAnalysisTool with vector store."""

    def test_no_vector_store_returns_guidance(self):
        tool = LocationAnalysisTool(vector_store=None)
        result = tool._run("prop1")
        assert "Location Analysis" in result
        assert "N/A" in result

    def test_vector_store_without_get_by_ids(self):
        store = MagicMock(spec=[])
        tool = LocationAnalysisTool(vector_store=store)
        result = tool._run("prop1")
        assert "does not support" in result

    def test_property_not_found(self):
        store = _mock_vector_store_with_get_by_ids({})
        tool = LocationAnalysisTool(vector_store=store)
        result = tool._run("missing_prop")
        assert "Property not found" in result

    def test_property_with_coordinates_and_neighborhood(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = LocationAnalysisTool(vector_store=store)
        result = tool._run("prop1")
        assert "Location Analysis" in result
        assert "Krakow" in result
        assert "Kazimierz" in result
        assert "50.0647" in result
        assert "Geospatial data available" in result

    def test_property_with_coordinates_no_neighborhood(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = LocationAnalysisTool(vector_store=store)
        result = tool._run("prop2")  # prop2 has no neighborhood
        assert "Warsaw" in result
        assert "Geospatial data available" in result
        assert "Neighborhood" not in result

    def test_property_without_coordinates(self):
        doc = _make_doc({"id": "no_coords", "city": "Berlin"})
        store = _mock_vector_store_with_get_by_ids({"no_coords": doc})
        tool = LocationAnalysisTool(vector_store=store)
        result = tool._run("no_coords")
        assert "coordinates not available" in result.lower()

    def test_property_with_missing_city_defaults_to_unknown(self):
        doc = _make_doc({"id": "no_city", "lat": 52.0, "lon": 13.0})
        store = _mock_vector_store_with_get_by_ids({"no_city": doc})
        tool = LocationAnalysisTool(vector_store=store)
        result = tool._run("no_city")
        assert "Unknown" in result

    def test_exception_handling(self):
        store = MagicMock()
        store.get_properties_by_ids.side_effect = RuntimeError("DB error")
        tool = LocationAnalysisTool(vector_store=store)
        result = tool._run("prop1")
        assert "Error analyzing location" in result

    @pytest.mark.asyncio
    async def test_arun_delegates_to_run(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = LocationAnalysisTool(vector_store=store)
        sync_result = tool._run("prop1")
        async_result = await tool._arun("prop1")
        assert sync_result == async_result


# ===========================================================================
# CommuteTimeAnalysisTool
# ===========================================================================


class TestCommuteTimeAnalysisTool:
    """Tests for CommuteTimeAnalysisTool from comparison_tools module."""

    def test_no_vector_store(self):
        tool = CommuteTimeAnalysisTool(vector_store=None)
        result = tool._run(
            property_id="prop1",
            destination_lat=52.0,
            destination_lon=21.0,
        )
        assert "Vector store not available" in result

    def test_property_not_found(self):
        store = _mock_vector_store_with_get_by_ids({})
        tool = CommuteTimeAnalysisTool(vector_store=store)
        result = tool._run(
            property_id="missing",
            destination_lat=52.0,
            destination_lon=21.0,
        )
        assert "Property not found" in result

    def test_property_without_coordinates(self):
        doc = _make_doc({"id": "nocoord"})
        store = _mock_vector_store_with_get_by_ids({"nocoord": doc})
        tool = CommuteTimeAnalysisTool(vector_store=store)
        result = tool._run(
            property_id="nocoord",
            destination_lat=52.0,
            destination_lon=21.0,
        )
        assert "coordinates not available" in result.lower()

    def test_valid_commute_with_mock_client(self):
        """Test with CommuteTimeClient returning mock commute result."""
        store = _mock_vector_store_with_get_by_ids()
        tool = CommuteTimeAnalysisTool(vector_store=store)

        # Use nearby coordinates so the mock Haversine distance is short (< 30 min)
        result = tool._run(
            property_id="prop1",
            destination_lat=50.0650,
            destination_lon=19.9455,
            mode="transit",
            destination_name="Central Station",
        )

        assert "Commute Analysis" in result
        assert "prop1" in result
        assert "Central Station" in result
        assert "Transit" in result
        assert "Duration" in result
        assert "Distance" in result
        assert "Assessment" in result

    def test_commute_assessment_under_30_min(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = CommuteTimeAnalysisTool(vector_store=store)

        mock_result = MagicMock()
        mock_result.duration_seconds = 1500  # 25 min
        mock_result.duration_text = "25m"
        mock_result.distance_text = "8km"
        mock_result.arrival_time = None

        with patch("asyncio.run", return_value=mock_result):
            result = tool._run(
                property_id="prop1",
                destination_lat=52.0,
                destination_lon=21.0,
                mode="driving",
            )

        assert "Excellent commute time!" in result

    def test_commute_assessment_30_to_45_min(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = CommuteTimeAnalysisTool(vector_store=store)

        mock_result = MagicMock()
        mock_result.duration_seconds = 2400  # 40 min
        mock_result.duration_text = "40m"
        mock_result.distance_text = "15km"
        mock_result.arrival_time = None

        with patch("asyncio.run", return_value=mock_result):
            result = tool._run(
                property_id="prop1",
                destination_lat=52.0,
                destination_lon=21.0,
                mode="driving",
            )

        assert "Reasonable commute time" in result

    def test_commute_assessment_45_to_60_min(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = CommuteTimeAnalysisTool(vector_store=store)

        mock_result = MagicMock()
        mock_result.duration_seconds = 3300  # 55 min
        mock_result.duration_text = "55m"
        mock_result.distance_text = "20km"
        mock_result.arrival_time = None

        with patch("asyncio.run", return_value=mock_result):
            result = tool._run(
                property_id="prop1",
                destination_lat=52.0,
                destination_lon=21.0,
                mode="transit",
            )

        assert "Long commute" in result

    def test_commute_assessment_over_60_min(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = CommuteTimeAnalysisTool(vector_store=store)

        mock_result = MagicMock()
        mock_result.duration_seconds = 5400  # 90 min
        mock_result.duration_text = "1h 30m"
        mock_result.distance_text = "50km"
        mock_result.arrival_time = None

        with patch("asyncio.run", return_value=mock_result):
            result = tool._run(
                property_id="prop1",
                destination_lat=52.0,
                destination_lon=21.0,
                mode="transit",
            )

        assert "Very long commute" in result

    def test_valid_departure_time_parsed(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = CommuteTimeAnalysisTool(vector_store=store)

        mock_result = MagicMock()
        mock_result.duration_seconds = 1800
        mock_result.duration_text = "30m"
        mock_result.distance_text = "10km"
        mock_result.arrival_time = None

        with patch("asyncio.run", return_value=mock_result):
            result = tool._run(
                property_id="prop1",
                destination_lat=52.0,
                destination_lon=21.0,
                mode="transit",
                departure_time="2024-06-15T08:30:00",
            )

        assert "Commute Analysis" in result

    def test_invalid_departure_time_format(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = CommuteTimeAnalysisTool(vector_store=store)

        result = tool._run(
            property_id="prop1",
            destination_lat=52.0,
            destination_lon=21.0,
            mode="transit",
            departure_time="not-a-date",
        )

        assert "Invalid departure_time format" in result

    def test_with_arrival_time(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = CommuteTimeAnalysisTool(vector_store=store)

        mock_result = MagicMock()
        mock_result.duration_seconds = 1800
        mock_result.duration_text = "30m"
        mock_result.distance_text = "10km"
        mock_result.arrival_time = datetime(2024, 6, 15, 9, 0)

        with patch("asyncio.run", return_value=mock_result):
            result = tool._run(
                property_id="prop1",
                destination_lat=52.0,
                destination_lon=21.0,
                mode="transit",
            )

        assert "Arrival:" in result
        assert "09:00" in result

    def test_destination_display_with_name(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = CommuteTimeAnalysisTool(vector_store=store)

        mock_result = MagicMock()
        mock_result.duration_seconds = 1800
        mock_result.duration_text = "30m"
        mock_result.distance_text = "10km"
        mock_result.arrival_time = None

        with patch("asyncio.run", return_value=mock_result):
            result = tool._run(
                property_id="prop1",
                destination_lat=52.0,
                destination_lon=21.0,
                mode="driving",
                destination_name="My Office",
            )

        assert "My Office" in result

    def test_destination_display_with_coordinates(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = CommuteTimeAnalysisTool(vector_store=store)

        mock_result = MagicMock()
        mock_result.duration_seconds = 1800
        mock_result.duration_text = "30m"
        mock_result.distance_text = "10km"
        mock_result.arrival_time = None

        with patch("asyncio.run", return_value=mock_result):
            result = tool._run(
                property_id="prop1",
                destination_lat=52.2297,
                destination_lon=21.0122,
                mode="walking",
            )

        assert "52.2297" in result

    def test_exception_handling(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = CommuteTimeAnalysisTool(vector_store=store)

        with patch("asyncio.run", side_effect=RuntimeError("API error")):
            result = tool._run(
                property_id="prop1",
                destination_lat=52.0,
                destination_lon=21.0,
            )

        assert "Error calculating commute time" in result

    @pytest.mark.asyncio
    async def test_arun_delegates_to_run(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = CommuteTimeAnalysisTool(vector_store=store)

        mock_result = MagicMock()
        mock_result.duration_seconds = 1800
        mock_result.duration_text = "30m"
        mock_result.distance_text = "10km"
        mock_result.arrival_time = None

        with patch("asyncio.run", return_value=mock_result):
            sync_result = tool._run(
                property_id="prop1",
                destination_lat=52.0,
                destination_lon=21.0,
            )
            async_result = await tool._arun(
                property_id="prop1",
                destination_lat=52.0,
                destination_lon=21.0,
            )

        assert sync_result == async_result


# ===========================================================================
# CommuteRankingTool
# ===========================================================================


class TestCommuteRankingTool:
    """Tests for CommuteRankingTool from comparison_tools module."""

    def test_no_vector_store(self):
        tool = CommuteRankingTool(vector_store=None)
        result = tool._run(
            property_ids="prop1,prop2",
            destination_lat=52.0,
            destination_lon=21.0,
        )
        assert "Vector store not available" in result

    def test_empty_property_ids(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = CommuteRankingTool(vector_store=store)
        result = tool._run(
            property_ids="  ,  ,  ",
            destination_lat=52.0,
            destination_lon=21.0,
        )
        assert "At least one property_id is required" in result

    def test_no_properties_found(self):
        store = MagicMock()
        store.get_properties_by_ids.return_value = []
        tool = CommuteRankingTool(vector_store=store)
        result = tool._run(
            property_ids="prop1,prop2",
            destination_lat=52.0,
            destination_lon=21.0,
        )
        assert "No properties found" in result

    def test_properties_without_coordinates(self):
        doc = _make_doc({"id": "no_coords"})
        store = _mock_vector_store_with_get_by_ids({"no_coords": doc})
        tool = CommuteRankingTool(vector_store=store)
        result = tool._run(
            property_ids="no_coords",
            destination_lat=52.0,
            destination_lon=21.0,
        )
        assert "No properties with valid coordinates" in result

    def test_invalid_departure_time(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = CommuteRankingTool(vector_store=store)
        result = tool._run(
            property_ids="prop1",
            destination_lat=52.0,
            destination_lon=21.0,
            departure_time="invalid-date",
        )
        assert "Invalid departure_time format" in result

    def test_valid_ranking_with_mock_client(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = CommuteRankingTool(vector_store=store)

        result1 = MagicMock()
        result1.property_id = "prop1"
        result1.duration_text = "20m"
        result1.distance_text = "8km"

        result2 = MagicMock()
        result2.property_id = "prop2"
        result2.duration_text = "35m"
        result2.distance_text = "12km"

        with patch("asyncio.run", return_value=[result1, result2]):
            result = tool._run(
                property_ids="prop1,prop2",
                destination_lat=52.0,
                destination_lon=21.0,
                mode="driving",
                destination_name="Office",
            )

        assert "Commute Ranking" in result
        assert "Office" in result
        assert "Driving" in result
        assert "Fastest" in result
        assert "Slowest" in result
        assert "20m" in result
        assert "35m" in result

    def test_ranking_without_property_title_falls_back_to_id(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = CommuteRankingTool(vector_store=store)

        mock_result = MagicMock()
        mock_result.property_id = "prop1"
        mock_result.duration_text = "20m"
        mock_result.distance_text = "8km"

        with patch("asyncio.run", return_value=[mock_result]):
            result = tool._run(
                property_ids="prop1",
                destination_lat=52.0,
                destination_lon=21.0,
                mode="walking",
            )

        assert "prop1" in result

    def test_ranking_with_custom_title(self):
        doc = _make_doc({"id": "titled", "lat": 50.0, "lon": 20.0, "title": "Nice Flat"})
        store = _mock_vector_store_with_get_by_ids({"titled": doc})
        tool = CommuteRankingTool(vector_store=store)

        mock_result = MagicMock()
        mock_result.property_id = "titled"
        mock_result.duration_text = "15m"
        mock_result.distance_text = "5km"

        with patch("asyncio.run", return_value=[mock_result]):
            result = tool._run(
                property_ids="titled",
                destination_lat=52.0,
                destination_lon=21.0,
                mode="bicycling",
            )

        assert "Nice Flat" in result

    def test_ranking_without_destination_name_shows_coords(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = CommuteRankingTool(vector_store=store)

        mock_result = MagicMock()
        mock_result.property_id = "prop1"
        mock_result.duration_text = "20m"
        mock_result.distance_text = "8km"

        with patch("asyncio.run", return_value=[mock_result]):
            result = tool._run(
                property_ids="prop1",
                destination_lat=52.2297,
                destination_lon=21.0122,
                mode="transit",
            )

        assert "52.2297" in result

    def test_empty_ranking_results(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = CommuteRankingTool(vector_store=store)

        with patch("asyncio.run", return_value=[]):
            result = tool._run(
                property_ids="prop1",
                destination_lat=52.0,
                destination_lon=21.0,
            )

        assert "Unable to calculate commute times" in result

    def test_exception_handling(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = CommuteRankingTool(vector_store=store)

        with patch("asyncio.run", side_effect=RuntimeError("API error")):
            result = tool._run(
                property_ids="prop1",
                destination_lat=52.0,
                destination_lon=21.0,
            )

        assert "Error" in result

    def test_title_truncation(self):
        long_title = "A" * 50
        doc = _make_doc({"id": "long_title", "lat": 50.0, "lon": 20.0, "title": long_title})
        store = _mock_vector_store_with_get_by_ids({"long_title": doc})
        tool = CommuteRankingTool(vector_store=store)

        mock_result = MagicMock()
        mock_result.property_id = "long_title"
        mock_result.duration_text = "20m"
        mock_result.distance_text = "8km"

        with patch("asyncio.run", return_value=[mock_result]):
            result = tool._run(
                property_ids="long_title",
                destination_lat=52.0,
                destination_lon=21.0,
            )

        # Title should be truncated to 28 chars
        truncated = long_title[:28]
        assert truncated in result

    def test_valid_departure_time_in_ranking(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = CommuteRankingTool(vector_store=store)

        mock_result = MagicMock()
        mock_result.property_id = "prop1"
        mock_result.duration_text = "20m"
        mock_result.distance_text = "8km"

        with patch("asyncio.run", return_value=[mock_result]):
            result = tool._run(
                property_ids="prop1",
                destination_lat=52.0,
                destination_lon=21.0,
                departure_time="2024-06-15T08:30:00",
            )

        assert "Commute Ranking" in result

    def test_doc_with_none_metadata_handled(self):
        doc = _make_doc({"id": "null_meta"})
        doc.metadata = None
        store = MagicMock()
        store.get_properties_by_ids.return_value = [doc]
        tool = CommuteRankingTool(vector_store=store)
        result = tool._run(
            property_ids="null_meta",
            destination_lat=52.0,
            destination_lon=21.0,
        )
        # Should handle None metadata gracefully
        assert "No properties with valid coordinates" in result

    @pytest.mark.asyncio
    async def test_arun_delegates_to_run(self):
        store = _mock_vector_store_with_get_by_ids()
        tool = CommuteRankingTool(vector_store=store)

        mock_result = MagicMock()
        mock_result.property_id = "prop1"
        mock_result.duration_text = "20m"
        mock_result.distance_text = "8km"

        with patch("asyncio.run", return_value=[mock_result]):
            sync_result = tool._run(
                property_ids="prop1",
                destination_lat=52.0,
                destination_lon=21.0,
            )
            async_result = await tool._arun(
                property_ids="prop1",
                destination_lat=52.0,
                destination_lon=21.0,
            )

        assert sync_result == async_result


# ===========================================================================
# Input Schema Validation
# ===========================================================================


class TestInputSchemas:
    """Test Pydantic input schema validation."""

    def test_property_comparison_input_requires_non_empty(self):
        from tools.comparison_tools import PropertyComparisonInput

        with pytest.raises(PydanticValidationError):
            PropertyComparisonInput(property_ids="")

    def test_price_analysis_input_requires_non_empty(self):
        from tools.comparison_tools import PriceAnalysisInput

        with pytest.raises(PydanticValidationError):
            PriceAnalysisInput(query="")

    def test_location_analysis_input_requires_non_empty(self):
        from tools.comparison_tools import LocationAnalysisInput

        with pytest.raises(PydanticValidationError):
            LocationAnalysisInput(property_id="")

    def test_commute_time_input_lat_range(self):
        from tools.comparison_tools import CommuteTimeInput

        # Valid
        ci = CommuteTimeInput(property_id="p1", destination_lat=45.0, destination_lon=10.0)
        assert ci.destination_lat == 45.0

        # Invalid lat
        with pytest.raises(PydanticValidationError):
            CommuteTimeInput(property_id="p1", destination_lat=100.0, destination_lon=10.0)

    def test_commute_time_input_lon_range(self):
        from tools.comparison_tools import CommuteTimeInput

        # Invalid lon
        with pytest.raises(PydanticValidationError):
            CommuteTimeInput(property_id="p1", destination_lat=45.0, destination_lon=200.0)

    def test_commute_ranking_input_lat_lon_range(self):
        from tools.comparison_tools import CommuteRankingInput

        # Valid
        ri = CommuteRankingInput(property_ids="p1,p2", destination_lat=0.0, destination_lon=0.0)
        assert ri.destination_lat == 0.0

        # Invalid lat
        with pytest.raises(PydanticValidationError):
            CommuteRankingInput(property_ids="p1,p2", destination_lat=-91.0, destination_lon=0.0)

    def test_commute_input_defaults(self):
        from tools.comparison_tools import CommuteTimeInput

        ci = CommuteTimeInput(property_id="p1", destination_lat=0.0, destination_lon=0.0)
        assert ci.mode == "transit"
        assert ci.destination_name is None
        assert ci.departure_time is None

    def test_commute_ranking_input_defaults(self):
        from tools.comparison_tools import CommuteRankingInput

        ri = CommuteRankingInput(property_ids="p1", destination_lat=0.0, destination_lon=0.0)
        assert ri.mode == "transit"
        assert ri.destination_name is None
        assert ri.departure_time is None
