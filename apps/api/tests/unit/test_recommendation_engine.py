from langchain_core.documents import Document

from agents.recommendation_engine import PropertyRecommendationEngine
from data.schemas import UserPreferences


def _make_doc(doc_id: str, **metadata_overrides) -> Document:
    """Helper to create a Document with sensible defaults."""
    meta = {
        "id": doc_id,
        "price": 300000,
        "rooms": 3.0,
        "city": "Warsaw",
        "property_type": "apartment",
        "price_per_sqm": 25,
    }
    meta.update(metadata_overrides)
    return Document(page_content="Property", metadata=meta)


# ---------------------------------------------------------------------------
# Original tests (updated signatures)
# ---------------------------------------------------------------------------


def test_recommend_returns_empty_for_no_documents():
    engine = PropertyRecommendationEngine()
    assert engine.recommend([]) == []


def test_recommend_ranks_and_limits_k():
    engine = PropertyRecommendationEngine()
    docs = [
        Document(page_content="Nice apartment", metadata={"id": "1", "price_per_sqm": 50}),
        Document(
            page_content="Great value apartment" * 30,
            metadata={
                "id": "2",
                "price_per_sqm": 15,
                "has_parking": True,
                "has_garden": True,
                "has_balcony": True,
            },
        ),
    ]

    ranked = engine.recommend(docs, k=1)
    assert len(ranked) == 1
    assert ranked[0][0].metadata["id"] == "2"
    assert ranked[0][2]["premium_amenities"] is True


def test_explicit_score_matches_city_case_insensitive_and_rooms_float():
    engine = PropertyRecommendationEngine()
    prefs = UserPreferences(
        user_id="u1",
        budget_range=(0, 1000),
        preferred_cities=["Krakow"],
        preferred_rooms=[2.0],
        must_have_amenities=["has_parking"],
        preferred_neighborhoods=["Old Town"],
    )

    doc = Document(
        page_content="Apartment",
        metadata={
            "id": "p1",
            "price": 950,
            "city": "KRAKOW",
            "rooms": 2.0,
            "has_parking": True,
            "neighborhood": "old town",
            "price_per_sqm": 25,
        },
    )

    score, explanation = engine._score_property(
        doc, prefs, documents=[doc], viewed_properties=None, favorited_properties=None
    )
    assert score > 0
    assert "preference_match" in explanation
    assert explanation["why_recommended"]


def test_generate_reason_defaults_when_no_signals():
    engine = PropertyRecommendationEngine()
    reason = engine._generate_recommendation_reason(
        explicit_score=0.0,
        value_score=0.0,
        implicit_score=0.0,
        metadata={},
    )
    assert reason == "Good match for your search"


# ---------------------------------------------------------------------------
# TestExtractReferenceProperties
# ---------------------------------------------------------------------------


class TestExtractReferenceProperties:
    def test_extracts_matching_documents(self):
        engine = PropertyRecommendationEngine()
        docs = [_make_doc("a1", city="Warsaw"), _make_doc("a2", city="Krakow")]
        result = engine._extract_reference_properties(docs, ["a1"])
        assert len(result) == 1
        assert result[0]["city"] == "Warsaw"

    def test_returns_empty_for_no_matches(self):
        engine = PropertyRecommendationEngine()
        docs = [_make_doc("a1")]
        result = engine._extract_reference_properties(docs, ["zzz"])
        assert result == []

    def test_handles_empty_ids_list(self):
        engine = PropertyRecommendationEngine()
        docs = [_make_doc("a1")]
        result = engine._extract_reference_properties(docs, [])
        assert result == []

    def test_handles_id_type_coercion(self):
        engine = PropertyRecommendationEngine()
        doc = Document(page_content="P", metadata={"id": 42, "city": "Berlin"})
        result = engine._extract_reference_properties([doc], ["42"])
        assert len(result) == 1

    def test_extracts_multiple_matches(self):
        engine = PropertyRecommendationEngine()
        docs = [_make_doc("a1"), _make_doc("a2"), _make_doc("a3")]
        result = engine._extract_reference_properties(docs, ["a1", "a3"])
        assert len(result) == 2


# ---------------------------------------------------------------------------
# TestCalculateFeatureSimilarity
# ---------------------------------------------------------------------------


