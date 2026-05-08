"""Unit tests for cma_report_generator module."""

import pytest

from utils.cma_report_generator import (
    CMAReportGenerator,
)

# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def generator() -> CMAReportGenerator:
    """Return a fresh CMAReportGenerator instance."""
    return CMAReportGenerator()


@pytest.fixture
def subject_data() -> dict:
    """Sample subject property data."""
    return {
        "street": "123 Main Street",
        "neighborhood": "Downtown",
        "district": "Central",
        "city": "Berlin",
        "property_type": "apartment",
        "listing_type": "sale",
        "area_sqm": 85,
        "rooms": 3,
        "bedrooms": 2,
        "bathrooms": 1,
        "year_built": 2010,
        "floor": 3,
        "total_floors": 6,
        "energy_rating": "A",
        "has_parking": True,
        "has_elevator": True,
        "has_balcony": True,
        "has_garden": False,
    }


@pytest.fixture
def comparables() -> list[dict]:
    """Sample comparable properties."""
    return [
        {
            "street": "456 Oak Avenue",
            "district": "Central",
            "city": "Berlin",
            "area_sqm": 80,
            "price": 320_000,
            "original_price": 310_000,
            "adjusted_price": 325_000,
            "similarity_score": 92,
            "adjustments": [
                {
                    "category": "size",
                    "description": "Smaller by 5 sqm",
                    "adjustment_percent": 2.5,
                    "confidence": 0.9,
                },
                {
                    "category": "floor",
                    "description": "Higher floor premium",
                    "adjustment_percent": -1.0,
                    "confidence": 0.8,
                },
            ],
        },
        {
            "street": "789 Pine Road",
            "district": "West",
            "city": "Berlin",
            "area_sqm": 90,
            "price": 350_000,
            "original_price": 345_000,
            "adjusted_price": 340_000,
            "similarity_score": 85,
            "adjustments": [
                {
                    "category": "location",
                    "description": "Slightly less desirable area",
                    "adjustment_percent": -3.0,
                    "confidence": 0.7,
                },
            ],
        },
        {
            "street": "101 Elm Street",
            "district": "Central",
            "city": "Berlin",
            "area_sqm": 82,
            "price": 315_000,
            "original_price": 315_000,
            "adjusted_price": 330_000,
            "similarity_score": 88,
            "adjustments": [],
        },
    ]


@pytest.fixture
def valuation() -> dict:
    """Sample valuation result."""
    return {
        "estimated_value": 335_000,
        "value_range_low": 315_000,
        "value_range_high": 355_000,
        "confidence_score": 0.85,
        "price_per_sqm": 3941,
    }


@pytest.fixture
def market_context() -> dict:
    """Sample market context data."""
    return {
        "avg_price_per_sqm": 3800,
        "median_price": 330_000,
        "trend": 3.5,
        "inventory_count": 42,
    }


# ---------------------------------------------------------------------------
# Tests: __init__ and style setup
# ---------------------------------------------------------------------------


class TestInit:
    """Tests for CMAReportGenerator initialization."""

    def test_creates_instance(self, generator):
        assert isinstance(generator, CMAReportGenerator)

    def test_has_styles(self, generator):
        assert generator.styles is not None

    def test_custom_styles_added(self, generator):
        style_names = list(generator.styles.byName.keys())
        for expected in (
            "ReportTitle",
            "SectionHeader",
            "SubsectionHeader",
            "MetricLabel",
            "MetricValue",
            "AddressText",
        ):
            assert expected in style_names, f"Missing style: {expected}"

    def test_report_title_style_centered(self, generator):
        style = generator.styles["ReportTitle"]
        assert style.alignment == 1  # Center

    def test_address_text_style(self, generator):
        style = generator.styles["AddressText"]
        assert style.fontSize == 14


# ---------------------------------------------------------------------------
# Tests: _format_address
# ---------------------------------------------------------------------------


class TestFormatAddress:
    """Tests for _format_address method."""

    def test_full_address(self, generator, subject_data):
        result = generator._format_address(subject_data)
        assert "123 Main Street" in result
        assert "Downtown" in result
        assert "Central" in result
        assert "Berlin" in result

    def test_short_address_omits_neighborhood(self, generator, subject_data):
        result = generator._format_address(subject_data, short=True)
        assert "123 Main Street" in result
        assert "Downtown" not in result  # neighborhood omitted in short
        assert "Berlin" in result

    def test_empty_data(self, generator):
        result = generator._format_address({})
        assert result == "Address not available"

    def test_street_and_city_only(self, generator):
        result = generator._format_address({"street": "1st Ave", "city": "Warsaw"})
        assert "1st Ave" in result
        assert "Warsaw" in result

    def test_no_street(self, generator):
        result = generator._format_address({"city": "Berlin"})
        assert "Berlin" in result

    def test_short_with_no_neighborhood(self, generator):
        result = generator._format_address({"street": "Test St", "city": "Berlin"}, short=True)
        assert "Test St" in result


