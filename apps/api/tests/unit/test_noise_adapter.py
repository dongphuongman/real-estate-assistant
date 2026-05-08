"""Tests for noise adapter."""

from unittest.mock import MagicMock, patch

from data.adapters.noise_adapter import (
    NoiseAdapter,
    NoiseResult,
    NoiseSource,
    get_noise_adapter,
)


class TestNoiseSource:
    def test_create_source(self):
        source = NoiseSource(
            id="road_1",
            type="road",
            name="Highway A1",
            latitude=52.0,
            longitude=21.0,
            distance_m=150.0,
            severity=0.8,
        )
        assert source.id == "road_1"
        assert source.severity == 0.8

    def test_to_dict(self):
        source = NoiseSource(
            id="road_1",
            type="road",
            name="Test Road",
            latitude=52.0,
            longitude=21.0,
            distance_m=150.5,
            severity=0.75,
            tags={"highway": "primary"},
        )
        d = source.to_dict()
        assert d["id"] == "road_1"
        assert d["type"] == "road"
        assert d["distance_m"] == 150.5
        assert d["severity"] == 0.75
        assert "tags" not in d


class TestNoiseResult:
    def test_create_result(self):
        result = NoiseResult(
            score=75.0,
            estimated_db=55.0,
            noise_sources=[],
            data_source="overpass_api",
            confidence=0.8,
            query_latitude=52.0,
            query_longitude=21.0,
        )
        assert result.score == 75.0

    def test_to_dict(self):
        result = NoiseResult(
            score=75.5,
            estimated_db=55.3,
            noise_sources=[],
            data_source="overpass_api",
            confidence=0.85,
            query_latitude=52.0,
            query_longitude=21.0,
        )
        d = result.to_dict()
        assert d["score"] == 75.5
        assert d["estimated_db"] == 55.3
        assert d["noise_sources"] == []


class TestNoiseAdapterInit:
    def test_init_default(self):
        adapter = NoiseAdapter()
        assert adapter._api_url == adapter.DEFAULT_API_URL
        assert adapter._timeout == 30

    def test_init_custom_url(self):
        adapter = NoiseAdapter(api_url="https://custom.api/interpreter")
        assert adapter._api_url == "https://custom.api/interpreter"

    @patch.dict("os.environ", {"OVERPASS_API_URL": "https://env.api/interpreter"})
    def test_init_from_env(self):
        adapter = NoiseAdapter()
        assert adapter._api_url == "https://env.api/interpreter"


class TestExtractCoordinates:
    def setup_method(self):
        self.adapter = NoiseAdapter()

    def test_node_element(self):
        element = {"lat": 52.0, "lon": 21.0}
        coords = self.adapter._extract_coordinates(element)
        assert coords == {"lat": 52.0, "lon": 21.0}

    def test_way_element_with_center(self):
        element = {"center": {"lat": 52.0, "lon": 21.0}}
        coords = self.adapter._extract_coordinates(element)
        assert coords == {"lat": 52.0, "lon": 21.0}

    def test_no_coordinates(self):
        element = {"id": 123}
        coords = self.adapter._extract_coordinates(element)
        assert coords is None


class TestQueryRoads:
    @patch("data.adapters.noise_adapter.requests.get")
    def test_query_roads_success(self, mock_get):
        adapter = NoiseAdapter()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": 1,
                    "center": {"lat": 52.0, "lon": 21.0},
                    "tags": {"highway": "motorway", "name": "A1"},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        sources = adapter._query_roads(52.0, 21.0, 500)
        assert len(sources) == 1
        assert sources[0].type == "road"
        assert sources[0].severity == 1.0

    @patch("data.adapters.noise_adapter.requests.get")
    def test_query_roads_request_error(self, mock_get):
        import requests

        adapter = NoiseAdapter()
        mock_get.side_effect = requests.RequestException("error")
        sources = adapter._query_roads(52.0, 21.0, 500)
        assert sources == []

    @patch("data.adapters.noise_adapter.requests.get")
    def test_query_roads_no_highway_tag(self, mock_get):
        adapter = NoiseAdapter()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": 1,
                    "center": {"lat": 52.0, "lon": 21.0},
                    "tags": {"name": "Some Way"},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        sources = adapter._query_roads(52.0, 21.0, 500)
        assert sources == []

    @patch("data.adapters.noise_adapter.requests.get")
    def test_query_roads_no_coords(self, mock_get):
        adapter = NoiseAdapter()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {"id": 1, "tags": {"highway": "primary"}},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        sources = adapter._query_roads(52.0, 21.0, 500)
        assert sources == []


