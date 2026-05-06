"""Unit tests for comparable_selector module.

Tests the ComparableSelector class and scoring algorithm for Task #85.
"""

from datetime import datetime, timedelta

import pytest

from analytics.comparable_selector import (
    COMPATIBLE_TYPES,
    ComparableScore,
    ComparableSelector,
    find_best_comparables,
)
from data.schemas import ListingType, Property, PropertyCollection, PropertyType

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def subject_property() -> Property:
    """Create a subject property for testing."""
    return Property(
        id="subject-1",
        title="Subject Property",
        description=None,
        country="Germany",
        region="Berlin",
        city="Berlin",
        district="Mitte",
        neighborhood="Mitte-Mitte",
        address=None,
        latitude=52.5200,
        longitude=13.4050,
        property_type=PropertyType.APARTMENT,
        listing_type=ListingType.SALE,
        price=350000,
        currency=None,
        price_media=None,
        price_delta=None,
        deposit=None,
        negotiation_rate=None,
        area_sqm=85.0,
        rooms=3,
        bathrooms=1,
        floor=3,
        total_floors=5,
        year_built=2010,
        energy_rating="B",
        has_parking=True,
        has_garden=False,
        has_elevator=True,
        has_balcony=True,
        is_furnished=False,
        has_pool=False,
        has_garage=False,
        pets_allowed=True,
        distance_to_school=None,
        distance_to_clinic=None,
        distance_to_restaurant=None,
        distance_to_transport=None,
        distance_to_shopping=None,
        owner_name=None,
        owner_phone=None,
        owner_email=None,
        source_url=None,
        source_platform=None,
        price_per_sqm=None,
        price_in_eur=None,
        total_monthly_cost=None,
        scraped_at=datetime.now() - timedelta(days=10),
    )


@pytest.fixture
def similar_property() -> Property:
    """Create a similar property for testing (good comparable)."""
    return Property(
        id="comp-1",
        title="Similar Apartment",
        description=None,
        country="Germany",
        region="Berlin",
        city="Berlin",
        district="Mitte",
        neighborhood="Mitte-Mitte",
        address=None,
        latitude=52.5180,
        longitude=13.4100,
        property_type=PropertyType.APARTMENT,
        listing_type=ListingType.SALE,
        price=340000,
        currency=None,
        price_media=None,
        price_delta=None,
        deposit=None,
        negotiation_rate=None,
        area_sqm=82.0,
        rooms=3,
        bathrooms=1,
        floor=4,
        total_floors=5,
        year_built=2012,
        energy_rating="B",
        has_parking=True,
        has_garden=False,
        has_elevator=True,
        has_balcony=True,
        is_furnished=False,
        has_pool=False,
        has_garage=False,
        pets_allowed=True,
        distance_to_school=None,
        distance_to_clinic=None,
        distance_to_restaurant=None,
        distance_to_transport=None,
        distance_to_shopping=None,
        owner_name=None,
        owner_phone=None,
        owner_email=None,
        source_url=None,
        source_platform=None,
        price_per_sqm=None,
        price_in_eur=None,
        total_monthly_cost=None,
        scraped_at=datetime.now() - timedelta(days=15),
    )


@pytest.fixture
def different_property() -> Property:
    """Create a different property for testing (poor comparable)."""
    return Property(
        id="comp-2",
        title="Different Property",
        description=None,
        country="Germany",
        region="Berlin",
        city="Berlin",
        district="Steglitz",
        neighborhood="Steglitz-Zentrum",
        address=None,
        latitude=52.4550,
        longitude=13.3300,
        property_type=PropertyType.HOUSE,
        listing_type=ListingType.SALE,
        price=550000,
        currency=None,
        price_media=None,
        price_delta=None,
        deposit=None,
        negotiation_rate=None,
        area_sqm=150.0,
        rooms=6,
        bathrooms=2,
        floor=None,
        total_floors=2,
        year_built=1985,
        energy_rating="D",
        has_parking=True,
        has_garden=True,
        has_elevator=False,
        has_balcony=False,
        is_furnished=False,
        has_pool=True,
        has_garage=True,
        pets_allowed=True,
        distance_to_school=None,
        distance_to_clinic=None,
        distance_to_restaurant=None,
        distance_to_transport=None,
        distance_to_shopping=None,
        owner_name=None,
        owner_phone=None,
        owner_email=None,
        source_url=None,
        source_platform=None,
        price_per_sqm=None,
        price_in_eur=None,
        total_monthly_cost=None,
        scraped_at=datetime.now() - timedelta(days=120),
    )


@pytest.fixture
def property_collection(
    subject_property: Property,
    similar_property: Property,
    different_property: Property,
) -> PropertyCollection:
    """Create a property collection for testing."""
    return PropertyCollection(
        properties=[subject_property, similar_property, different_property],
        total_count=3,
        source_type="test",
    )