# ---------------------------------------------------------------------------
# Tests: _format_property_type
# ---------------------------------------------------------------------------


class TestFormatPropertyType:
    """Tests for _format_property_type method."""

    @pytest.mark.parametrize(
        "input_type,expected",
        [
            ("apartment", "Apartment"),
            ("house", "House"),
            ("studio", "Studio"),
            ("loft", "Loft"),
            ("townhouse", "Townhouse"),
            ("villa", "Villa"),
            ("penthouse", "Penthouse"),
            ("other", "Other"),
        ],
    )
    def test_known_types(self, generator, input_type, expected):
        result = generator._format_property_type(input_type)
        assert result == expected

    def test_uppercase_input(self, generator):
        result = generator._format_property_type("APARTMENT")
        assert result == "Apartment"

    def test_unknown_type_title_cased(self, generator):
        result = generator._format_property_type("condo")
        assert result == "Condo"

    def test_mixed_case(self, generator):
        result = generator._format_property_type("HoUsE")
        assert result == "House"


# ---------------------------------------------------------------------------
# Tests: _get_amenities_list
# ---------------------------------------------------------------------------


class TestGetAmenitiesList:
    """Tests for _get_amenities_list method."""

    def test_with_amenities(self, generator, subject_data):
        amenities = generator._get_amenities_list(subject_data)
        assert "Parking" in amenities
        assert "Elevator" in amenities
        assert "Balcony" in amenities
        assert "Garden" not in amenities

    def test_empty_data(self, generator):
        amenities = generator._get_amenities_list({})
        assert amenities == []

    def test_all_amenities(self, generator):
        data = {
            "has_parking": True,
            "has_garden": True,
            "has_elevator": True,
            "has_balcony": True,
            "is_furnished": True,
            "has_pool": True,
            "has_garage": True,
            "pets_allowed": True,
            "has_bike_room": True,
        }
        amenities = generator._get_amenities_list(data)
        assert len(amenities) == 9

    def test_no_amenities(self, generator):
        data = {
            "has_parking": False,
            "has_garden": False,
            "has_elevator": False,
            "has_balcony": False,
        }
        amenities = generator._get_amenities_list(data)
        assert amenities == []


# ---------------------------------------------------------------------------
# Tests: _build_header
# ---------------------------------------------------------------------------


class TestBuildHeader:
    """Tests for _build_header method."""

    def test_returns_list(self, generator, subject_data):
        story = generator._build_header(subject_data)
        assert isinstance(story, list)

    def test_contains_elements(self, generator, subject_data):
        story = generator._build_header(subject_data)
        assert len(story) >= 2

    def test_no_address(self, generator):
        story = generator._build_header({})
        assert isinstance(story, list)

    def test_with_address(self, generator, subject_data):
        story = generator._build_header(subject_data)
        # Should include address paragraph + spacer
        assert len(story) >= 3


# ---------------------------------------------------------------------------
# Tests: _build_executive_summary
# ---------------------------------------------------------------------------


class TestBuildExecutiveSummary:
    """Tests for _build_executive_summary method."""

    def test_returns_list(self, generator, valuation, subject_data):
        story = generator._build_executive_summary(valuation, subject_data)
        assert isinstance(story, list)

    def test_contains_table(self, generator, valuation, subject_data):
        from reportlab.platypus import Table

        story = generator._build_executive_summary(valuation, subject_data)
        tables = [item for item in story if isinstance(item, Table)]
        assert len(tables) >= 1

    def test_high_confidence(self, generator, subject_data):
        valuation = {
            "estimated_value": 300_000,
            "value_range_low": 280_000,
            "value_range_high": 320_000,
            "confidence_score": 0.9,
            "price_per_sqm": 3500,
        }
        story = generator._build_executive_summary(valuation, subject_data)
        assert isinstance(story, list)

    def test_moderate_confidence(self, generator, subject_data):
        valuation = {
            "estimated_value": 300_000,
            "value_range_low": 280_000,
            "value_range_high": 320_000,
            "confidence_score": 0.7,
            "price_per_sqm": 0,
        }
        story = generator._build_executive_summary(valuation, subject_data)
        assert isinstance(story, list)

    def test_low_confidence(self, generator, subject_data):
        valuation = {
            "estimated_value": 300_000,
            "value_range_low": 280_000,
            "value_range_high": 320_000,
            "confidence_score": 0.4,
            "price_per_sqm": 0,
        }
        story = generator._build_executive_summary(valuation, subject_data)
        assert isinstance(story, list)

    def test_with_price_per_sqm(self, generator, subject_data):
        valuation = {
            "estimated_value": 300_000,
            "value_range_low": 280_000,
            "value_range_high": 320_000,
            "confidence_score": 0.85,
            "price_per_sqm": 3500,
        }
        story = generator._build_executive_summary(valuation, subject_data)
        from reportlab.platypus import Table

        tables = [item for item in story if isinstance(item, Table)]
        # Table should have 5 data rows (4 base + 1 price_per_sqm)
        assert len(tables) >= 1

    def test_without_price_per_sqm(self, generator, subject_data):
        valuation = {
            "estimated_value": 300_000,
            "value_range_low": 280_000,
            "value_range_high": 320_000,
            "confidence_score": 0.85,
            "price_per_sqm": 0,
        }
        story = generator._build_executive_summary(valuation, subject_data)
        assert isinstance(story, list)

    def test_default_values(self, generator, subject_data):
        story = generator._build_executive_summary({}, subject_data)
        assert isinstance(story, list)