class TestQueryRailways:
    @patch("data.adapters.noise_adapter.requests.get")
    def test_query_railways_success(self, mock_get):
        adapter = NoiseAdapter()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": 10,
                    "center": {"lat": 52.0, "lon": 21.0},
                    "tags": {"railway": "rail", "name": "Main Line"},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        sources = adapter._query_railways(52.0, 21.0, 500)
        assert len(sources) == 1
        assert sources[0].type == "railway"
        assert sources[0].severity == 0.9

    @patch("data.adapters.noise_adapter.requests.get")
    def test_query_railways_no_tags(self, mock_get):
        adapter = NoiseAdapter()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [{"id": 10, "tags": {}}],
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        sources = adapter._query_railways(52.0, 21.0, 500)
        assert sources == []

    @patch("data.adapters.noise_adapter.requests.get")
    def test_query_railways_error(self, mock_get):
        import requests

        adapter = NoiseAdapter()
        mock_get.side_effect = requests.RequestException("error")
        sources = adapter._query_railways(52.0, 21.0, 500)
        assert sources == []


class TestQueryAirports:
    @patch("data.adapters.noise_adapter.requests.get")
    def test_query_airports_success(self, mock_get):
        adapter = NoiseAdapter()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": 20,
                    "center": {"lat": 52.0, "lon": 21.0},
                    "tags": {"aeroway": "aerodrome", "name": "Test Airport"},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        sources = adapter._query_airports(52.0, 21.0)
        assert len(sources) == 1
        assert sources[0].type == "airport"
        assert sources[0].severity == 1.0

    @patch("data.adapters.noise_adapter.requests.get")
    def test_query_airports_no_coords(self, mock_get):
        adapter = NoiseAdapter()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [{"id": 20, "tags": {"aeroway": "aerodrome"}}],
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        sources = adapter._query_airports(52.0, 21.0)
        assert sources == []

    @patch("data.adapters.noise_adapter.requests.get")
    def test_query_airports_error(self, mock_get):
        import requests

        adapter = NoiseAdapter()
        mock_get.side_effect = requests.RequestException("error")
        sources = adapter._query_airports(52.0, 21.0)
        assert sources == []


class TestQueryIndustrial:
    @patch("data.adapters.noise_adapter.requests.get")
    def test_query_industrial_success(self, mock_get):
        adapter = NoiseAdapter()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": 30,
                    "center": {"lat": 52.0, "lon": 21.0},
                    "tags": {"landuse": "industrial", "name": "Factory"},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        sources = adapter._query_industrial(52.0, 21.0, 500)
        assert len(sources) == 1
        assert sources[0].type == "industrial"
        assert sources[0].severity == 0.5

    @patch("data.adapters.noise_adapter.requests.get")
    def test_query_industrial_error(self, mock_get):
        import requests

        adapter = NoiseAdapter()
        mock_get.side_effect = requests.RequestException("error")
        sources = adapter._query_industrial(52.0, 21.0, 500)
        assert sources == []


class TestGetNearbyNoiseSources:
    @patch.object(NoiseAdapter, "_query_roads")
    @patch.object(NoiseAdapter, "_query_railways")
    @patch.object(NoiseAdapter, "_query_airports")
    @patch.object(NoiseAdapter, "_query_industrial")
    def test_combined_sources_sorted(
        self, mock_industrial, mock_airports, mock_railways, mock_roads
    ):
        adapter = NoiseAdapter()
        road = NoiseSource(
            id="r1",
            type="road",
            name="R",
            latitude=52.0,
            longitude=21.0,
            distance_m=200.0,
            severity=0.6,
        )
        rail = NoiseSource(
            id="ra1",
            type="railway",
            name="Ra",
            latitude=52.0,
            longitude=21.0,
            distance_m=50.0,
            severity=0.9,
        )
        mock_roads.return_value = [road]
        mock_railways.return_value = [rail]
        mock_airports.return_value = []
        mock_industrial.return_value = []

        sources = adapter.get_nearby_noise_sources(52.0, 21.0)
        assert len(sources) == 2
        assert sources[0].distance_m <= sources[1].distance_m


