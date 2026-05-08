"""Tests for transport adapter."""

from unittest.mock import MagicMock, patch

from data.adapters.transport_adapter import (
    TransportAdapter,
    TransportResult,
    TransportStop,
    get_transport_adapter,
)


class TestTransportStop:
    def test_create_stop(self):
        stop = TransportStop(
            id="123",
            name="Bus Stop A",
            type="bus",
            latitude=52.2297,
            longitude=21.0122,
            distance_m=150.0,
        )
        assert stop.id == "123"
        assert stop.type == "bus"
        assert stop.distance_m == 150.0

    def test_create_stop_no_distance(self):
        stop = TransportStop(
            id="456",
            name=None,
            type="tram",
            latitude=52.0,
            longitude=21.0,
        )
        assert stop.distance_m is None


class TestTransportAdapterInit:
    def test_init_default(self):
        adapter = TransportAdapter()
        assert adapter._api_url == adapter.DEFAULT_API_URL
        assert adapter._timeout == 30

    def test_init_custom_url(self):
        adapter = TransportAdapter(api_url="https://custom.api/interpreter")
        assert adapter._api_url == "https://custom.api/interpreter"

    @patch.dict("os.environ", {"OVERPASS_API_URL": "https://env.api/interpreter"})
    def test_init_from_env(self):
        adapter = TransportAdapter()
        assert adapter._api_url == "https://env.api/interpreter"


class TestDetermineTransportType:
    def setup_method(self):
        self.adapter = TransportAdapter()

    def test_bus_stop(self):
        result = self.adapter._determine_transport_type({"highway": "bus_stop"})
        assert result == "bus"

    def test_tram_stop(self):
        result = self.adapter._determine_transport_type({"railway": "tram_stop"})
        assert result == "tram"

    def test_metro(self):
        result = self.adapter._determine_transport_type({"railway": "subway_entrance"})
        assert result == "metro"

    def test_train(self):
        result = self.adapter._determine_transport_type({"railway": "station"})
        assert result == "train"

    def test_light_rail(self):
        result = self.adapter._determine_transport_type({"railway": "light_rail"})
        assert result == "light_rail"

    def test_public_transport_bus(self):
        result = self.adapter._determine_transport_type(
            {"public_transport": "stop_position", "bus": "yes"}
        )
        assert result == "bus"

    def test_public_transport_tram(self):
        result = self.adapter._determine_transport_type(
            {"public_transport": "platform", "tram": "yes"}
        )
        assert result == "tram"

    def test_public_transport_subway(self):
        result = self.adapter._determine_transport_type(
            {"public_transport": "platform", "subway": "yes"}
        )
        assert result == "metro"

    def test_public_transport_train(self):
        result = self.adapter._determine_transport_type(
            {"public_transport": "platform", "train": "yes"}
        )
        assert result == "train"

    def test_public_transport_default_bus(self):
        result = self.adapter._determine_transport_type({"public_transport": "stop_position"})
        assert result == "bus"

    def test_public_transport_platform_default_bus(self):
        result = self.adapter._determine_transport_type({"public_transport": "platform"})
        assert result == "bus"

    def test_unknown_tags_default_bus(self):
        result = self.adapter._determine_transport_type({"foo": "bar"})
        assert result == "bus"


class TestParseTransportStop:
    def setup_method(self):
        self.adapter = TransportAdapter()

    def test_parse_node_element(self):
        element = {
            "id": 123,
            "lat": 52.23,
            "lon": 21.01,
            "tags": {"highway": "bus_stop", "name": "Test Stop"},
        }
        stop = self.adapter._parse_transport_stop(element, 52.2297, 21.0122)
        assert stop is not None
        assert stop.name == "Test Stop"
        assert stop.type == "bus"
        assert stop.distance_m is not None

    def test_parse_way_with_center(self):
        element = {
            "id": 456,
            "center": {"lat": 52.23, "lon": 21.01},
            "tags": {"railway": "tram_stop", "name": "Tram Stop"},
        }
        stop = self.adapter._parse_transport_stop(element, 52.2297, 21.0122)
        assert stop is not None
        assert stop.type == "tram"

    def test_parse_no_tags(self):
        element = {"id": 789, "lat": 52.23, "lon": 21.01}
        stop = self.adapter._parse_transport_stop(element, 52.2297, 21.0122)
        assert stop is None

    def test_parse_no_coordinates(self):
        element = {"id": 999, "tags": {"highway": "bus_stop"}}
        stop = self.adapter._parse_transport_stop(element, 52.2297, 21.0122)
        assert stop is None

    def test_parse_ref_as_name(self):
        element = {
            "id": 111,
            "lat": 52.23,
            "lon": 21.01,
            "tags": {"highway": "bus_stop", "ref": "B12"},
        }
        stop = self.adapter._parse_transport_stop(element, 52.2297, 21.0122)
        assert stop is not None
        assert stop.name == "B12"