class TestCalculateFeatureSimilarity:
    def test_perfect_match_returns_high_score(self):
        engine = PropertyRecommendationEngine()
        meta = {
            "city": "Warsaw",
            "rooms": 3,
            "price": 500000,
            "property_type": "apartment",
            "has_parking": True,
        }
        score = engine._calculate_feature_similarity(meta, dict(meta))
        assert score == 1.0

    def test_no_match_returns_low_score(self):
        engine = PropertyRecommendationEngine()
        candidate = {"city": "Warsaw", "rooms": 3, "price": 500000, "property_type": "apartment"}
        reference = {"city": "Krakow", "rooms": 1, "price": 100000, "property_type": "house"}
        score = engine._calculate_feature_similarity(candidate, reference)
        # City=0, rooms=(1-2)/5=0.2, price=(1-400k/100k)=0, type=0, amenities=1.0 (empty sets)
        assert score < 0.5

    def test_partial_city_and_rooms_match(self):
        engine = PropertyRecommendationEngine()
        candidate = {"city": "Warsaw", "rooms": 3, "price": 500000, "property_type": "house"}
        reference = {"city": "Warsaw", "rooms": 3, "price": 200000, "property_type": "apartment"}
        score = engine._calculate_feature_similarity(candidate, reference)
        # city=1, rooms=1, price=(1-300k/200k)=0, type=0, amenities=1.0
        expected = 0.25 * 1.0 + 0.20 * 1.0 + 0.20 * 0.0 + 0.15 * 0.0 + 0.20 * 1.0
        assert abs(score - expected) < 0.01

    def test_amenity_jaccard_with_empty_sets(self):
        engine = PropertyRecommendationEngine()
        # Both have no amenities → Jaccard returns 1.0
        candidate = {"city": "X", "rooms": 2, "price": 100, "property_type": "apt"}
        reference = {"city": "X", "rooms": 2, "price": 100, "property_type": "apt"}
        score = engine._calculate_feature_similarity(candidate, reference)
        assert score == 1.0

    def test_amenity_partial_overlap(self):
        engine = PropertyRecommendationEngine()
        candidate = {
            "city": "X",
            "rooms": 2,
            "price": 100,
            "property_type": "apt",
            "has_parking": True,
            "has_garden": True,
        }
        reference = {
            "city": "X",
            "rooms": 2,
            "price": 100,
            "property_type": "apt",
            "has_parking": True,
            "has_elevator": True,
        }
        # intersection={has_parking}=1, union={has_parking,has_garden,has_elevator}=3 → 1/3
        score = engine._calculate_feature_similarity(candidate, reference)
        amenity_part = 1 / 3
        expected = 0.25 + 0.20 + 0.20 + 0.15 + 0.20 * amenity_part
        assert abs(score - expected) < 0.01

    def test_missing_rooms_and_price_defaults_to_half(self):
        engine = PropertyRecommendationEngine()
        candidate = {"city": "X"}
        reference = {"city": "X"}
        score = engine._calculate_feature_similarity(candidate, reference)
        # city=1, rooms=0.5, price=0.5, type=""=="")=1.0, amenities=1.0 (empty)
        assert score > 0.7


# ---------------------------------------------------------------------------
# TestCalculateImplicitScore
# ---------------------------------------------------------------------------