# ============================================================================
# ComparableScore Tests
# ============================================================================


class TestComparableScore:
    """Tests for ComparableScore dataclass."""

    def test_comparable_score_creation(self):
        """Test creating a ComparableScore instance."""
        score = ComparableScore(
            property_id="test-1",
            total_score=85.5,
            location_score=22.0,
            type_score=20.0,
            size_score=13.5,
            rooms_score=15.0,
            recency_score=10.0,
            amenities_score=5.0,
            distance_km=0.8,
            price_per_sqm=4000.0,
            price=340000.0,
        )

        assert score.property_id == "test-1"
        assert score.total_score == 85.5
        assert score.distance_km == 0.8

    def test_score_breakdown_populated(self):
        """Test that score_breakdown is populated in __post_init__."""
        score = ComparableScore(
            property_id="test-1",
            total_score=85.5,
            location_score=22.0,
            type_score=20.0,
            size_score=13.5,
            rooms_score=15.0,
            recency_score=10.0,
            amenities_score=5.0,
            distance_km=0.8,
            price_per_sqm=4000.0,
            price=340000.0,
        )

        assert score.score_breakdown == {
            "location": 22.0,
            "type": 20.0,
            "size": 13.5,
            "rooms": 15.0,
            "recency": 10.0,
            "amenities": 5.0,
        }


# ============================================================================
# Compatible Types Tests
# ============================================================================


class TestCompatibleTypes:
    """Tests for COMPATIBLE_TYPES mapping."""

    def test_apartment_compatible_types(self):
        """Test apartment compatible types."""
        assert PropertyType.STUDIO in COMPATIBLE_TYPES[PropertyType.APARTMENT]
        assert PropertyType.LOFT in COMPATIBLE_TYPES[PropertyType.APARTMENT]

    def test_house_compatible_types(self):
        """Test house compatible types."""
        assert PropertyType.TOWNHOUSE in COMPATIBLE_TYPES[PropertyType.HOUSE]

    def test_other_has_no_compatible_types(self):
        """Test OTHER has no compatible types."""
        assert len(COMPATIBLE_TYPES[PropertyType.OTHER]) == 0


# ============================================================================
# ComparableSelector Tests
# ============================================================================