class TestFetchTransportPOIs:
    @patch("data.adapters.transport_adapter.requests.get")
    def test_fetch_success(self, mock_get):
        adapter = TransportAdapter()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": 1,
                    "lat": 52.23,
                    "lon": 21.01,
                    "tags": {"highway": "bus_stop", "name": "Stop 1"},
                },
                {
                    "id": 2,
                    "lat": 52.24,
                    "lon": 21.02,
                    "tags": {"railway": "tram_stop", "name": "Tram 1"},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        stops = adapter.fetch_transport_pois(52.2297, 21.0122, 500)
        assert len(stops) == 2

    @patch("data.adapters.transport_adapter.requests.get")
    def test_fetch_request_error(self, mock_get):
        import requests

        adapter = TransportAdapter()
        mock_get.side_effect = requests.RequestException("error")

        stops = adapter.fetch_transport_pois(52.2297, 21.0122)
        assert stops == []

    @patch("data.adapters.transport_adapter.requests.get")
    def test_fetch_parse_error(self, mock_get):
        adapter = TransportAdapter()
        mock_response = MagicMock()
        mock_response.json.side_effect = Exception("parse error")
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        stops = adapter.fetch_transport_pois(52.2297, 21.0122)
        assert stops == []

    @patch("data.adapters.transport_adapter.requests.get")
    def test_fetch_empty_elements(self, mock_get):
        adapter = TransportAdapter()
        mock_response = MagicMock()
        mock_response.json.return_value = {"elements": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        stops = adapter.fetch_transport_pois(52.2297, 21.0122)
        assert stops == []


class TestCountStops:
    @patch.object(TransportAdapter, "fetch_transport_pois")
    def test_count_stops(self, mock_fetch):
        adapter = TransportAdapter()
        mock_fetch.return_value = [
            TransportStop(id="1", name="S1", type="bus", latitude=52.0, longitude=21.0),
            TransportStop(id="2", name="S2", type="bus", latitude=52.0, longitude=21.0),
        ]
        count = adapter.count_stops(52.2297, 21.0122)
        assert count == 2

    @patch.object(TransportAdapter, "fetch_transport_pois")
    def test_count_no_stops(self, mock_fetch):
        adapter = TransportAdapter()
        mock_fetch.return_value = []
        count = adapter.count_stops(52.2297, 21.0122)
        assert count == 0


class TestGetStopTypes:
    @patch.object(TransportAdapter, "fetch_transport_pois")
    def test_stop_types(self, mock_fetch):
        adapter = TransportAdapter()
        mock_fetch.return_value = [
            TransportStop(id="1", name="S1", type="bus", latitude=52.0, longitude=21.0),
            TransportStop(id="2", name="S2", type="tram", latitude=52.0, longitude=21.0),
            TransportStop(id="3", name="S3", type="bus", latitude=52.0, longitude=21.0),
        ]
        types = adapter.get_stop_types(52.2297, 21.0122)
        assert types["bus"] == 2
        assert types["tram"] == 1
        assert types["metro"] == 0


class TestCalculateAccessibilityScore:
    @patch.object(TransportAdapter, "fetch_transport_pois")
    @patch.object(TransportAdapter, "get_stop_types")
    def test_no_stops_baseline(self, mock_types, mock_fetch):
        adapter = TransportAdapter()
        mock_fetch.return_value = []
        mock_types.return_value = {"bus": 0, "tram": 0, "metro": 0, "train": 0, "light_rail": 0}
        score = adapter.calculate_accessibility_score(52.0, 21.0)
        assert score == 20.0

    @patch.object(TransportAdapter, "fetch_transport_pois")
    @patch.object(TransportAdapter, "get_stop_types")
    def test_many_stops(self, mock_types, mock_fetch):
        adapter = TransportAdapter()
        mock_fetch.return_value = [MagicMock() for _ in range(15)]
        mock_types.return_value = {"bus": 10, "tram": 3, "metro": 2, "train": 0, "light_rail": 0}
        score = adapter.calculate_accessibility_score(52.0, 21.0)
        assert score > 80.0


class TestGetFullResult:
    @patch.object(TransportAdapter, "fetch_transport_pois")
    @patch.object(TransportAdapter, "get_stop_types")
    @patch.object(TransportAdapter, "calculate_accessibility_score")
    def test_full_result(self, mock_score, mock_types, mock_fetch):
        adapter = TransportAdapter()
        stops = [
            TransportStop(
                id="1",
                name="Bus A",
                type="bus",
                latitude=52.0,
                longitude=21.0,
                distance_m=100.0,
            ),
        ]
        mock_fetch.return_value = stops
        mock_types.return_value = {"bus": 1, "tram": 0, "metro": 0, "train": 0, "light_rail": 0}
        mock_score.return_value = 45.0

        result = adapter.get_full_result(52.0, 21.0)
        assert isinstance(result, TransportResult)
        assert result.score == 45.0
        assert result.total_stops == 1
        assert result.data_source == "overpass"


class TestBaseScore:
    def setup_method(self):
        self.adapter = TransportAdapter()

    def test_zero_stops(self):
        assert self.adapter._calculate_base_score(0) == 20.0

    def test_one_stop(self):
        assert self.adapter._calculate_base_score(1) == 40.0

    def test_three_stops(self):
        assert self.adapter._calculate_base_score(3) == 60.0

    def test_seven_stops(self):
        assert self.adapter._calculate_base_score(7) == 80.0

    def test_twelve_stops(self):
        assert self.adapter._calculate_base_score(12) == 95.0


class TestDiversityBonus:
    def setup_method(self):
        self.adapter = TransportAdapter()

    def test_one_type(self):
        assert self.adapter._calculate_diversity_bonus({"bus": 5}) == 0.0

    def test_two_types(self):
        assert self.adapter._calculate_diversity_bonus({"bus": 3, "tram": 2}) == 3.0

    def test_three_types(self):
        assert self.adapter._calculate_diversity_bonus({"bus": 1, "tram": 1, "metro": 1}) == 5.0


class TestCapacityBonus:
    def setup_method(self):
        self.adapter = TransportAdapter()

    def test_no_high_capacity(self):
        assert self.adapter._calculate_capacity_bonus({"bus": 5, "tram": 3}) == 0.0

    def test_metro(self):
        assert self.adapter._calculate_capacity_bonus({"metro": 1}) == 3.0

    def test_train(self):
        assert self.adapter._calculate_capacity_bonus({"train": 1}) == 2.0

    def test_light_rail(self):
        bonus = self.adapter._calculate_capacity_bonus({"light_rail": 1})
        assert bonus == 1.5

    def test_capped(self):
        bonus = self.adapter._calculate_capacity_bonus({"metro": 2, "train": 1, "light_rail": 1})
        assert bonus <= 5.0


class TestConfidence:
    def setup_method(self):
        self.adapter = TransportAdapter()

    def test_no_stops(self):
        assert self.adapter._calculate_confidence([], {"bus": 0}) == 0.5

    def test_named_stops(self):
        stops = [
            TransportStop(id="1", name="Named", type="bus", latitude=52.0, longitude=21.0),
            TransportStop(id="2", name=None, type="bus", latitude=52.0, longitude=21.0),
        ]
        types = {"bus": 2}
        conf = self.adapter._calculate_confidence(stops, types)
        assert conf > 0.5

    def test_diverse_types(self):
        stops = [
            TransportStop(id="1", name="S1", type="bus", latitude=52.0, longitude=21.0),
            TransportStop(id="2", name="S2", type="tram", latitude=52.0, longitude=21.0),
            TransportStop(id="3", name="S3", type="metro", latitude=52.0, longitude=21.0),
        ]
        types = {"bus": 1, "tram": 1, "metro": 1, "train": 0, "light_rail": 0}
        conf = self.adapter._calculate_confidence(stops, types)
        assert conf > 0.6


class TestBuildQuery:
    def test_build_query(self):
        adapter = TransportAdapter()
        query = adapter._build_transport_query(52.2297, 21.0122, 500)
        assert "bus_stop" in query
        assert "52.2297" in query
        assert "21.0122" in query
        assert "500" in query


class TestDistance:
    def setup_method(self):
        self.adapter = TransportAdapter()

    def test_same_point(self):
        dist = self.adapter._calculate_distance(52.0, 21.0, 52.0, 21.0)
        assert dist == 0.0

    def test_known_distance(self):
        dist = self.adapter._calculate_distance(52.2297, 21.0122, 52.2397, 21.0222)
        assert dist > 0
        assert dist < 2000


class TestGetAdapter:
    def test_get_adapter_creates_instance(self):
        import data.adapters.transport_adapter as mod

        original = mod._default_adapter
        mod._default_adapter = None
        try:
            adapter = get_transport_adapter()
            assert isinstance(adapter, TransportAdapter)
        finally:
            mod._default_adapter = original

    def test_get_adapter_same_instance(self):
        import data.adapters.transport_adapter as mod

        original = mod._default_adapter
        mod._default_adapter = None
        try:
            a1 = get_transport_adapter()
            a2 = get_transport_adapter()
            assert a1 is a2
        finally:
            mod._default_adapter = original