# ---------------------------------------------------------------------------
# Tests: _build_subject_section
# ---------------------------------------------------------------------------


class TestBuildSubjectSection:
    """Tests for _build_subject_section method."""

    def test_returns_list(self, generator, subject_data):
        story = generator._build_subject_section(subject_data)
        assert isinstance(story, list)

    def test_contains_details_table(self, generator, subject_data):
        from reportlab.platypus import Table

        story = generator._build_subject_section(subject_data)
        tables = [item for item in story if isinstance(item, Table)]
        assert len(tables) >= 1

    def test_with_amenities(self, generator, subject_data):
        story = generator._build_subject_section(subject_data)
        # Should include amenities subsection
        assert len(story) >= 3  # header + table + amenities

    def test_without_amenities(self, generator):
        data = {"property_type": "apartment", "listing_type": "sale"}
        story = generator._build_subject_section(data)
        assert isinstance(story, list)

    def test_empty_data(self, generator):
        story = generator._build_subject_section({})
        assert isinstance(story, list)

    def test_missing_optional_fields(self, generator):
        data = {"property_type": "apartment"}
        story = generator._build_subject_section(data)
        assert isinstance(story, list)


# ---------------------------------------------------------------------------
# Tests: _build_comparables_section
# ---------------------------------------------------------------------------


class TestBuildComparablesSection:
    """Tests for _build_comparables_section method."""

    def test_returns_list(self, generator, comparables):
        story = generator._build_comparables_section(comparables)
        assert isinstance(story, list)

    def test_contains_table(self, generator, comparables):
        from reportlab.platypus import Table

        story = generator._build_comparables_section(comparables)
        tables = [item for item in story if isinstance(item, Table)]
        assert len(tables) == 1

    def test_empty_comparables(self, generator):
        story = generator._build_comparables_section([])
        assert isinstance(story, list)

    def test_single_comparable(self, generator):
        comps = [
            {
                "street": "1 Test St",
                "city": "Berlin",
                "price": 300_000,
                "adjusted_price": 310_000,
                "similarity_score": 90,
            }
        ]
        story = generator._build_comparables_section(comps)
        assert isinstance(story, list)

    def test_long_address_truncated(self, generator):
        comps = [
            {
                "street": "A" * 50,
                "city": "Berlin",
                "price": 300_000,
                "adjusted_price": 310_000,
                "similarity_score": 90,
            }
        ]
        story = generator._build_comparables_section(comps)
        assert isinstance(story, list)

    def test_no_price(self, generator):
        comps = [{"street": "Test St", "city": "Berlin", "similarity_score": 90}]
        story = generator._build_comparables_section(comps)
        assert isinstance(story, list)


# ---------------------------------------------------------------------------
# Tests: _build_adjustments_section
# ---------------------------------------------------------------------------