class TestCalculateNoiseScore:
    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_no_sources(self, mock_sources):
        adapter = NoiseAdapter()
        mock_sources.return_value = []
        score = adapter.calculate_noise_score(52.0, 21.0)
        assert score == 95.0

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_major_road_near(self, mock_sources):
        adapter = NoiseAdapter()
        mock_sources.return_value = [
            NoiseSource(
                id="r1",
                type="road",
                name="Motorway",
                latitude=52.0,
                longitude=21.0,
                distance_m=50.0,
                severity=1.0,
            ),
        ]
        score = adapter.calculate_noise_score(52.0, 21.0)
        assert score < 95.0
        assert score >= 0

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_major_road_medium_distance(self, mock_sources):
        adapter = NoiseAdapter()
        mock_sources.return_value = [
            NoiseSource(
                id="r1",
                type="road",
                name="Trunk",
                latitude=52.0,
                longitude=21.0,
                distance_m=150.0,
                severity=0.8,
            ),
        ]
        score = adapter.calculate_noise_score(52.0, 21.0)
        assert score < 95.0

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_minor_road_near(self, mock_sources):
        adapter = NoiseAdapter()
        mock_sources.return_value = [
            NoiseSource(
                id="r1",
                type="road",
                name="Secondary",
                latitude=52.0,
                longitude=21.0,
                distance_m=80.0,
                severity=0.4,
            ),
        ]
        score = adapter.calculate_noise_score(52.0, 21.0)
        assert score < 95.0

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_minor_road_far(self, mock_sources):
        adapter = NoiseAdapter()
        mock_sources.return_value = [
            NoiseSource(
                id="r1",
                type="road",
                name="Secondary",
                latitude=52.0,
                longitude=21.0,
                distance_m=300.0,
                severity=0.4,
            ),
        ]
        score = adapter.calculate_noise_score(52.0, 21.0)
        assert score < 95.0

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_railway_near(self, mock_sources):
        adapter = NoiseAdapter()
        mock_sources.return_value = [
            NoiseSource(
                id="ra1",
                type="railway",
                name="Rail",
                latitude=52.0,
                longitude=21.0,
                distance_m=100.0,
                severity=0.9,
            ),
        ]
        score = adapter.calculate_noise_score(52.0, 21.0)
        assert score < 95.0

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_airport_near(self, mock_sources):
        adapter = NoiseAdapter()
        mock_sources.return_value = [
            NoiseSource(
                id="a1",
                type="airport",
                name="Airport",
                latitude=52.0,
                longitude=21.0,
                distance_m=1000.0,
                severity=1.0,
            ),
        ]
        score = adapter.calculate_noise_score(52.0, 21.0)
        assert score < 95.0

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_industrial_near(self, mock_sources):
        adapter = NoiseAdapter()
        mock_sources.return_value = [
            NoiseSource(
                id="i1",
                type="industrial",
                name="Factory",
                latitude=52.0,
                longitude=21.0,
                distance_m=300.0,
                severity=0.5,
            ),
        ]
        score = adapter.calculate_noise_score(52.0, 21.0)
        assert score < 95.0


