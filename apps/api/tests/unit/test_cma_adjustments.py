"""
Unit tests for analytics/cma_adjustments.py

Covers all classes and functions:
- CMAAdjustment dataclass (to_dict)
- AdjustedComparable dataclass (__post_init__)
- CMAAdjustmentCalculator (all methods)
- calculate_cma_adjustments convenience function
"""

from datetime import datetime, timedelta

from analytics.cma_adjustments import (
    AdjustedComparable,
    CMAAdjustment,
    CMAAdjustmentCalculator,
    calculate_cma_adjustments,
)
from data.schemas import Property, PropertyType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_property(**overrides) -> Property:
    """Create a Property with sensible defaults, overridden by kwargs."""
    defaults = dict(
        id="prop-1",
        city="Berlin",
        district="Mitte",
        neighborhood=None,
        property_type=PropertyType.APARTMENT,
        area_sqm=80.0,
        floor=2.0,
        total_floors=5.0,
        year_built=2005,
        energy_rating="C",
        price=300000.0,
        has_parking=False,
        has_garden=False,
        has_elevator=False,
        has_balcony=False,
        is_furnished=False,
        has_pool=False,
        has_garage=False,
        pets_allowed=False,
    )
    defaults.update(overrides)
    return Property(**defaults)


# ---------------------------------------------------------------------------
# CMAAdjustment dataclass
# ---------------------------------------------------------------------------


class TestCMAAdjustment:
    """Tests for the CMAAdjustment dataclass."""

    def test_to_dict_basic(self):
        adj = CMAAdjustment(
            category="location",
            description="Location difference",
            subject_value="Mitte",
            comp_value="Kreuzberg",
            adjustment_percent=0.05,
            adjustment_amount=15000.0,
            confidence=0.7,
        )
        d = adj.to_dict()
        assert d["category"] == "location"
        assert d["description"] == "Location difference"
        assert d["subject_value"] == "Mitte"
        assert d["comp_value"] == "Kreuzberg"
        assert d["adjustment_percent"] == 0.05
        assert d["adjustment_amount"] == 15000.0
        assert d["confidence"] == 0.7

    def test_to_dict_rounds_values(self):
        adj = CMAAdjustment(
            category="size",
            description="Size diff",
            subject_value="80",
            comp_value="100",
            adjustment_percent=0.123456,
            adjustment_amount=12345.6789,
            confidence=0.85123,
        )
        d = adj.to_dict()
        assert d["adjustment_percent"] == 0.12
        assert d["adjustment_amount"] == 12345.68
        assert d["confidence"] == 0.85

    def test_to_dict_none_values_converted(self):
        adj = CMAAdjustment(
            category="age",
            description="No data",
            subject_value=None,
            comp_value=None,
            adjustment_percent=0.0,
            adjustment_amount=0.0,
        )
        d = adj.to_dict()
        assert d["subject_value"] is None
        assert d["comp_value"] is None

    def test_to_dict_non_string_values_converted(self):
        adj = CMAAdjustment(
            category="age",
            description="Year diff",
            subject_value=2000,
            comp_value=2010,
            adjustment_percent=0.05,
            adjustment_amount=10000.0,
        )
        d = adj.to_dict()
        assert d["subject_value"] == "2000"
        assert d["comp_value"] == "2010"

    def test_default_confidence(self):
        adj = CMAAdjustment(
            category="test",
            description="test",
            subject_value="a",
            comp_value="b",
            adjustment_percent=0.0,
            adjustment_amount=0.0,
        )
        assert adj.confidence == 1.0


# ---------------------------------------------------------------------------
# AdjustedComparable dataclass
# ---------------------------------------------------------------------------


class TestAdjustedComparable:
    """Tests for the AdjustedComparable dataclass."""

    def test_post_init_no_adjustments_sets_adjusted_price(self):
        ac = AdjustedComparable(
            property_id="prop-1",
            original_price=300000.0,
        )
        assert ac.adjusted_price == 300000.0

    def test_post_init_with_adjustments_does_not_override(self):
        adj = CMAAdjustment(
            category="size",
            description="Size diff",
            subject_value="80",
            comp_value="100",
            adjustment_percent=0.05,
            adjustment_amount=15000.0,
        )
        ac = AdjustedComparable(
            property_id="prop-1",
            original_price=300000.0,
            adjustments=[adj],
            adjusted_price=315000.0,
        )
        # With adjustments present, __post_init__ does NOT override adjusted_price
        assert ac.adjusted_price == 315000.0

    def test_default_values(self):
        ac = AdjustedComparable(
            property_id="prop-1",
            original_price=250000.0,
        )
        assert ac.adjustments == []
        assert ac.total_adjustment_percent == 0.0
        assert ac.total_adjustment_amount == 0.0
        assert ac.adjusted_price == 250000.0
        assert ac.net_adjustment == 0.0


# ---------------------------------------------------------------------------
# CMAAdjustmentCalculator — initialization
# ---------------------------------------------------------------------------