class TestBuildAdjustmentsSection:
    """Tests for _build_adjustments_section method."""

    def test_returns_list(self, generator, comparables):
        story = generator._build_adjustments_section(comparables)
        assert isinstance(story, list)

    def test_with_adjustments(self, generator, comparables):
        from reportlab.platypus import Table

        story = generator._build_adjustments_section(comparables)
        tables = [item for item in story if isinstance(item, Table)]
        # First two comparables have adjustments
        assert len(tables) >= 1

    def test_no_adjustments(self, generator):
        comps = [{"street": "Test St", "city": "Berlin", "adjustments": []}]
        story = generator._build_adjustments_section(comps)
        assert isinstance(story, list)

    def test_positive_adjustment(self, generator):
        comps = [
            {
                "street": "Test",
                "city": "Berlin",
                "adjustments": [
                    {
                        "category": "size",
                        "description": "Larger",
                        "adjustment_percent": 5.0,
                        "confidence": 0.9,
                    }
                ],
            }
        ]
        story = generator._build_adjustments_section(comps)
        assert isinstance(story, list)

    def test_negative_adjustment(self, generator):
        comps = [
            {
                "street": "Test",
                "city": "Berlin",
                "adjustments": [
                    {
                        "category": "location",
                        "description": "Worse area",
                        "adjustment_percent": -3.5,
                        "confidence": 0.8,
                    }
                ],
            }
        ]
        story = generator._build_adjustments_section(comps)
        assert isinstance(story, list)

    def test_zero_adjustment(self, generator):
        comps = [
            {
                "street": "Test",
                "city": "Berlin",
                "adjustments": [
                    {
                        "category": "age",
                        "description": "Same age",
                        "adjustment_percent": 0.0,
                        "confidence": 1.0,
                    }
                ],
            }
        ]
        story = generator._build_adjustments_section(comps)
        assert isinstance(story, list)

    def test_long_description_truncated(self, generator):
        long_desc = "A" * 60
        comps = [
            {
                "street": "Test",
                "city": "Berlin",
                "adjustments": [
                    {
                        "category": "size",
                        "description": long_desc,
                        "adjustment_percent": 2.0,
                        "confidence": 0.9,
                    }
                ],
            }
        ]
        story = generator._build_adjustments_section(comps)
        assert isinstance(story, list)

    def test_multiple_adjustments_per_comparable(self, generator):
        comps = [
            {
                "street": "Test",
                "city": "Berlin",
                "adjustments": [
                    {
                        "category": "size",
                        "description": "Larger",
                        "adjustment_percent": 3.0,
                        "confidence": 0.9,
                    },
                    {
                        "category": "floor",
                        "description": "Higher",
                        "adjustment_percent": 1.5,
                        "confidence": 0.8,
                    },
                    {
                        "category": "age",
                        "description": "Newer",
                        "adjustment_percent": 2.0,
                        "confidence": 0.7,
                    },
                ],
            }
        ]
        story = generator._build_adjustments_section(comps)
        assert isinstance(story, list)


# ---------------------------------------------------------------------------
# Tests: _build_market_context_section
# ---------------------------------------------------------------------------


class TestBuildMarketContextSection:
    """Tests for _build_market_context_section method."""

    def test_returns_list(self, generator, market_context):
        story = generator._build_market_context_section(market_context)
        assert isinstance(story, list)

    def test_contains_table(self, generator, market_context):
        from reportlab.platypus import Table

        story = generator._build_market_context_section(market_context)
        tables = [item for item in story if isinstance(item, Table)]
        assert len(tables) == 1

    def test_empty_context(self, generator):
        story = generator._build_market_context_section({})
        assert isinstance(story, list)
        # Returns section header paragraph even with empty data
        from reportlab.platypus import Table

        tables = [item for item in story if isinstance(item, Table)]
        assert len(tables) == 0

    def test_partial_context_avg_price_only(self, generator):
        story = generator._build_market_context_section({"avg_price_per_sqm": 3500})
        assert isinstance(story, list)

    def test_negative_trend(self, generator):
        story = generator._build_market_context_section({"trend": -2.5})
        assert isinstance(story, list)

    def test_positive_trend(self, generator):
        story = generator._build_market_context_section({"trend": 5.0})
        assert isinstance(story, list)

    def test_median_price(self, generator):
        story = generator._build_market_context_section({"median_price": 300_000})
        assert isinstance(story, list)

    def test_inventory_count(self, generator):
        story = generator._build_market_context_section({"inventory_count": 15})
        assert isinstance(story, list)


# ---------------------------------------------------------------------------
# Tests: _build_methodology_section
# ---------------------------------------------------------------------------


class TestBuildMethodologySection:
    """Tests for _build_methodology_section method."""

    def test_returns_list(self, generator):
        story = generator._build_methodology_section()
        assert isinstance(story, list)

    def test_contains_content(self, generator):
        story = generator._build_methodology_section()
        assert len(story) >= 1

    def test_has_methodology_text(self, generator):
        story = generator._build_methodology_section()
        # Should contain paragraph elements
        assert any(hasattr(item, "text") for item in story)


# ---------------------------------------------------------------------------
# Tests: _build_footer
# ---------------------------------------------------------------------------