class TestComparableSelector:
    """Tests for ComparableSelector class."""

    def test_selector_initialization(
        self,
        property_collection: PropertyCollection,
    ):
        """Test ComparableSelector initialization."""
        selector = ComparableSelector(property_collection)
        assert selector.properties == property_collection
        assert selector.market_insights is not None

    def test_find_comparables_basic(
        self,
        subject_property: Property,
        property_collection: PropertyCollection,
    ):
        """Test basic comparable finding."""
        selector = ComparableSelector(property_collection)
        scores = selector.find_comparables(
            subject=subject_property,
            max_results=10,
            min_score=0.0,
        )

        # Should find at least one comparable (the similar property)
        assert len(scores) >= 1

        # Similar property should have higher score than different property
        similar_scores = [s for s in scores if s.property_id == "comp-1"]
        different_scores = [s for s in scores if s.property_id == "comp-2"]

        if similar_scores and different_scores:
            assert similar_scores[0].total_score > different_scores[0].total_score

    def test_find_comparables_excludes_subject(
        self,
        subject_property: Property,
        property_collection: PropertyCollection,
    ):
        """Test that subject is excluded from results."""
        selector = ComparableSelector(property_collection)
        scores = selector.find_comparables(
            subject=subject_property,
            exclude_subject=True,
        )

        # Subject should not be in results
        subject_ids = [s.property_id for s in scores]
        assert subject_property.id not in subject_ids

    def test_find_comparables_min_score_filter(
        self,
        subject_property: Property,
        property_collection: PropertyCollection,
    ):
        """Test minimum score filtering."""
        selector = ComparableSelector(property_collection)
        scores = selector.find_comparables(
            subject=subject_property,
            min_score=70.0,
        )

        # All scores should be >= 70
        for score in scores:
            assert score.total_score >= 70.0

    def test_find_comparables_max_results(
        self,
        subject_property: Property,
        property_collection: PropertyCollection,
    ):
        """Test max_results limiting."""
        selector = ComparableSelector(property_collection)
        scores = selector.find_comparables(
            subject=subject_property,
            max_results=1,
        )

        assert len(scores) <= 1

    def test_score_location_geo_distance(
        self,
        subject_property: Property,
        similar_property: Property,
        property_collection: PropertyCollection,
    ):
        """Test location scoring with geo-distance."""
        selector = ComparableSelector(property_collection)

        # Similar property is close to subject
        score = selector._score_location(subject_property, similar_property)
        assert score > 15.0  # Should be high score for close property

    def test_score_type_exact_match(
        self,
        subject_property: Property,
        similar_property: Property,
        property_collection: PropertyCollection,
    ):
        """Test type scoring for exact match."""
        selector = ComparableSelector(property_collection)

        score = selector._score_type(subject_property, similar_property)
        assert score == 20.0  # Max score for exact match

    def test_score_type_different(
        self,
        subject_property: Property,
        different_property: Property,
        property_collection: PropertyCollection,
    ):
        """Test type scoring for different types."""
        selector = ComparableSelector(property_collection)

        score = selector._score_type(subject_property, different_property)
        assert score == 0.0  # No score for incompatible types

    def test_score_size_within_10_percent(
        self,
        subject_property: Property,
        similar_property: Property,
        property_collection: PropertyCollection,
    ):
        """Test size scoring when within 10%."""
        selector = ComparableSelector(property_collection)

        # subject: 85 sqm, similar: 82 sqm -> ~3.5% diff
        score = selector._score_size(subject_property, similar_property)
        assert score == 15.0  # Max score for < 10% diff

    def test_score_rooms_exact_match(
        self,
        subject_property: Property,
        similar_property: Property,
        property_collection: PropertyCollection,
    ):
        """Test room scoring for exact match."""
        selector = ComparableSelector(property_collection)

        score = selector._score_rooms(subject_property, similar_property)
        assert score == 15.0  # Max score for exact match

    def test_score_recency_recent(
        self,
        similar_property: Property,
        property_collection: PropertyCollection,
    ):
        """Test recency scoring for recent listing."""
        selector = ComparableSelector(property_collection)

        score = selector._score_recency(similar_property)
        assert score >= 10.0  # High score for recent listing

    def test_score_recency_old(
        self,
        different_property: Property,
        property_collection: PropertyCollection,
    ):
        """Test recency scoring for old listing."""
        selector = ComparableSelector(property_collection)

        score = selector._score_recency(different_property)
        assert score <= 5.0  # Low score for old listing

    def test_calculate_distance_km(
        self,
        property_collection: PropertyCollection,
    ):
        """Test Haversine distance calculation."""
        # Berlin Mitte to Berlin Steglitz is roughly 10-12 km
        distance = ComparableSelector._calculate_distance_km(
            lat1=52.5200,
            lon1=13.4050,  # Mitte
            lat2=52.4550,
            lon2=13.3300,  # Steglitz
        )

        # Should be approximately 8-10 km
        assert 6.0 < distance < 12.0


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_missing_coordinates_fallback(
        self,
        subject_property: Property,
        property_collection: PropertyCollection,
    ):
        """Test location scoring fallback when no coordinates."""
        subject_no_coords = subject_property.model_copy(
            update={"latitude": None, "longitude": None}
        )

        selector = ComparableSelector(property_collection)
        scores = selector.find_comparables(
            subject=subject_no_coords,
        )

        # Should still work with district fallback
        assert len(scores) >= 1

    def test_missing_area_sqm(
        self,
        subject_property: Property,
        similar_property: Property,
        property_collection: PropertyCollection,
    ):
        """Test size scoring when area is missing."""
        subject_no_area = subject_property.model_copy(update={"area_sqm": None})

        selector = ComparableSelector(property_collection)
        score = selector._score_size(subject_no_area, similar_property)

        # Should return neutral score
        assert score == 5.0

    def test_missing_rooms(
        self,
        subject_property: Property,
        similar_property: Property,
        property_collection: PropertyCollection,
    ):
        """Test room scoring when rooms is missing."""
        subject_no_rooms = subject_property.model_copy(update={"rooms": None})

        selector = ComparableSelector(property_collection)
        score = selector._score_rooms(subject_no_rooms, similar_property)

        # Should return neutral score
        assert score == 5.0

    def test_zero_area_sqm(
        self,
        subject_property: Property,
        similar_property: Property,
        property_collection: PropertyCollection,
    ):
        """Test size scoring when area is zero."""
        subject_zero_area = subject_property.model_copy(update={"area_sqm": 0})

        selector = ComparableSelector(property_collection)
        score = selector._score_size(subject_zero_area, similar_property)

        # Should return neutral score
        assert score == 5.0


# ============================================================================
# Test Convenience Function
# ============================================================================


class TestFindBestComparables:
    """Tests for find_best_comparables convenience function."""

    def test_find_best_returns_results(
        self,
        subject_property: Property,
        similar_property: Property,
        property_collection: PropertyCollection,
    ):
        """Test that find_best_comparables returns results."""
        results = find_best_comparables(
            properties=property_collection,
            subject=subject_property,
            max_results=5,
        )

        assert len(results) >= 1
        # First result should be the similar property (highest score)
        assert results[0].property_id == similar_property.id