class TestCMAAdjustmentCalculatorInit:
    """Tests for CMAAdjustmentCalculator initialization."""

    def test_default_init(self):
        calc = CMAAdjustmentCalculator()
        assert calc.market_price_trend == 0.0
        assert calc.location_price_indices == {}
        assert calc.custom_adjustments == {}

    def test_init_with_market_trend(self):
        calc = CMAAdjustmentCalculator(market_price_trend=0.03)
        assert calc.market_price_trend == 0.03

    def test_init_with_location_indices(self):
        indices = {"berlin:mitte": 1.2, "berlin:kreuzberg": 0.9}
        calc = CMAAdjustmentCalculator(location_price_indices=indices)
        assert calc.location_price_indices == indices

    def test_custom_adjustments_override_amenity_premiums(self):
        # Save original to restore after (AMENITY_PREMIUM is a mutable class-level dict)
        original_parking = CMAAdjustmentCalculator.AMENITY_PREMIUM["has_parking"]
        original_garden = CMAAdjustmentCalculator.AMENITY_PREMIUM["has_garden"]
        try:
            custom = {"has_parking": 0.10, "has_garden": 0.15}
            calc = CMAAdjustmentCalculator(custom_adjustments=custom)
            assert calc.AMENITY_PREMIUM["has_parking"] == 0.10
            assert calc.AMENITY_PREMIUM["has_garden"] == 0.15
            # Non-overridden amenity should remain
            assert calc.AMENITY_PREMIUM["has_elevator"] == 0.03
        finally:
            CMAAdjustmentCalculator.AMENITY_PREMIUM["has_parking"] = original_parking
            CMAAdjustmentCalculator.AMENITY_PREMIUM["has_garden"] = original_garden

    def test_custom_adjustments_ignores_unknown_keys(self):
        original = dict(CMAAdjustmentCalculator.AMENITY_PREMIUM)
        try:
            custom = {"unknown_amenity": 0.99}
            calc = CMAAdjustmentCalculator(custom_adjustments=custom)
            assert "unknown_amenity" not in calc.AMENITY_PREMIUM
        finally:
            CMAAdjustmentCalculator.AMENITY_PREMIUM.clear()
            CMAAdjustmentCalculator.AMENITY_PREMIUM.update(original)


# ---------------------------------------------------------------------------
# CMAAdjustmentCalculator — _get_location_key
# ---------------------------------------------------------------------------


class TestGetLocationKey:
    """Tests for _get_location_key helper."""

    def test_with_neighborhood(self):
        calc = CMAAdjustmentCalculator()
        prop = _make_property(city="Berlin", neighborhood="Prenzlauer Berg")
        assert calc._get_location_key(prop) == "berlin:prenzlauer berg"

    def test_with_district_no_neighborhood(self):
        calc = CMAAdjustmentCalculator()
        prop = _make_property(city="Berlin", district="Mitte", neighborhood=None)
        assert calc._get_location_key(prop) == "berlin:mitte"

    def test_with_city_only(self):
        calc = CMAAdjustmentCalculator()
        prop = _make_property(city="Warsaw", district=None, neighborhood=None)
        assert calc._get_location_key(prop) == "warsaw"

    def test_neighborhood_takes_priority_over_district(self):
        calc = CMAAdjustmentCalculator()
        prop = _make_property(city="Berlin", district="Mitte", neighborhood="Prenzlauer Berg")
        # Neighborhood takes priority
        assert calc._get_location_key(prop) == "berlin:prenzlauer berg"


# ---------------------------------------------------------------------------
# CMAAdjustmentCalculator — _get_floor_type
# ---------------------------------------------------------------------------


class TestGetFloorType:
    """Tests for _get_floor_type helper."""

    def test_ground_floor_1(self):
        calc = CMAAdjustmentCalculator()
        assert calc._get_floor_type(1, 5) == "ground"

    def test_ground_floor_0(self):
        calc = CMAAdjustmentCalculator()
        assert calc._get_floor_type(0, 5) == "ground"

    def test_ground_floor_negative(self):
        calc = CMAAdjustmentCalculator()
        assert calc._get_floor_type(-1, 5) == "ground"

    def test_top_floor(self):
        calc = CMAAdjustmentCalculator()
        assert calc._get_floor_type(5, 5) == "top"

    def test_top_floor_above_total(self):
        calc = CMAAdjustmentCalculator()
        assert calc._get_floor_type(6, 5) == "top"

    def test_middle_floor(self):
        calc = CMAAdjustmentCalculator()
        assert calc._get_floor_type(3, 5) == "middle"

    def test_none_floor(self):
        calc = CMAAdjustmentCalculator()
        assert calc._get_floor_type(None, 5) == "middle"

    def test_none_total_floors(self):
        calc = CMAAdjustmentCalculator()
        # Floor 3 with total_floors None -> not top, so middle
        assert calc._get_floor_type(3, None) == "middle"

    def test_floor_2_with_total_5(self):
        calc = CMAAdjustmentCalculator()
        assert calc._get_floor_type(2, 5) == "middle"


# ---------------------------------------------------------------------------
# CMAAdjustmentCalculator — _adjust_location
# ---------------------------------------------------------------------------