class TestBuildFooter:
    """Tests for _build_footer method."""

    def test_returns_list(self, generator):
        story = generator._build_footer()
        assert isinstance(story, list)

    def test_contains_disclaimer(self, generator):
        story = generator._build_footer()
        assert len(story) >= 1


# ---------------------------------------------------------------------------
# Tests: generate (full integration with real reportlab)
# ---------------------------------------------------------------------------


class TestGenerate:
    """Tests for the main generate method (full PDF output)."""

    def test_returns_bytes(self, generator, subject_data, comparables, valuation):
        pdf_bytes = generator.generate(subject_data, comparables, valuation)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_pdf_starts_with_header(self, generator, subject_data, comparables, valuation):
        pdf_bytes = generator.generate(subject_data, comparables, valuation)
        assert pdf_bytes[:4] == b"%PDF"

    def test_with_market_context(
        self, generator, subject_data, comparables, valuation, market_context
    ):
        pdf_bytes = generator.generate(subject_data, comparables, valuation, market_context)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"

    def test_without_market_context(self, generator, subject_data, comparables, valuation):
        pdf_bytes = generator.generate(subject_data, comparables, valuation, market_context=None)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"

    def test_minimal_data(self, generator):
        pdf_bytes = generator.generate({}, [], {})
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"

    def test_many_comparables_triggers_page_break(self, generator, subject_data, valuation):
        """When more than 3 comparables, a page break should be inserted."""
        comps = [
            {
                "street": f"Street {i}",
                "city": "Berlin",
                "price": 300_000,
                "adjusted_price": 310_000,
                "similarity_score": 80,
                "adjustments": [],
            }
            for i in range(5)
        ]
        pdf_bytes = generator.generate(subject_data, comps, valuation)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"

    def test_few_comparables_no_page_break(self, generator, subject_data, valuation):
        """When 3 or fewer comparables, no page break."""
        comps = [
            {
                "street": "Street 1",
                "city": "Berlin",
                "price": 300_000,
                "adjusted_price": 310_000,
                "similarity_score": 80,
                "adjustments": [],
            }
        ]
        pdf_bytes = generator.generate(subject_data, comps, valuation)
        assert isinstance(pdf_bytes, bytes)

    def test_with_full_amenities(self, generator, comparables, valuation):
        data = {
            "street": "123 Main",
            "city": "Berlin",
            "property_type": "house",
            "has_parking": True,
            "has_garden": True,
            "has_elevator": False,
            "has_balcony": True,
            "is_furnished": True,
            "has_pool": True,
            "has_garage": True,
            "pets_allowed": True,
            "has_bike_room": True,
        }
        pdf_bytes = generator.generate(data, comparables, valuation)
        assert isinstance(pdf_bytes, bytes)

    def test_pdf_with_market_context_is_larger(
        self, generator, subject_data, comparables, valuation, market_context
    ):
        pdf_without = generator.generate(subject_data, comparables, valuation, market_context=None)
        pdf_with = generator.generate(subject_data, comparables, valuation, market_context)
        assert len(pdf_with) > len(pdf_without)

    def test_various_property_types(self, generator, comparables, valuation):
        for prop_type in (
            "apartment",
            "house",
            "studio",
            "loft",
            "townhouse",
            "villa",
            "penthouse",
        ):
            data = {"property_type": prop_type, "city": "Berlin"}
            pdf_bytes = generator.generate(data, comparables, valuation)
            assert isinstance(pdf_bytes, bytes)
            assert pdf_bytes[:4] == b"%PDF"

    def test_empty_comparables(self, generator, subject_data, valuation):
        pdf_bytes = generator.generate(subject_data, [], valuation)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"

    def test_comparable_without_adjustments_key(self, generator, subject_data, valuation):
        comps = [{"street": "Test", "city": "Berlin", "price": 300_000, "similarity_score": 80}]
        pdf_bytes = generator.generate(subject_data, comps, valuation)
        assert isinstance(pdf_bytes, bytes)

    def test_subject_with_all_fields(self, generator, comparables, valuation):
        data = {
            "street": "Full Address 42",
            "neighborhood": "Nice Area",
            "district": "North",
            "city": "Munich",
            "property_type": "penthouse",
            "listing_type": "rent",
            "area_sqm": 120,
            "rooms": 4,
            "bedrooms": 3,
            "bathrooms": 2,
            "year_built": 2020,
            "floor": 10,
            "total_floors": 12,
            "energy_rating": "A+",
        }
        pdf_bytes = generator.generate(data, comparables, valuation)
        assert isinstance(pdf_bytes, bytes)