class TestEstimateDecibels:
    def setup_method(self):
        self.adapter = NoiseAdapter()

    def test_no_sources(self):
        db = self.adapter._estimate_decibels([])
        assert db == 40.0

    def test_road_source(self):
        source = NoiseSource(
            id="r1",
            type="road",
            name="R",
            latitude=52.0,
            longitude=21.0,
            distance_m=200.0,
            severity=0.8,
        )
        db = self.adapter._estimate_decibels([source])
        assert db > 40.0

    def test_airport_source_boosted(self):
        source = NoiseSource(
            id="a1",
            type="airport",
            name="A",
            latitude=52.0,
            longitude=21.0,
            distance_m=200.0,
            severity=1.0,
        )
        db = self.adapter._estimate_decibels([source])
        assert db > 40.0

    def test_railway_source_boosted(self):
        source = NoiseSource(
            id="ra1",
            type="railway",
            name="R",
            latitude=52.0,
            longitude=21.0,
            distance_m=200.0,
            severity=0.9,
        )
        db = self.adapter._estimate_decibels([source])
        assert db > 40.0

    def test_clamped_max(self):
        sources = [
            NoiseSource(
                id=f"s{i}",
                type="road",
                name=f"S{i}",
                latitude=52.0,
                longitude=21.0,
                distance_m=10.0,
                severity=1.0,
            )
            for i in range(20)
        ]
        db = self.adapter._estimate_decibels(sources)
        assert db <= 80.0


class TestCalculateConfidence:
    def setup_method(self):
        self.adapter = NoiseAdapter()

    def test_no_sources(self):
        conf = self.adapter._calculate_confidence([])
        assert conf == 0.5

    def test_with_named_sources(self):
        sources = [
            NoiseSource(
                id="1",
                type="road",
                name="Named Road",
                latitude=52.0,
                longitude=21.0,
                distance_m=100.0,
                severity=0.8,
            ),
        ]
        conf = self.adapter._calculate_confidence(sources)
        assert conf >= 0.5

    def test_with_unnamed_sources(self):
        sources = [
            NoiseSource(
                id="1",
                type="road",
                name=None,
                latitude=52.0,
                longitude=21.0,
                distance_m=100.0,
                severity=0.8,
            ),
        ]
        conf = self.adapter._calculate_confidence(sources)
        assert conf > 0.3


class TestEstimateNoiseLevel:
    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    @patch.object(NoiseAdapter, "calculate_noise_score")
    def test_success(self, mock_score, mock_sources):
        adapter = NoiseAdapter()
        mock_sources.return_value = []
        mock_score.return_value = 90.0

        result = adapter.estimate_noise_level(52.0, 21.0)
        assert isinstance(result, NoiseResult)
        assert result.score == 90.0
        assert result.query_latitude == 52.0

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    @patch.object(NoiseAdapter, "calculate_noise_score")
    def test_error_fallback(self, mock_score, mock_sources):
        adapter = NoiseAdapter()
        mock_sources.side_effect = Exception("error")

        result = adapter.estimate_noise_level(52.0, 21.0)
        assert result.score == 50.0
        assert result.confidence == 0.0


class TestDistance:
    def setup_method(self):
        self.adapter = NoiseAdapter()

    def test_same_point(self):
        dist = self.adapter._calculate_distance(52.0, 21.0, 52.0, 21.0)
        assert dist == 0.0

    def test_known_distance(self):
        dist = self.adapter._calculate_distance(52.0, 21.0, 52.01, 21.01)
        assert dist > 0


class TestGetRoadRailwayNames:
    def setup_method(self):
        self.adapter = NoiseAdapter()

    def test_road_name(self):
        assert self.adapter._get_road_name({"name": "Main Road"}) == "Main Road"

    def test_road_ref(self):
        assert self.adapter._get_road_name({"ref": "A1"}) == "A1"

    def test_road_no_name(self):
        assert self.adapter._get_road_name({}) is None

    def test_railway_name(self):
        assert self.adapter._get_railway_name({"name": "Express"}) == "Express"

    def test_railway_type(self):
        assert self.adapter._get_railway_name({"railway": "rail"}) == "rail"


class TestGetAdapter:
    def test_get_adapter_creates_instance(self):
        import data.adapters.noise_adapter as mod

        original = mod._default_adapter
        mod._default_adapter = None
        try:
            adapter = get_noise_adapter()
            assert isinstance(adapter, NoiseAdapter)
        finally:
            mod._default_adapter = original

    def test_get_adapter_same_instance(self):
        import data.adapters.noise_adapter as mod

        original = mod._default_adapter
        mod._default_adapter = None
        try:
            a1 = get_noise_adapter()
            a2 = get_noise_adapter()
            assert a1 is a2
        finally:
            mod._default_adapter = original