class TestCalculateImplicitScore:
    def test_returns_neutral_without_reference_properties(self):
        engine = PropertyRecommendationEngine()
        docs = [_make_doc("a1")]
        score = engine._calculate_implicit_score(
            docs[0].metadata, docs, viewed_properties=None, favorited_properties=None
        )
        assert score == 0.5

    def test_returns_higher_for_favorite_match(self):
        engine = PropertyRecommendationEngine()
        fav = _make_doc("fav1", city="Warsaw", rooms=3, price=500000, property_type="apartment")
        candidate_meta = {
            "city": "Warsaw",
            "rooms": 3,
            "price": 500000,
            "property_type": "apartment",
        }
        score = engine._calculate_implicit_score(
            candidate_meta, [fav], viewed_properties=None, favorited_properties=["fav1"]
        )
        assert score > 0.5

    def test_returns_moderate_for_viewed_match(self):
        engine = PropertyRecommendationEngine()
        viewed = _make_doc("v1", city="Warsaw", rooms=3, price=500000, property_type="apartment")
        candidate_meta = {
            "city": "Warsaw",
            "rooms": 3,
            "price": 500000,
            "property_type": "apartment",
        }
        score = engine._calculate_implicit_score(
            candidate_meta, [viewed], viewed_properties=["v1"], favorited_properties=None
        )
        assert score > 0.5

    def test_favorites_weighted_more_than_views(self):
        engine = PropertyRecommendationEngine()
        ref = _make_doc("r1", city="Warsaw", rooms=3, price=500000, property_type="apartment")
        candidate_meta = {
            "city": "Warsaw",
            "rooms": 3,
            "price": 500000,
            "property_type": "apartment",
        }

        engine._calculate_implicit_score(
            candidate_meta, [ref], viewed_properties=["r1"], favorited_properties=None
        )
        engine._calculate_implicit_score(
            candidate_meta, [ref], viewed_properties=None, favorited_properties=["r1"]
        )
        # Both get same similarity, but favorite has 2x weight — same score since only 1 ref
        # With a dissimilar candidate though:
        diff_meta = {"city": "Gdansk", "rooms": 1, "price": 100000, "property_type": "house"}

        score_view_diff = engine._calculate_implicit_score(
            diff_meta, [ref], viewed_properties=["r1"], favorited_properties=None
        )
        # Multiple refs with mixed signals:
        viewed2 = _make_doc("v2", city="Gdansk", rooms=1, price=100000, property_type="house")
        score_mixed = engine._calculate_implicit_score(
            diff_meta, [ref, viewed2], viewed_properties=["r1"], favorited_properties=["v2"]
        )
        # v2 is similar and favorite (2x weight), r1 is dissimilar and viewed (1x)
        assert score_mixed > score_view_diff

    def test_handles_empty_documents_list(self):
        engine = PropertyRecommendationEngine()
        score = engine._calculate_implicit_score(
            {"city": "X"}, [], viewed_properties=["a1"], favorited_properties=None
        )
        assert score == 0.5

    def test_ids_not_in_pool_returns_neutral(self):
        engine = PropertyRecommendationEngine()
        docs = [_make_doc("a1")]
        score = engine._calculate_implicit_score(
            docs[0].metadata, docs, viewed_properties=["nonexistent"], favorited_properties=None
        )
        assert score == 0.5


# ---------------------------------------------------------------------------
# TestRecommendIntegration
# ---------------------------------------------------------------------------


class TestRecommendIntegration:
    def test_recommended_properties_scored_by_similarity(self):
        engine = PropertyRecommendationEngine()

        # Favorited property: cheap Warsaw apartment
        fav = _make_doc(
            "fav1",
            city="Warsaw",
            rooms=2,
            price=200000,
            property_type="apartment",
            price_per_sqm=15,
        )

        # Candidate A: similar to favorite
        similar = _make_doc(
            "c1",
            city="Warsaw",
            rooms=2,
            price=210000,
            property_type="apartment",
            price_per_sqm=14,
            has_parking=True,
            has_balcony=True,
        )

        # Candidate B: completely different
        different = _make_doc(
            "c2", city="Krakow", rooms=5, price=900000, property_type="house", price_per_sqm=40
        )

        ranked = engine.recommend(
            [fav, similar, different],
            favorited_properties=["fav1"],
        )

        # Similar candidate should rank higher than different one
        ids = [r[0].metadata["id"] for r in ranked]
        assert ids.index("c1") < ids.index("c2")

    def test_mixed_viewed_and_favorited(self):
        engine = PropertyRecommendationEngine()

        viewed = _make_doc(
            "v1", city="Warsaw", rooms=3, price=300000, property_type="apartment", price_per_sqm=20
        )
        fav = _make_doc(
            "f1", city="Krakow", rooms=2, price=200000, property_type="apartment", price_per_sqm=18
        )
        candidate_krakow = _make_doc(
            "c1", city="Krakow", rooms=2, price=220000, property_type="apartment", price_per_sqm=19
        )
        candidate_warsaw = _make_doc(
            "c2", city="Warsaw", rooms=3, price=310000, property_type="apartment", price_per_sqm=21
        )

        # Pass all docs so reference extraction can find v1/f1 by ID
        ranked = engine.recommend(
            [viewed, fav, candidate_krakow, candidate_warsaw],
            viewed_properties=["v1"],
            favorited_properties=["f1"],
        )

        # c1 matches favorite (Krakow, 2x weight) → should rank above c2
        scores = {r[0].metadata["id"]: r[1] for r in ranked}
        assert scores["c1"] > scores["c2"]

    def test_no_preference_data_uses_neutral_scores(self):
        engine = PropertyRecommendationEngine()

        docs = [
            _make_doc("a", price_per_sqm=10),
            _make_doc("b", price_per_sqm=50),
        ]

        ranked = engine.recommend(docs)
        assert len(ranked) == 2
        # Both should have valid scores
        for _doc, score, explanation in ranked:
            assert score > 0
            assert "recommendation_score" in explanation