class TestAdjustLocation:
    """Tests for _adjust_location method."""

    def test_returns_none_when_no_indices(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property()
        comp = _make_property()
        result = calc._adjust_location(subject, comp, 300000.0)
        assert result is None

    def test_returns_none_when_same_index(self):
        calc = CMAAdjustmentCalculator(location_price_indices={"berlin:mitte": 1.0})
        subject = _make_property(city="Berlin", district="Mitte", neighborhood=None)
        comp = _make_property(city="Berlin", district="Mitte", neighborhood=None)
        result = calc._adjust_location(subject, comp, 300000.0)
        assert result is None

    def test_comp_in_pricier_area(self):
        calc = CMAAdjustmentCalculator(
            location_price_indices={"berlin:mitte": 1.0, "berlin:kreuzberg": 1.2}
        )
        subject = _make_property(city="Berlin", district="Mitte", neighborhood=None)
        comp = _make_property(city="Berlin", district="Kreuzberg", neighborhood=None)
        result = calc._adjust_location(subject, comp, 300000.0)
        assert result is not None
        assert result.category == "location"
        # Comp is 20% pricier: adjustment_percent = (1.2-1.0)/1.0 = 0.2, capped at 0.15
        # negated: -0.15
        assert result.adjustment_percent < 0

    def test_comp_in_cheaper_area(self):
        calc = CMAAdjustmentCalculator(
            location_price_indices={"berlin:mitte": 1.2, "berlin:kreuzberg": 0.8}
        )
        subject = _make_property(city="Berlin", district="Mitte", neighborhood=None)
        comp = _make_property(city="Berlin", district="Kreuzberg", neighborhood=None)
        result = calc._adjust_location(subject, comp, 300000.0)
        assert result is not None
        # Comp is cheaper: (0.8-1.2)/1.2 = -0.333, capped at -0.15, negated: +0.15
        assert result.adjustment_percent > 0

    def test_capped_at_15_percent(self):
        calc = CMAAdjustmentCalculator(
            location_price_indices={"berlin:mitte": 1.0, "berlin:luxury": 2.0}
        )
        subject = _make_property(city="Berlin", district="Mitte", neighborhood=None)
        comp = _make_property(city="Berlin", district="Luxury", neighborhood=None)
        result = calc._adjust_location(subject, comp, 300000.0)
        assert result is not None
        # (2.0-1.0)/1.0 = 1.0, capped at 0.15, negated = -0.15
        assert result.adjustment_percent >= -0.15

    def test_unknown_location_defaults_to_1(self):
        calc = CMAAdjustmentCalculator(location_price_indices={"berlin:mitte": 1.1})
        subject = _make_property(city="Berlin", district="Mitte", neighborhood=None)
        comp = _make_property(city="Berlin", district="Unknown", neighborhood=None)
        result = calc._adjust_location(subject, comp, 300000.0)
        assert result is not None
        # comp_index=1.0, subject_index=1.1 -> diff=-0.1/1.1, negated
        assert result.confidence == 0.7

    def test_confidence_0_7_with_indices(self):
        calc = CMAAdjustmentCalculator(
            location_price_indices={"berlin:mitte": 1.0, "berlin:kreuzberg": 1.1}
        )
        subject = _make_property(city="Berlin", district="Mitte", neighborhood=None)
        comp = _make_property(city="Berlin", district="Kreuzberg", neighborhood=None)
        result = calc._adjust_location(subject, comp, 300000.0)
        assert result.confidence == 0.7


# ---------------------------------------------------------------------------
# CMAAdjustmentCalculator — _adjust_size
# ---------------------------------------------------------------------------


class TestAdjustSize:
    """Tests for _adjust_size method."""

    def test_returns_none_when_subject_area_missing(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(area_sqm=None)
        comp = _make_property(area_sqm=100.0)
        assert calc._adjust_size(subject, comp, 300000.0) is None

    def test_returns_none_when_comp_area_missing(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(area_sqm=80.0)
        comp = _make_property(area_sqm=None)
        assert calc._adjust_size(subject, comp, 300000.0) is None

    def test_returns_none_when_subject_area_zero(self):
        """Source code checks area_sqm <= 0, but Property model requires gt=0.
        Use object.__setattr__ to bypass Pydantic validation."""
        calc = CMAAdjustmentCalculator()
        subject = _make_property(area_sqm=1.0)
        object.__setattr__(subject, "area_sqm", 0.0)
        comp = _make_property(area_sqm=100.0)
        assert calc._adjust_size(subject, comp, 300000.0) is None

    def test_returns_none_when_comp_area_zero(self):
        """Source code checks area_sqm <= 0, but Property model requires gt=0.
        Use object.__setattr__ to bypass Pydantic validation."""
        calc = CMAAdjustmentCalculator()
        subject = _make_property(area_sqm=80.0)
        comp = _make_property(area_sqm=1.0)
        object.__setattr__(comp, "area_sqm", 0.0)
        assert calc._adjust_size(subject, comp, 300000.0) is None

    def test_returns_none_within_5_percent(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(area_sqm=100.0)
        comp = _make_property(area_sqm=103.0)  # 3% difference < 5%
        assert calc._adjust_size(subject, comp, 300000.0) is None

    def test_comp_larger_negative_adjustment(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(area_sqm=80.0)
        comp = _make_property(area_sqm=120.0)  # 50% larger
        result = calc._adjust_size(subject, comp, 300000.0)
        assert result is not None
        assert result.category == "size"
        # comp is 50% larger -> size_diff_percent = 0.5
        # adjustment = -0.5 * 0.003/0.01 = -0.15, capped at -0.10
        assert result.adjustment_percent < 0

    def test_comp_smaller_positive_adjustment(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(area_sqm=120.0)
        comp = _make_property(area_sqm=80.0)  # 33% smaller
        result = calc._adjust_size(subject, comp, 300000.0)
        assert result is not None
        assert result.adjustment_percent > 0

    def test_size_adjustment_capped_at_10_percent(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(area_sqm=50.0)
        comp = _make_property(area_sqm=200.0)  # 300% larger
        result = calc._adjust_size(subject, comp, 300000.0)
        assert result is not None
        assert result.adjustment_percent >= -0.10

    def test_exact_boundary_5_percent(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(area_sqm=100.0)
        comp = _make_property(area_sqm=105.0)  # exactly 5%
        result = calc._adjust_size(subject, comp, 300000.0)
        # abs(0.05) < 0.05 is False, so adjustment IS returned
        assert result is not None

    def test_just_under_5_percent(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(area_sqm=100.0)
        comp = _make_property(area_sqm=104.9)
        result = calc._adjust_size(subject, comp, 300000.0)
        assert result is None

    def test_adjustment_amount_matches(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(area_sqm=80.0)
        comp = _make_property(area_sqm=100.0)  # 25% larger
        result = calc._adjust_size(subject, comp, 300000.0)
        assert result is not None
        expected_amount = round(300000.0 * result.adjustment_percent, 2)
        assert result.adjustment_amount == expected_amount


# ---------------------------------------------------------------------------
# CMAAdjustmentCalculator — _adjust_age
# ---------------------------------------------------------------------------


class TestAdjustAge:
    """Tests for _adjust_age method."""

    def test_returns_none_when_subject_year_missing(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(year_built=None)
        comp = _make_property(year_built=2010)
        assert calc._adjust_age(subject, comp, 300000.0) is None

    def test_returns_none_when_comp_year_missing(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(year_built=2000)
        comp = _make_property(year_built=None)
        assert calc._adjust_age(subject, comp, 300000.0) is None

    def test_returns_none_when_same_year(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(year_built=2000)
        comp = _make_property(year_built=2000)
        assert calc._adjust_age(subject, comp, 300000.0) is None

    def test_returns_none_within_2_years(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(year_built=2000)
        comp = _make_property(year_built=2002)
        assert calc._adjust_age(subject, comp, 300000.0) is None

    def test_comp_newer_positive_adjustment(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(year_built=1990)
        comp = _make_property(year_built=2010)
        result = calc._adjust_age(subject, comp, 300000.0)
        assert result is not None
        assert result.category == "age"
        # age_diff = 2010 - 1990 = 20
        # adjustment = -20 * 0.005 = -0.10 (comp is newer -> negative adjustment)
        assert result.adjustment_percent < 0

    def test_comp_older_negative_adjustment(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(year_built=2010)
        comp = _make_property(year_built=1990)
        result = calc._adjust_age(subject, comp, 300000.0)
        assert result is not None
        # age_diff = 1990 - 2010 = -20
        # adjustment = -(-20) * 0.005 = +0.10 (comp is older -> positive adjustment)
        assert result.adjustment_percent > 0

    def test_age_adjustment_capped_at_max(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(year_built=1950)
        comp = _make_property(year_built=2020)
        result = calc._adjust_age(subject, comp, 300000.0)
        assert result is not None
        # age_diff = 70 -> -70*0.005 = -0.35, capped at -0.20
        assert result.adjustment_percent >= -0.20

    def test_exact_boundary_3_years(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(year_built=2000)
        comp = _make_property(year_built=2003)
        result = calc._adjust_age(subject, comp, 300000.0)
        assert result is not None

    def test_confidence_0_7(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(year_built=1990)
        comp = _make_property(year_built=2010)
        result = calc._adjust_age(subject, comp, 300000.0)
        assert result.confidence == 0.7


# ---------------------------------------------------------------------------
# CMAAdjustmentCalculator — _adjust_condition
# ---------------------------------------------------------------------------


class TestAdjustCondition:
    """Tests for _adjust_condition method."""

    def test_returns_none_when_same_rating(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(energy_rating="B")
        comp = _make_property(energy_rating="B")
        assert calc._adjust_condition(subject, comp, 300000.0) is None

    def test_returns_none_when_both_default_d(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(energy_rating=None)
        comp = _make_property(energy_rating=None)
        assert calc._adjust_condition(subject, comp, 300000.0) is None

    def test_comp_better_rating(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(energy_rating="D")
        comp = _make_property(energy_rating="A")
        result = calc._adjust_condition(subject, comp, 300000.0)
        assert result is not None
        assert result.category == "condition"
        # comp_premium=0.10, subject_premium=0.00
        # adjustment = -(0.10 - 0.00) = -0.10
        assert result.adjustment_percent < 0

    def test_comp_worse_rating(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(energy_rating="A")
        comp = _make_property(energy_rating="F")
        result = calc._adjust_condition(subject, comp, 300000.0)
        assert result is not None
        # comp_premium=-0.06, subject_premium=0.10
        # adjustment = -(-0.06 - 0.10) = 0.16
        assert result.adjustment_percent > 0

    def test_none_rating_defaults_to_d(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(energy_rating=None)
        comp = _make_property(energy_rating="A")
        result = calc._adjust_condition(subject, comp, 300000.0)
        assert result is not None
        # subject default D -> 0.00, comp A -> 0.10
        # adjustment = -(0.10 - 0.00) = -0.10
        assert result.adjustment_percent < 0

    def test_unknown_rating_defaults_to_0(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(energy_rating="D")
        comp = _make_property(energy_rating="Z")
        result = calc._adjust_condition(subject, comp, 300000.0)
        # Z not in ENERGY_PREMIUM -> 0.0, D -> 0.0, same premium => None
        assert result is None

    def test_confidence_0_6(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(energy_rating="C")
        comp = _make_property(energy_rating="A")
        result = calc._adjust_condition(subject, comp, 300000.0)
        assert result is not None
        assert result.confidence == 0.6

    def test_case_insensitive_rating(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(energy_rating="a")
        comp = _make_property(energy_rating="f")
        result = calc._adjust_condition(subject, comp, 300000.0)
        assert result is not None
        # subject "A" -> 0.10, comp "F" -> -0.06
        # adjustment = -(-0.06 - 0.10) = 0.16
        assert result.adjustment_percent > 0


# ---------------------------------------------------------------------------
# CMAAdjustmentCalculator — _adjust_amenities
# ---------------------------------------------------------------------------


class TestAdjustAmenities:
    """Tests for _adjust_amenities method."""

    def test_returns_empty_when_identical_amenities(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property()
        comp = _make_property()
        result = calc._adjust_amenities(subject, comp, 300000.0)
        assert result == []

    def test_comp_has_amenity_subject_does_not(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(has_parking=False)
        comp = _make_property(has_parking=True)
        result = calc._adjust_amenities(subject, comp, 300000.0)
        # Should find 1 adjustment for has_parking
        parking_adj = [a for a in result if "parking" in a.description]
        assert len(parking_adj) == 1
        assert parking_adj[0].adjustment_percent > 0  # positive adjustment
        assert parking_adj[0].comp_value == "Yes"
        assert parking_adj[0].subject_value == "No"

    def test_subject_has_amenity_comp_does_not(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(has_garden=True)
        comp = _make_property(has_garden=False)
        result = calc._adjust_amenities(subject, comp, 300000.0)
        garden_adj = [a for a in result if "garden" in a.description]
        assert len(garden_adj) == 1
        assert garden_adj[0].adjustment_percent < 0  # negative adjustment
        assert garden_adj[0].comp_value == "No"
        assert garden_adj[0].subject_value == "Yes"

    def test_multiple_amenity_differences(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(has_parking=True, has_garden=True)
        comp = _make_property(has_parking=False, has_garden=False, has_pool=True)
        result = calc._adjust_amenities(subject, comp, 300000.0)
        # 3 differences: parking, garden, pool
        assert len(result) == 3

    def test_amenity_description_format_comp_has(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(has_elevator=False)
        comp = _make_property(has_elevator=True)
        result = calc._adjust_amenities(subject, comp, 300000.0)
        elevator_adj = [a for a in result if "elevator" in a.description]
        assert len(elevator_adj) == 1
        assert "Comparable has" in elevator_adj[0].description
        assert "elevator" in elevator_adj[0].description

    def test_amenity_description_format_subject_has(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(is_furnished=True)
        comp = _make_property(is_furnished=False)
        result = calc._adjust_amenities(subject, comp, 300000.0)
        furnished_adj = [a for a in result if "furnished" in a.description]
        assert len(furnished_adj) == 1
        assert "Subject has" in furnished_adj[0].description

    def test_amenity_category(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(has_balcony=False)
        comp = _make_property(has_balcony=True)
        result = calc._adjust_amenities(subject, comp, 300000.0)
        assert all(a.category == "amenities" for a in result)

    def test_amenity_confidence_0_8(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(has_pool=False)
        comp = _make_property(has_pool=True)
        result = calc._adjust_amenities(subject, comp, 300000.0)
        pool_adj = [a for a in result if "pool" in a.description]
        assert len(pool_adj) == 1
        assert pool_adj[0].confidence == 0.8

    def test_amenity_adjustment_amount_calculation(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(has_parking=False)
        comp = _make_property(has_parking=True)
        result = calc._adjust_amenities(subject, comp, 300000.0)
        parking_adj = [a for a in result if "parking" in a.description][0]
        # adjustment_amount = comp_price * adjustment_percent
        expected_amount = round(300000.0 * parking_adj.adjustment_percent, 2)
        assert parking_adj.adjustment_amount == expected_amount

    def test_all_amenity_types(self):
        """Test all 8 amenity types produce adjustments when different."""
        calc = CMAAdjustmentCalculator()
        subject = _make_property(
            has_parking=False,
            has_garden=False,
            has_elevator=False,
            has_balcony=False,
            is_furnished=False,
            has_pool=False,
            has_garage=False,
            pets_allowed=False,
        )
        comp = _make_property(
            has_parking=True,
            has_garden=True,
            has_elevator=True,
            has_balcony=True,
            is_furnished=True,
            has_pool=True,
            has_garage=True,
            pets_allowed=True,
        )
        result = calc._adjust_amenities(subject, comp, 300000.0)
        assert len(result) == 8


# ---------------------------------------------------------------------------
# CMAAdjustmentCalculator — _adjust_floor
# ---------------------------------------------------------------------------


class TestAdjustFloor:
    """Tests for _adjust_floor method."""

    def test_returns_none_for_non_apartments(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(property_type=PropertyType.HOUSE, floor=1.0, total_floors=1.0)
        comp = _make_property(property_type=PropertyType.HOUSE, floor=1.0, total_floors=1.0)
        assert calc._adjust_floor(subject, comp, 300000.0) is None

    def test_returns_none_when_subject_floor_none(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(floor=None, total_floors=None)
        comp = _make_property(floor=3.0, total_floors=5.0)
        assert calc._adjust_floor(subject, comp, 300000.0) is None

    def test_returns_none_when_comp_floor_none(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(floor=3.0, total_floors=5.0)
        comp = _make_property(floor=None, total_floors=None)
        assert calc._adjust_floor(subject, comp, 300000.0) is None

    def test_returns_none_same_floor_type(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(floor=2.0, total_floors=5.0)
        comp = _make_property(floor=3.0, total_floors=5.0)
        # Both are "middle" -> no adjustment
        assert calc._adjust_floor(subject, comp, 300000.0) is None

    def test_comp_ground_subject_top(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(floor=5.0, total_floors=5.0)  # top
        comp = _make_property(floor=1.0, total_floors=5.0)  # ground
        result = calc._adjust_floor(subject, comp, 300000.0)
        assert result is not None
        assert result.category == "floor"
        # subject_adj = 0.02 (top), comp_adj = -0.03 (ground)
        # adjustment = -(-0.03 - 0.02) = 0.05
        assert result.adjustment_percent > 0

    def test_comp_top_subject_ground(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(floor=1.0, total_floors=5.0)  # ground
        comp = _make_property(floor=5.0, total_floors=5.0)  # top
        result = calc._adjust_floor(subject, comp, 300000.0)
        assert result is not None
        # subject_adj = -0.03 (ground), comp_adj = 0.02 (top)
        # adjustment = -(0.02 - (-0.03)) = -0.05
        assert result.adjustment_percent < 0

    def test_returns_none_small_adjustment(self):
        calc = CMAAdjustmentCalculator()
        # Both middle -> 0.00 - 0.00 = 0, abs < 0.005
        subject = _make_property(floor=2.0, total_floors=5.0)
        comp = _make_property(floor=3.0, total_floors=5.0)
        assert calc._adjust_floor(subject, comp, 300000.0) is None

    def test_confidence_0_6(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(floor=5.0, total_floors=5.0)
        comp = _make_property(floor=1.0, total_floors=5.0)
        result = calc._adjust_floor(subject, comp, 300000.0)
        assert result.confidence == 0.6

    def test_only_one_apartment(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(property_type=PropertyType.HOUSE, floor=1.0, total_floors=1.0)
        comp = _make_property(floor=3.0, total_floors=5.0)
        assert calc._adjust_floor(subject, comp, 300000.0) is None


# ---------------------------------------------------------------------------
# CMAAdjustmentCalculator — _adjust_market_conditions
# ---------------------------------------------------------------------------


class TestAdjustMarketConditions:
    """Tests for _adjust_market_conditions method."""

    def test_returns_none_when_no_listing_date(self):
        calc = CMAAdjustmentCalculator()
        comp = _make_property(scraped_at=None, last_updated=None)
        assert calc._adjust_market_conditions(comp, 300000.0) is None

    def test_returns_none_for_recent_listing(self):
        calc = CMAAdjustmentCalculator()
        comp = _make_property(scraped_at=datetime.now())
        assert calc._adjust_market_conditions(comp, 300000.0) is None

    def test_adjusts_for_old_listing(self):
        calc = CMAAdjustmentCalculator(market_price_trend=0.01)
        old_date = datetime.now() - timedelta(days=180)  # ~6 months
        comp = _make_property(scraped_at=old_date)
        result = calc._adjust_market_conditions(comp, 300000.0)
        assert result is not None
        assert result.category == "market"
        assert result.adjustment_percent != 0

    def test_rising_market_positive_adjustment(self):
        calc = CMAAdjustmentCalculator(market_price_trend=0.02)
        old_date = datetime.now() - timedelta(days=90)  # ~3 months
        comp = _make_property(scraped_at=old_date)
        result = calc._adjust_market_conditions(comp, 300000.0)
        assert result is not None
        assert result.adjustment_percent > 0

    def test_falling_market_negative_adjustment(self):
        calc = CMAAdjustmentCalculator(market_price_trend=-0.02)
        old_date = datetime.now() - timedelta(days=90)
        comp = _make_property(scraped_at=old_date)
        result = calc._adjust_market_conditions(comp, 300000.0)
        assert result is not None
        assert result.adjustment_percent < 0

    def test_zero_trend_no_adjustment(self):
        calc = CMAAdjustmentCalculator(market_price_trend=0.0)
        old_date = datetime.now() - timedelta(days=90)
        comp = _make_property(scraped_at=old_date)
        result = calc._adjust_market_conditions(comp, 300000.0)
        assert result is not None
        # Even though listing is old, trend is 0, so percent is 0
        assert result.adjustment_percent == 0.0

    def test_capped_at_10_percent(self):
        calc = CMAAdjustmentCalculator(market_price_trend=0.05)
        old_date = datetime.now() - timedelta(days=365)
        comp = _make_property(scraped_at=old_date)
        result = calc._adjust_market_conditions(comp, 300000.0)
        assert result is not None
        assert result.adjustment_percent <= 0.10

    def test_capped_at_minus_10_percent(self):
        calc = CMAAdjustmentCalculator(market_price_trend=-0.05)
        old_date = datetime.now() - timedelta(days=365)
        comp = _make_property(scraped_at=old_date)
        result = calc._adjust_market_conditions(comp, 300000.0)
        assert result is not None
        assert result.adjustment_percent >= -0.10

    def test_uses_last_updated_fallback(self):
        calc = CMAAdjustmentCalculator(market_price_trend=0.02)
        old_date = datetime.now() - timedelta(days=90)
        comp = _make_property(scraped_at=None, last_updated=old_date)
        result = calc._adjust_market_conditions(comp, 300000.0)
        assert result is not None

    def test_timezone_aware_datetime(self):
        calc = CMAAdjustmentCalculator(market_price_trend=0.02)
        from datetime import timezone

        old_date = datetime.now(timezone.utc) - timedelta(days=90)
        comp = _make_property(scraped_at=old_date)
        result = calc._adjust_market_conditions(comp, 300000.0)
        assert result is not None

    def test_confidence_0_5(self):
        calc = CMAAdjustmentCalculator(market_price_trend=0.01)
        old_date = datetime.now() - timedelta(days=90)
        comp = _make_property(scraped_at=old_date)
        result = calc._adjust_market_conditions(comp, 300000.0)
        assert result.confidence == 0.5

    def test_description_contains_months(self):
        calc = CMAAdjustmentCalculator(market_price_trend=0.01)
        old_date = datetime.now() - timedelta(days=90)
        comp = _make_property(scraped_at=old_date)
        result = calc._adjust_market_conditions(comp, 300000.0)
        assert "months" in result.description


# ---------------------------------------------------------------------------
# CMAAdjustmentCalculator — calculate_adjustments (integration)
# ---------------------------------------------------------------------------


class TestCalculateAdjustments:
    """Tests for the full calculate_adjustments method."""

    def test_returns_list(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property()
        comp = _make_property()
        result = calc.calculate_adjustments(subject, comp, 300000.0)
        assert isinstance(result, list)

    def test_minimal_adjustments_similar_properties(self):
        calc = CMAAdjustmentCalculator()
        subject = _make_property(area_sqm=80.0, year_built=2005, energy_rating="C")
        comp = _make_property(area_sqm=82.0, year_built=2005, energy_rating="C")
        result = calc.calculate_adjustments(subject, comp, 300000.0)
        # Size within 5%, same year, same energy, no amenity diffs -> very few adjustments
        assert isinstance(result, list)

    def test_many_adjustments_different_properties(self):
        calc = CMAAdjustmentCalculator(
            market_price_trend=0.02,
            location_price_indices={"berlin:mitte": 1.0, "berlin:kreuzberg": 1.1},
        )
        subject = _make_property(
            district="Mitte",
            neighborhood=None,
            area_sqm=80.0,
            year_built=2005,
            energy_rating="A",
            has_parking=True,
            has_garden=True,
            floor=5.0,
            total_floors=5.0,
        )
        comp = _make_property(
            district="Kreuzberg",
            neighborhood=None,
            area_sqm=120.0,
            year_built=1990,
            energy_rating="F",
            has_parking=False,
            has_garden=False,
            floor=1.0,
            total_floors=5.0,
            scraped_at=datetime.now() - timedelta(days=90),
        )
        result = calc.calculate_adjustments(subject, comp, 300000.0)
        # Should have location, size, age, condition, amenities (2x), floor, market
        categories = [a.category for a in result]
        assert "location" in categories
        assert "size" in categories
        assert "age" in categories
        assert "condition" in categories
        assert "amenities" in categories
        assert "floor" in categories
        assert "market" in categories

    def test_no_market_adjustment_for_recent_listing(self):
        calc = CMAAdjustmentCalculator(market_price_trend=0.02)
        subject = _make_property()
        comp = _make_property(scraped_at=datetime.now())
        result = calc.calculate_adjustments(subject, comp, 300000.0)
        market_adj = [a for a in result if a.category == "market"]
        assert len(market_adj) == 0


# ---------------------------------------------------------------------------
# CMAAdjustmentCalculator — apply_adjustments
# ---------------------------------------------------------------------------


class TestApplyAdjustments:
    """Tests for the apply_adjustments method."""

    def test_no_adjustments(self):
        calc = CMAAdjustmentCalculator()
        result = calc.apply_adjustments(300000.0, [])
        assert result.original_price == 300000.0
        assert result.adjusted_price == 300000.0
        assert result.total_adjustment_percent == 0.0
        assert result.total_adjustment_amount == 0.0
        assert result.net_adjustment == 0.0

    def test_single_positive_adjustment(self):
        calc = CMAAdjustmentCalculator()
        adj = CMAAdjustment(
            category="size",
            description="Size diff",
            subject_value="80",
            comp_value="60",
            adjustment_percent=0.06,
            adjustment_amount=18000.0,
        )
        result = calc.apply_adjustments(300000.0, [adj])
        assert result.adjusted_price == 300000.0 * 1.06
        assert result.net_adjustment > 0
        assert result.total_adjustment_percent == 6.0

    def test_single_negative_adjustment(self):
        calc = CMAAdjustmentCalculator()
        adj = CMAAdjustment(
            category="size",
            description="Size diff",
            subject_value="80",
            comp_value="100",
            adjustment_percent=-0.06,
            adjustment_amount=-18000.0,
        )
        result = calc.apply_adjustments(300000.0, [adj])
        assert result.adjusted_price == 300000.0 * 0.94
        assert result.net_adjustment < 0

    def test_multiple_adjustments_cumulative(self):
        calc = CMAAdjustmentCalculator()
        adj1 = CMAAdjustment(
            category="size",
            description="Size",
            subject_value="80",
            comp_value="100",
            adjustment_percent=0.03,
            adjustment_amount=9000.0,
        )
        adj2 = CMAAdjustment(
            category="age",
            description="Age",
            subject_value="2000",
            comp_value="2010",
            adjustment_percent=-0.05,
            adjustment_amount=-15000.0,
        )
        result = calc.apply_adjustments(300000.0, [adj1, adj2])
        expected_percent = 0.03 + (-0.05)  # = -0.02
        expected_price = 300000.0 * (1 + expected_percent)
        assert result.adjusted_price == round(expected_price, 2)

    def test_capped_at_30_percent_positive(self):
        calc = CMAAdjustmentCalculator()
        adj = CMAAdjustment(
            category="test",
            description="Big adj",
            subject_value="a",
            comp_value="b",
            adjustment_percent=0.50,
            adjustment_amount=150000.0,
        )
        result = calc.apply_adjustments(300000.0, [adj])
        # Total percent capped at 0.30
        assert result.adjusted_price == 300000.0 * 1.30

    def test_capped_at_30_percent_negative(self):
        calc = CMAAdjustmentCalculator()
        adj = CMAAdjustment(
            category="test",
            description="Big adj",
            subject_value="a",
            comp_value="b",
            adjustment_percent=-0.50,
            adjustment_amount=-150000.0,
        )
        result = calc.apply_adjustments(300000.0, [adj])
        assert result.adjusted_price == 300000.0 * 0.70

    def test_total_adjustment_percent_in_percentage(self):
        calc = CMAAdjustmentCalculator()
        adj = CMAAdjustment(
            category="test",
            description="adj",
            subject_value="a",
            comp_value="b",
            adjustment_percent=0.10,
            adjustment_amount=30000.0,
        )
        result = calc.apply_adjustments(300000.0, [adj])
        # 0.10 * 100 = 10.0 percent
        assert result.total_adjustment_percent == 10.0

    def test_property_id_is_empty_by_default(self):
        calc = CMAAdjustmentCalculator()
        result = calc.apply_adjustments(300000.0, [])
        assert result.property_id == ""

    def test_values_are_rounded(self):
        calc = CMAAdjustmentCalculator()
        adj = CMAAdjustment(
            category="test",
            description="adj",
            subject_value="a",
            comp_value="b",
            adjustment_percent=0.033,
            adjustment_amount=10000.0,
        )
        result = calc.apply_adjustments(300000.0, [adj])
        assert result.total_adjustment_amount == 10000.0


# ---------------------------------------------------------------------------
# calculate_cma_adjustments convenience function
# ---------------------------------------------------------------------------


class TestCalculateCmaAdjustmentsFunction:
    """Tests for the module-level convenience function."""

    def test_returns_adjusted_comparable(self):
        subject = _make_property()
        comp = _make_property(id="comp-1")
        result = calculate_cma_adjustments(subject, comp, 300000.0)
        assert isinstance(result, AdjustedComparable)
        assert result.property_id == "comp-1"

    def test_uses_comparable_id(self):
        subject = _make_property()
        comp = _make_property(id="special-id")
        result = calculate_cma_adjustments(subject, comp, 300000.0)
        assert result.property_id == "special-id"

    def test_empty_id_when_none(self):
        subject = _make_property()
        comp = _make_property(id=None)
        result = calculate_cma_adjustments(subject, comp, 300000.0)
        assert result.property_id == ""

    def test_passes_market_trend(self):
        subject = _make_property()
        comp = _make_property(scraped_at=datetime.now() - timedelta(days=90))
        result = calculate_cma_adjustments(subject, comp, 300000.0, market_trend=0.05)
        market_adj = [a for a in result.adjustments if a.category == "market"]
        assert len(market_adj) == 1

    def test_passes_location_indices(self):
        subject = _make_property(city="Berlin", district="Mitte", neighborhood=None)
        comp = _make_property(city="Berlin", district="Kreuzberg", neighborhood=None)
        result = calculate_cma_adjustments(
            subject,
            comp,
            300000.0,
            location_indices={"berlin:mitte": 1.0, "berlin:kreuzberg": 1.2},
        )
        location_adj = [a for a in result.adjustments if a.category == "location"]
        assert len(location_adj) == 1

    def test_original_price_matches_comp_price(self):
        subject = _make_property()
        comp = _make_property()
        result = calculate_cma_adjustments(subject, comp, 350000.0)
        assert result.original_price == 350000.0
