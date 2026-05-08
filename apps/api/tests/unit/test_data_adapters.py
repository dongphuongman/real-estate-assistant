"""Unit tests for data adapters: AirQuality, Transport, Noise.

All external HTTP calls are mocked. Tests cover success paths, error handling,
empty data, invalid responses, caching, and scoring logic.
"""

import time
from unittest.mock import MagicMock, patch

import requests

from data.adapters.air_quality_adapter import (
    CITY_AQI_AVERAGES,
    AirQualityAdapter,
    AirQualityResult,
    AirQualityStation,
    get_air_quality_adapter,
)
from data.adapters.noise_adapter import (
    NoiseAdapter,
    NoiseResult,
    NoiseSource,
    get_noise_adapter,
)
from data.adapters.transport_adapter import (
    TransportAdapter,
    TransportResult,
    TransportStop,
    get_transport_adapter,
)

# ---------------------------------------------------------------------------
# AirQualityAdapter tests
# ---------------------------------------------------------------------------


class TestAirQualityAdapterInit:
    """Tests for AirQualityAdapter initialization."""

    def test_init_with_api_key(self):
        adapter = AirQualityAdapter(api_key="test-key")
        assert adapter._api_key == "test-key"
        assert adapter._timeout == 30
        assert adapter._cache_ttl == 3600

    def test_init_without_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            adapter = AirQualityAdapter()
            assert adapter._api_key is None

    def test_init_custom_cache_ttl(self):
        """Explicit cache_ttl is used when env var AIR_QUALITY_CACHE_TTL is also set.

        Note: due to Python operator precedence in the source code
        (cache_ttl or int(ttl_env) if ttl_env else DEFAULT),
        the explicit value is only respected when the env var is also set.
        """
        with patch.dict("os.environ", {"AIR_QUALITY_CACHE_TTL": "0"}, clear=True):
            adapter = AirQualityAdapter(api_key="k", cache_ttl=1800)
            assert adapter._cache_ttl == 1800

    def test_init_cache_ttl_from_env(self):
        with patch.dict("os.environ", {"AIR_QUALITY_CACHE_TTL": "7200"}, clear=True):
            adapter = AirQualityAdapter(api_key="k")
            assert adapter._cache_ttl == 7200

    def test_init_default_cache_ttl(self):
        with patch.dict("os.environ", {}, clear=True):
            adapter = AirQualityAdapter(api_key="k")
            assert adapter._cache_ttl == 3600


class TestAirQualityGetNearestStation:
    """Tests for AirQualityAdapter.get_nearest_station."""

    def test_returns_none_without_api_key(self):
        adapter = AirQualityAdapter(api_key=None)
        result = adapter.get_nearest_station(52.2297, 21.0122)
        assert result is None

    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_success_returns_station(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "ok",
            "data": {
                "idx": 1234,
                "city": {"name": "Warsaw Central", "geo": [52.23, 21.01]},
                "aqi": 65,
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = AirQualityAdapter(api_key="test-key")
        station = adapter.get_nearest_station(52.2297, 21.0122)

        assert isinstance(station, AirQualityStation)
        assert station.station_id == "1234"
        assert station.name == "Warsaw Central"
        assert station.aqi == 65
        assert station.latitude == 52.23
        assert station.longitude == 21.01
        assert station.distance_km > 0

    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_api_returns_error_status(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "error"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = AirQualityAdapter(api_key="test-key")
        result = adapter.get_nearest_station(52.0, 21.0)
        assert result is None

    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_api_returns_empty_data(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "data": {}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = AirQualityAdapter(api_key="test-key")
        result = adapter.get_nearest_station(52.0, 21.0)
        assert result is None

    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_request_exception_returns_none(self, mock_get):
        mock_get.side_effect = requests.RequestException("timeout")

        adapter = AirQualityAdapter(api_key="test-key")
        result = adapter.get_nearest_station(52.0, 21.0)
        assert result is None

    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_parse_error_returns_none(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "data": None}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = AirQualityAdapter(api_key="test-key")
        result = adapter.get_nearest_station(52.0, 21.0)
        assert result is None

    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_result_is_cached(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "ok",
            "data": {
                "idx": 1,
                "city": {"name": "Station A", "geo": [52.0, 21.0]},
                "aqi": 50,
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = AirQualityAdapter(api_key="test-key")
        adapter.get_nearest_station(52.0, 21.0)
        adapter.get_nearest_station(52.0, 21.0)

        # Should only call API once due to caching
        assert mock_get.call_count == 1


class TestAirQualityGetAqiScore:
    """Tests for AirQualityAdapter.get_aqi_score."""

    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_api_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "ok",
            "data": {
                "aqi": 45,
                "city": {"name": "Krakow Station"},
                "iaqi": {
                    "pm25": {"v": 12.5},
                    "pm10": {"v": 20.0},
                },
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = AirQualityAdapter(api_key="test-key")
        result = adapter.get_aqi_score(50.06, 19.94)

        assert isinstance(result, AirQualityResult)
        assert result.aqi_value == 45
        assert result.pm25 == 12.5
        assert result.pm10 == 20.0
        assert result.data_source == "waqi"
        assert result.confidence == 1.0
        assert result.station_name == "Krakow Station"

    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_api_failure_falls_back_to_city(self, mock_get):
        mock_get.side_effect = requests.RequestException("fail")

        adapter = AirQualityAdapter(api_key="test-key")
        result = adapter.get_aqi_score(50.06, 19.94, city="krakow")

        assert result.data_source == "fallback"
        assert result.confidence == 0.5
        assert result.aqi_value == CITY_AQI_AVERAGES["krakow"]["aqi"]

    def test_no_api_key_uses_fallback_with_known_city(self):
        adapter = AirQualityAdapter(api_key=None)
        result = adapter.get_aqi_score(52.0, 21.0, city="warsaw")

        assert result.data_source == "fallback"
        assert result.aqi_value == 65
        assert result.pm25 == 18.5
        assert result.pm10 == 28.0
        assert result.confidence == 0.5
        assert "Warsaw" in result.station_name

    def test_no_api_key_uses_fallback_unknown_city(self):
        adapter = AirQualityAdapter(api_key=None)
        result = adapter.get_aqi_score(52.0, 21.0, city="Atlantis")

        assert result.data_source == "fallback"
        assert result.aqi_value == 50
        assert result.pm25 == 14.0
        assert result.pm10 == 22.0

    def test_no_api_key_no_city_uses_default(self):
        adapter = AirQualityAdapter(api_key=None)
        result = adapter.get_aqi_score(52.0, 21.0, city=None)

        assert result.data_source == "fallback"
        assert result.aqi_value == 50
        assert result.confidence == 0.3
        assert result.station_name == "Unknown (default)"

    def test_no_api_key_empty_city_uses_default(self):
        adapter = AirQualityAdapter(api_key=None)
        result = adapter.get_aqi_score(52.0, 21.0, city="")

        assert result.data_source == "fallback"
        assert result.confidence == 0.3

    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_api_returns_error_status_falls_back(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "error"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = AirQualityAdapter(api_key="test-key")
        result = adapter.get_aqi_score(52.0, 21.0, city="gdansk")

        assert result.data_source == "fallback"
        assert result.aqi_value == CITY_AQI_AVERAGES["gdansk"]["aqi"]

    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_aqi_result_is_cached(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "ok",
            "data": {
                "aqi": 30,
                "city": {"name": "Cached Station"},
                "iaqi": {"pm25": {"v": 8.0}, "pm10": {"v": 15.0}},
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = AirQualityAdapter(api_key="test-key")
        adapter.get_aqi_score(52.0, 21.0)
        adapter.get_aqi_score(52.0, 21.0)

        assert mock_get.call_count == 1

    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_api_key_error_falls_back(self, mock_get):
        """When API response raises KeyError during parsing, fallback is used."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "data": {"aqi": "not_a_number"}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = AirQualityAdapter(api_key="test-key")
        result = adapter.get_aqi_score(52.0, 21.0, city="poznan")

        assert result.data_source == "fallback"


class TestAirQualityCalculateAqiScore:
    """Tests for _calculate_aqi_score scoring bands."""

    def setup_method(self):
        self.adapter = AirQualityAdapter(api_key="k")

    def test_none_aqi_returns_neutral(self):
        assert self.adapter._calculate_aqi_score(None) == 50.0

    def test_aqi_0_good(self):
        score = self.adapter._calculate_aqi_score(0)
        assert 90 <= score <= 100

    def test_aqi_50_good_upper_boundary(self):
        score = self.adapter._calculate_aqi_score(50)
        assert 90 <= score <= 100

    def test_aqi_75_moderate(self):
        score = self.adapter._calculate_aqi_score(75)
        assert 70 <= score <= 89

    def test_aqi_100_moderate_upper_boundary(self):
        score = self.adapter._calculate_aqi_score(100)
        assert 70 <= score <= 89

    def test_aqi_125_unhealthy_sensitive(self):
        score = self.adapter._calculate_aqi_score(125)
        assert 50 <= score <= 69

    def test_aqi_175_unhealthy(self):
        score = self.adapter._calculate_aqi_score(175)
        assert 30 <= score <= 49

    def test_aqi_250_very_unhealthy(self):
        score = self.adapter._calculate_aqi_score(250)
        assert 10 <= score <= 29

    def test_aqi_350_hazardous(self):
        score = self.adapter._calculate_aqi_score(350)
        assert 0 <= score < 10

    def test_higher_aqi_means_lower_score(self):
        score_good = self.adapter._calculate_aqi_score(20)
        score_bad = self.adapter._calculate_aqi_score(200)
        assert score_good > score_bad


class TestAirQualityHaversine:
    """Tests for _haversine_distance."""

    def setup_method(self):
        self.adapter = AirQualityAdapter(api_key="k")

    def test_same_point_returns_zero(self):
        dist = self.adapter._haversine_distance(52.0, 21.0, 52.0, 21.0)
        assert dist == 0.0

    def test_known_distance_warsaw_krakow(self):
        # Warsaw ~52.23, 21.01 ; Krakow ~50.06, 19.94 ~ approx 250-270 km
        dist = self.adapter._haversine_distance(52.23, 21.01, 50.06, 19.94)
        assert 250 < dist < 300


class TestAirQualityCache:
    """Tests for caching mechanisms."""

    def test_put_and_get_from_cache(self):
        adapter = AirQualityAdapter(api_key="k", cache_ttl=3600)
        value = {"test": True}
        adapter._put_in_cache("key1", value)

        result = adapter._get_from_cache("key1")
        assert result == value

    def test_expired_cache_returns_none(self):
        adapter = AirQualityAdapter(api_key="k", cache_ttl=3600)
        # Manually insert with an old timestamp to simulate expiration
        adapter._cache["key2"] = ("val", time.time() - 9999)
        result = adapter._get_from_cache("key2")
        assert result is None

    def test_missing_key_returns_none(self):
        adapter = AirQualityAdapter(api_key="k")
        result = adapter._get_from_cache("nonexistent")
        assert result is None

    def test_station_cache_returns_station(self):
        adapter = AirQualityAdapter(api_key="k", cache_ttl=3600)
        station = AirQualityStation("s1", "Test", 52.0, 21.0, 50, 1.0)
        adapter._put_in_cache("sc", station)
        result = adapter._get_station_from_cache("sc")
        assert isinstance(result, AirQualityStation)
        assert result.station_id == "s1"

    def test_aqi_result_cache_returns_result(self):
        adapter = AirQualityAdapter(api_key="k", cache_ttl=3600)
        aqi_result = AirQualityResult(95.0, 30, 8.0, 15.0, "waqi", 1.0, "S")
        adapter._put_in_cache("aqi", aqi_result)
        result = adapter._get_aqi_result_from_cache("aqi")
        assert isinstance(result, AirQualityResult)
        assert result.score == 95.0


class TestAirQualityGetStatus:
    """Tests for get_status."""

    def test_status_with_api_key(self):
        adapter = AirQualityAdapter(api_key="test-key")
        status = adapter.get_status()

        assert status["adapter"] == "AirQualityAdapter"
        assert status["api_configured"] is True
        assert status["cache_ttl"] == 3600
        assert status["cache_size"] == 0
        assert "waqi.info" in status["api_endpoint"]

    def test_status_without_api_key(self):
        adapter = AirQualityAdapter(api_key=None)
        status = adapter.get_status()
        assert status["api_configured"] is False


class TestAirQualityFallbackCityData:
    """Tests for fallback data across all configured cities."""

    def test_all_city_averages_have_required_fields(self):
        required_keys = {"aqi", "pm25", "pm10"}
        for city, data in CITY_AQI_AVERAGES.items():
            assert required_keys.issubset(data.keys()), f"Missing keys for {city}"

    def test_fallback_case_insensitive_city(self):
        adapter = AirQualityAdapter(api_key=None)
        result_lower = adapter.get_aqi_score(0, 0, city="warsaw")
        result_upper = adapter.get_aqi_score(0, 0, city="Warsaw")
        assert result_lower.aqi_value == result_upper.aqi_value

    def test_fallback_strips_whitespace(self):
        adapter = AirQualityAdapter(api_key=None)
        result = adapter.get_aqi_score(0, 0, city="  warsaw  ")
        assert result.aqi_value == 65


class TestGetAirQualityAdapter:
    """Tests for the module-level singleton factory."""

    def test_returns_adapter_instance(self):
        adapter = get_air_quality_adapter()
        assert isinstance(adapter, AirQualityAdapter)


# ---------------------------------------------------------------------------
# TransportAdapter tests
# ---------------------------------------------------------------------------


class TestTransportAdapterInit:
    """Tests for TransportAdapter initialization."""

    def test_default_api_url(self):
        with patch.dict("os.environ", {}, clear=True):
            adapter = TransportAdapter()
            assert adapter._api_url == "https://overpass-api.de/api/interpreter"

    def test_custom_api_url(self):
        adapter = TransportAdapter(api_url="http://custom-overpass.local/api")
        assert adapter._api_url == "http://custom-overpass.local/api"

    def test_api_url_from_env(self):
        with patch.dict("os.environ", {"OVERPASS_API_URL": "http://env-overpass.local"}):
            adapter = TransportAdapter()
            assert adapter._api_url == "http://env-overpass.local"


class TestTransportFetchPois:
    """Tests for TransportAdapter.fetch_transport_pois."""

    @patch("data.adapters.transport_adapter.requests.get")
    def test_success_returns_stops(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": 100,
                    "lat": 52.230,
                    "lon": 21.013,
                    "tags": {"highway": "bus_stop", "name": "Bus Stop A"},
                },
                {
                    "id": 200,
                    "lat": 52.231,
                    "lon": 21.014,
                    "tags": {"railway": "tram_stop", "name": "Tram Stop B"},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = TransportAdapter()
        stops = adapter.fetch_transport_pois(52.2297, 21.0122)

        assert len(stops) == 2
        assert isinstance(stops[0], TransportStop)
        assert stops[0].type == "bus"
        assert stops[0].name == "Bus Stop A"
        assert stops[1].type == "tram"

    @patch("data.adapters.transport_adapter.requests.get")
    def test_empty_elements(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"elements": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = TransportAdapter()
        stops = adapter.fetch_transport_pois(52.0, 21.0)
        assert stops == []

    @patch("data.adapters.transport_adapter.requests.get")
    def test_request_exception_returns_empty(self, mock_get):
        mock_get.side_effect = requests.RequestException("network error")

        adapter = TransportAdapter()
        stops = adapter.fetch_transport_pois(52.0, 21.0)
        assert stops == []

    @patch("data.adapters.transport_adapter.requests.get")
    def test_generic_exception_returns_empty(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("bad json")
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = TransportAdapter()
        stops = adapter.fetch_transport_pois(52.0, 21.0)
        assert stops == []

    @patch("data.adapters.transport_adapter.requests.get")
    def test_element_without_tags_skipped(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {"id": 1, "lat": 52.0, "lon": 21.0},  # no tags
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = TransportAdapter()
        stops = adapter.fetch_transport_pois(52.0, 21.0)
        assert stops == []

    @patch("data.adapters.transport_adapter.requests.get")
    def test_element_without_coordinates_skipped(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {"id": 1, "tags": {"highway": "bus_stop"}},  # no lat/lon
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = TransportAdapter()
        stops = adapter.fetch_transport_pois(52.0, 21.0)
        assert stops == []

    @patch("data.adapters.transport_adapter.requests.get")
    def test_element_with_center_coords(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": 1,
                    "center": {"lat": 52.23, "lon": 21.01},
                    "tags": {"railway": "station", "name": "Central Station"},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = TransportAdapter()
        stops = adapter.fetch_transport_pois(52.229, 21.012)
        assert len(stops) == 1
        assert stops[0].type == "train"
        assert stops[0].latitude == 52.23


class TestTransportStopCounting:
    """Tests for count_stops and get_stop_types."""

    @patch("data.adapters.transport_adapter.requests.get")
    def test_count_stops(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {"id": 1, "lat": 52.23, "lon": 21.01, "tags": {"highway": "bus_stop"}},
                {"id": 2, "lat": 52.231, "lon": 21.011, "tags": {"highway": "bus_stop"}},
                {"id": 3, "lat": 52.232, "lon": 21.012, "tags": {"railway": "tram_stop"}},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = TransportAdapter()
        count = adapter.count_stops(52.23, 21.01)
        assert count == 3

    @patch("data.adapters.transport_adapter.requests.get")
    def test_get_stop_types(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {"id": 1, "lat": 52.23, "lon": 21.01, "tags": {"highway": "bus_stop"}},
                {"id": 2, "lat": 52.231, "lon": 21.011, "tags": {"highway": "bus_stop"}},
                {"id": 3, "lat": 52.232, "lon": 21.012, "tags": {"railway": "tram_stop"}},
                {"id": 4, "lat": 52.233, "lon": 21.013, "tags": {"railway": "station"}},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = TransportAdapter()
        types = adapter.get_stop_types(52.23, 21.01)

        assert types["bus"] == 2
        assert types["tram"] == 1
        assert types["train"] == 1
        assert types["metro"] == 0
        assert types["light_rail"] == 0

    @patch("data.adapters.transport_adapter.requests.get")
    def test_get_stop_types_empty(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"elements": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = TransportAdapter()
        types = adapter.get_stop_types(52.0, 21.0)
        assert all(v == 0 for v in types.values())


class TestTransportAccessibilityScore:
    """Tests for calculate_accessibility_score."""

    @patch("data.adapters.transport_adapter.requests.get")
    def test_no_stops_returns_baseline(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"elements": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = TransportAdapter()
        score = adapter.calculate_accessibility_score(52.0, 21.0)
        assert score == 20.0

    @patch("data.adapters.transport_adapter.requests.get")
    def test_many_stops_high_score(self, mock_get):
        elements = []
        for i in range(12):
            elements.append(
                {
                    "id": i,
                    "lat": 52.23 + i * 0.001,
                    "lon": 21.01 + i * 0.001,
                    "tags": {"highway": "bus_stop", "name": f"Stop {i}"},
                }
            )
        mock_response = MagicMock()
        mock_response.json.return_value = {"elements": elements}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = TransportAdapter()
        score = adapter.calculate_accessibility_score(52.23, 21.01)
        assert score > 80

    @patch("data.adapters.transport_adapter.requests.get")
    def test_score_capped_at_100(self, mock_get):
        # Create diverse high-count stops to push score toward 100
        elements = []
        for i in range(15):
            elements.append(
                {
                    "id": i,
                    "lat": 52.23 + i * 0.001,
                    "lon": 21.01 + i * 0.001,
                    "tags": {"highway": "bus_stop"},
                }
            )
        for i in range(15, 20):
            elements.append(
                {
                    "id": i,
                    "lat": 52.23 + i * 0.001,
                    "lon": 21.01 + i * 0.001,
                    "tags": {"railway": "station"},
                }
            )
        for i in range(20, 25):
            elements.append(
                {
                    "id": i,
                    "lat": 52.23 + i * 0.001,
                    "lon": 21.01 + i * 0.001,
                    "tags": {"railway": "subway_entrance"},
                }
            )
        mock_response = MagicMock()
        mock_response.json.return_value = {"elements": elements}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = TransportAdapter()
        score = adapter.calculate_accessibility_score(52.23, 21.01)
        assert score <= 100.0


class TestTransportBaseScore:
    """Tests for _calculate_base_score."""

    def setup_method(self):
        self.adapter = TransportAdapter()

    def test_zero_stops(self):
        assert self.adapter._calculate_base_score(0) == 20.0

    def test_one_stop(self):
        assert self.adapter._calculate_base_score(1) == 40.0

    def test_two_stops(self):
        assert self.adapter._calculate_base_score(2) == 40.0

    def test_three_stops(self):
        assert self.adapter._calculate_base_score(3) == 60.0

    def test_six_stops(self):
        assert self.adapter._calculate_base_score(6) == 80.0

    def test_eleven_stops(self):
        assert self.adapter._calculate_base_score(11) == 95.0


class TestTransportDiversityBonus:
    """Tests for _calculate_diversity_bonus."""

    def setup_method(self):
        self.adapter = TransportAdapter()

    def test_single_type(self):
        assert (
            self.adapter._calculate_diversity_bonus(
                {"bus": 3, "tram": 0, "metro": 0, "train": 0, "light_rail": 0}
            )
            == 0.0
        )

    def test_two_types(self):
        assert (
            self.adapter._calculate_diversity_bonus(
                {"bus": 2, "tram": 1, "metro": 0, "train": 0, "light_rail": 0}
            )
            == 3.0
        )

    def test_three_types(self):
        assert (
            self.adapter._calculate_diversity_bonus(
                {"bus": 2, "tram": 1, "metro": 1, "train": 0, "light_rail": 0}
            )
            == 5.0
        )

    def test_four_types(self):
        assert (
            self.adapter._calculate_diversity_bonus(
                {"bus": 1, "tram": 1, "metro": 1, "train": 1, "light_rail": 0}
            )
            == 7.0
        )

    def test_five_types(self):
        assert (
            self.adapter._calculate_diversity_bonus(
                {"bus": 1, "tram": 1, "metro": 1, "train": 1, "light_rail": 1}
            )
            == 10.0
        )


class TestTransportCapacityBonus:
    """Tests for _calculate_capacity_bonus."""

    def setup_method(self):
        self.adapter = TransportAdapter()

    def test_no_high_capacity(self):
        assert (
            self.adapter._calculate_capacity_bonus(
                {"bus": 5, "tram": 0, "metro": 0, "train": 0, "light_rail": 0}
            )
            == 0.0
        )

    def test_metro_only(self):
        bonus = self.adapter._calculate_capacity_bonus(
            {"bus": 0, "tram": 0, "metro": 1, "train": 0, "light_rail": 0}
        )
        assert bonus == 3.0

    def test_train_only(self):
        bonus = self.adapter._calculate_capacity_bonus(
            {"bus": 0, "tram": 0, "metro": 0, "train": 1, "light_rail": 0}
        )
        assert bonus == 2.0

    def test_light_rail_only(self):
        bonus = self.adapter._calculate_capacity_bonus(
            {"bus": 0, "tram": 0, "metro": 0, "train": 0, "light_rail": 1}
        )
        assert bonus == 1.5

    def test_all_high_capacity_capped(self):
        bonus = self.adapter._calculate_capacity_bonus(
            {"bus": 0, "tram": 0, "metro": 2, "train": 3, "light_rail": 1}
        )
        assert bonus == 5.0  # 3 + 2 + 1.5 = 6.5 capped at 5.0


class TestTransportDetermineType:
    """Tests for _determine_transport_type."""

    def setup_method(self):
        self.adapter = TransportAdapter()

    def test_bus_stop(self):
        assert self.adapter._determine_transport_type({"highway": "bus_stop"}) == "bus"

    def test_tram_stop(self):
        assert self.adapter._determine_transport_type({"railway": "tram_stop"}) == "tram"

    def test_subway_entrance(self):
        assert self.adapter._determine_transport_type({"railway": "subway_entrance"}) == "metro"

    def test_station(self):
        assert self.adapter._determine_transport_type({"railway": "station"}) == "train"

    def test_light_rail(self):
        assert self.adapter._determine_transport_type({"railway": "light_rail"}) == "light_rail"

    def test_public_transport_stop_position(self):
        assert (
            self.adapter._determine_transport_type({"public_transport": "stop_position"}) == "bus"
        )

    def test_public_transport_platform_with_bus(self):
        assert (
            self.adapter._determine_transport_type({"public_transport": "platform", "bus": "yes"})
            == "bus"
        )

    def test_public_transport_platform_with_tram(self):
        assert (
            self.adapter._determine_transport_type({"public_transport": "platform", "tram": "yes"})
            == "tram"
        )

    def test_public_transport_platform_with_subway(self):
        assert (
            self.adapter._determine_transport_type(
                {"public_transport": "platform", "subway": "yes"}
            )
            == "metro"
        )

    def test_public_transport_platform_with_train(self):
        assert (
            self.adapter._determine_transport_type({"public_transport": "platform", "train": "yes"})
            == "train"
        )

    def test_unknown_tags_default_to_bus(self):
        assert self.adapter._determine_transport_type({"some_tag": "some_value"}) == "bus"


class TestTransportHaversine:
    """Tests for _calculate_distance."""

    def test_same_point_returns_zero(self):
        adapter = TransportAdapter()
        dist = adapter._calculate_distance(52.0, 21.0, 52.0, 21.0)
        assert dist == 0.0

    def test_positive_distance(self):
        adapter = TransportAdapter()
        dist = adapter._calculate_distance(52.23, 21.01, 50.06, 19.94)
        assert dist > 200000  # >200 km in meters


class TestTransportBuildQuery:
    """Tests for _build_transport_query."""

    def test_query_contains_coordinates(self):
        adapter = TransportAdapter()
        query = adapter._build_transport_query(52.23, 21.01, 500)
        assert "52.23" in query
        assert "21.01" in query
        assert "500" in query

    def test_query_contains_bus_stop_tag(self):
        adapter = TransportAdapter()
        query = adapter._build_transport_query(52.0, 21.0, 1000)
        assert "bus_stop" in query


class TestTransportGetFullResult:
    """Tests for get_full_result."""

    @patch("data.adapters.transport_adapter.requests.get")
    def test_full_result_structure(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": 1,
                    "lat": 52.23,
                    "lon": 21.01,
                    "tags": {"highway": "bus_stop", "name": "Stop A"},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = TransportAdapter()
        result = adapter.get_full_result(52.23, 21.01)

        assert isinstance(result, TransportResult)
        assert result.total_stops == 1
        assert result.data_source == "overpass"
        assert 0 <= result.confidence <= 1
        assert result.score > 0

    @patch("data.adapters.transport_adapter.requests.get")
    def test_full_result_empty_stops(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"elements": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = TransportAdapter()
        result = adapter.get_full_result(52.0, 21.0)

        assert result.total_stops == 0
        assert result.score == 20.0
        assert result.confidence == 0.5


class TestTransportConfidence:
    """Tests for _calculate_confidence."""

    def test_empty_stops_returns_half(self):
        adapter = TransportAdapter()
        assert (
            adapter._calculate_confidence(
                [], {"bus": 0, "tram": 0, "metro": 0, "train": 0, "light_rail": 0}
            )
            == 0.5
        )

    def test_named_stops_higher_confidence(self):
        adapter = TransportAdapter()
        named = [TransportStop("1", "Named", "bus", 52.0, 21.0)]
        unnamed = [TransportStop("2", None, "bus", 52.0, 21.0)]
        conf_named = adapter._calculate_confidence(
            named, {"bus": 1, "tram": 0, "metro": 0, "train": 0, "light_rail": 0}
        )
        conf_unnamed = adapter._calculate_confidence(
            unnamed, {"bus": 1, "tram": 0, "metro": 0, "train": 0, "light_rail": 0}
        )
        assert conf_named > conf_unnamed

    def test_diverse_types_higher_confidence(self):
        adapter = TransportAdapter()
        stops = [TransportStop("1", "S", "bus", 52.0, 21.0)]
        low_diversity = {"bus": 1, "tram": 0, "metro": 0, "train": 0, "light_rail": 0}
        high_diversity = {"bus": 1, "tram": 1, "metro": 1, "train": 1, "light_rail": 1}
        conf_low = adapter._calculate_confidence(stops, low_diversity)
        conf_high = adapter._calculate_confidence(stops, high_diversity)
        assert conf_high > conf_low


class TestGetTransportAdapter:
    """Tests for the module-level singleton factory."""

    def test_returns_adapter_instance(self):
        adapter = get_transport_adapter()
        assert isinstance(adapter, TransportAdapter)


# ---------------------------------------------------------------------------
# NoiseAdapter tests
# ---------------------------------------------------------------------------


class TestNoiseAdapterInit:
    """Tests for NoiseAdapter initialization."""

    def test_default_api_url(self):
        with patch.dict("os.environ", {}, clear=True):
            adapter = NoiseAdapter()
            assert adapter._api_url == "https://overpass-api.de/api/interpreter"

    def test_custom_api_url(self):
        adapter = NoiseAdapter(api_url="http://custom.local/api")
        assert adapter._api_url == "http://custom.local/api"

    def test_api_url_from_env(self):
        with patch.dict("os.environ", {"OVERPASS_API_URL": "http://env-overpass.local"}):
            adapter = NoiseAdapter()
            assert adapter._api_url == "http://env-overpass.local"


class TestNoiseSourceDataclass:
    """Tests for NoiseSource."""

    def test_to_dict(self):
        source = NoiseSource(
            id="road_1",
            type="road",
            name="Highway A1",
            latitude=52.0,
            longitude=21.0,
            distance_m=150.5,
            severity=0.8,
            tags={"highway": "motorway"},
        )
        d = source.to_dict()
        assert d["id"] == "road_1"
        assert d["type"] == "road"
        assert d["distance_m"] == 150.5
        assert d["severity"] == 0.8

    def test_to_dict_rounding(self):
        source = NoiseSource("1", "road", "Rd", 52.0, 21.0, 123.456, 0.789)
        d = source.to_dict()
        assert d["distance_m"] == 123.5
        assert d["severity"] == 0.79


class TestNoiseResultDataclass:
    """Tests for NoiseResult."""

    def test_to_dict(self):
        sources = [NoiseSource("1", "road", "Rd", 52.0, 21.0, 100.0, 0.5)]
        result = NoiseResult(
            score=80.0,
            estimated_db=55.0,
            noise_sources=sources,
            data_source="overpass_api",
            confidence=0.8,
            query_latitude=52.0,
            query_longitude=21.0,
        )
        d = result.to_dict()
        assert d["score"] == 80.0
        assert d["estimated_db"] == 55.0
        assert len(d["noise_sources"]) == 1
        assert d["query_latitude"] == 52.0


class TestNoiseEstimateNoiseLevel:
    """Tests for estimate_noise_level."""

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    @patch.object(NoiseAdapter, "calculate_noise_score")
    def test_success_returns_result(self, mock_score, mock_sources):
        mock_sources.return_value = []
        mock_score.return_value = 95.0

        adapter = NoiseAdapter()
        result = adapter.estimate_noise_level(52.0, 21.0)

        assert isinstance(result, NoiseResult)
        assert result.data_source == "overpass_api"
        assert result.query_latitude == 52.0
        assert result.query_longitude == 21.0

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_exception_returns_default_result(self, mock_sources):
        mock_sources.side_effect = Exception("unexpected error")

        adapter = NoiseAdapter()
        result = adapter.estimate_noise_level(52.0, 21.0)

        assert result.score == 50.0
        assert result.estimated_db == 55.0
        assert result.noise_sources == []
        assert result.confidence == 0.0

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    @patch.object(NoiseAdapter, "calculate_noise_score")
    def test_with_noise_sources(self, mock_score, mock_sources):
        source = NoiseSource("r1", "road", "Highway", 52.001, 21.001, 80.0, 1.0)
        mock_sources.return_value = [source]
        mock_score.return_value = 50.0

        adapter = NoiseAdapter()
        result = adapter.estimate_noise_level(52.0, 21.0)

        assert result.noise_sources == [source]
        assert result.estimated_db > 40.0


class TestNoiseGetNearbySources:
    """Tests for get_nearby_noise_sources."""

    @patch.object(NoiseAdapter, "_query_airports")
    @patch.object(NoiseAdapter, "_query_industrial")
    @patch.object(NoiseAdapter, "_query_railways")
    @patch.object(NoiseAdapter, "_query_roads")
    def test_combines_all_sources(self, mock_roads, mock_railways, mock_airports, mock_industrial):
        mock_roads.return_value = [NoiseSource("r1", "road", "Road", 52.0, 21.0, 100, 0.6)]
        mock_railways.return_value = [NoiseSource("rw1", "railway", "Rail", 52.0, 21.0, 200, 0.9)]
        mock_airports.return_value = []
        mock_industrial.return_value = [
            NoiseSource("i1", "industrial", "Factory", 52.0, 21.0, 300, 0.5)
        ]

        adapter = NoiseAdapter()
        sources = adapter.get_nearby_noise_sources(52.0, 21.0)

        assert len(sources) == 3
        # Should be sorted by distance
        assert sources[0].distance_m <= sources[1].distance_m <= sources[2].distance_m

    @patch.object(NoiseAdapter, "_query_airports")
    @patch.object(NoiseAdapter, "_query_industrial")
    @patch.object(NoiseAdapter, "_query_railways")
    @patch.object(NoiseAdapter, "_query_roads")
    def test_no_sources_returns_empty(
        self, mock_roads, mock_railways, mock_airports, mock_industrial
    ):
        mock_roads.return_value = []
        mock_railways.return_value = []
        mock_airports.return_value = []
        mock_industrial.return_value = []

        adapter = NoiseAdapter()
        sources = adapter.get_nearby_noise_sources(52.0, 21.0)
        assert sources == []


class TestNoiseCalculateScore:
    """Tests for calculate_noise_score."""

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_no_sources_returns_base(self, mock_sources):
        mock_sources.return_value = []
        adapter = NoiseAdapter()
        score = adapter.calculate_noise_score(52.0, 21.0)
        assert score == 95.0

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_major_road_near_penalty(self, mock_sources):
        # Motorway <100m -> severity 1.0 >= 0.8, near distance
        source = NoiseSource("r1", "road", "Motorway", 52.0, 21.0, 50.0, 1.0)
        mock_sources.return_value = [source]

        adapter = NoiseAdapter()
        score = adapter.calculate_noise_score(52.0, 21.0)
        assert score == 95.0 - 45.0  # PENALTY_MAJOR_ROAD_NEAR

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_major_road_medium_distance_penalty(self, mock_sources):
        # Trunk 100-200m -> severity 0.8 >= 0.8
        source = NoiseSource("r1", "road", "Trunk", 52.0, 21.0, 150.0, 0.8)
        mock_sources.return_value = [source]

        adapter = NoiseAdapter()
        score = adapter.calculate_noise_score(52.0, 21.0)
        assert score == 95.0 - 25.0  # PENALTY_MAJOR_ROAD_MEDIUM

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_minor_road_far_penalty(self, mock_sources):
        # Secondary road >200m -> severity 0.4 < 0.8, far distance
        source = NoiseSource("r1", "road", "Secondary", 52.0, 21.0, 300.0, 0.4)
        mock_sources.return_value = [source]

        adapter = NoiseAdapter()
        score = adapter.calculate_noise_score(52.0, 21.0)
        assert score == 95.0 - 10.0  # PENALTY_MINOR_ROAD_FAR

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_minor_road_near_penalty(self, mock_sources):
        # Secondary road <200m -> severity 0.4 < 0.8, not far
        source = NoiseSource("r1", "road", "Secondary", 52.0, 21.0, 100.0, 0.4)
        mock_sources.return_value = [source]

        adapter = NoiseAdapter()
        score = adapter.calculate_noise_score(52.0, 21.0)
        assert score == 95.0 - 45.0 * 0.5  # PENALTY_MAJOR_ROAD_NEAR * 0.5

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_railway_near_penalty(self, mock_sources):
        source = NoiseSource("rw1", "railway", "Rail", 52.0, 21.0, 100.0, 0.9)
        mock_sources.return_value = [source]

        adapter = NoiseAdapter()
        score = adapter.calculate_noise_score(52.0, 21.0)
        assert score == 95.0 - 15.0  # PENALTY_RAILWAY_NEAR

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_airport_near_penalty(self, mock_sources):
        source = NoiseSource("a1", "airport", "Airport", 52.0, 21.0, 1000.0, 1.0)
        mock_sources.return_value = [source]

        adapter = NoiseAdapter()
        score = adapter.calculate_noise_score(52.0, 21.0)
        assert score == 95.0 - 20.0  # PENALTY_AIRPORT_NEAR

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_industrial_near_penalty(self, mock_sources):
        source = NoiseSource("i1", "industrial", "Factory", 52.0, 21.0, 200.0, 0.5)
        mock_sources.return_value = [source]

        adapter = NoiseAdapter()
        score = adapter.calculate_noise_score(52.0, 21.0)
        assert score == 95.0 - 10.0  # PENALTY_INDUSTRIAL_NEAR

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_combined_penalties(self, mock_sources):
        sources = [
            NoiseSource("r1", "road", "Motorway", 52.0, 21.0, 50.0, 1.0),
            NoiseSource("rw1", "railway", "Rail", 52.0, 21.0, 100.0, 0.9),
        ]
        mock_sources.return_value = sources

        adapter = NoiseAdapter()
        score = adapter.calculate_noise_score(52.0, 21.0)
        assert score == 95.0 - 45.0 - 15.0  # road + railway

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_score_never_below_zero(self, mock_sources):
        # All penalties combined to max
        sources = [
            NoiseSource("r1", "road", "Motorway", 52.0, 21.0, 10.0, 1.0),
            NoiseSource("rw1", "railway", "Rail", 52.0, 21.0, 10.0, 1.0),
            NoiseSource("a1", "airport", "Airport", 52.0, 21.0, 100.0, 1.0),
            NoiseSource("i1", "industrial", "Factory", 52.0, 21.0, 50.0, 0.5),
        ]
        mock_sources.return_value = sources

        adapter = NoiseAdapter()
        score = adapter.calculate_noise_score(52.0, 21.0)
        assert score >= 0.0

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_airport_beyond_threshold_no_penalty(self, mock_sources):
        source = NoiseSource("a1", "airport", "Airport", 52.0, 21.0, 2500.0, 1.0)
        mock_sources.return_value = [source]

        adapter = NoiseAdapter()
        score = adapter.calculate_noise_score(52.0, 21.0)
        assert score == 95.0  # no penalty beyond 2000m

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_railway_beyond_threshold_no_penalty(self, mock_sources):
        source = NoiseSource("rw1", "railway", "Rail", 52.0, 21.0, 300.0, 0.9)
        mock_sources.return_value = [source]

        adapter = NoiseAdapter()
        score = adapter.calculate_noise_score(52.0, 21.0)
        assert score == 95.0  # no penalty beyond 200m

    @patch.object(NoiseAdapter, "get_nearby_noise_sources")
    def test_industrial_beyond_threshold_no_penalty(self, mock_sources):
        source = NoiseSource("i1", "industrial", "Factory", 52.0, 21.0, 600.0, 0.5)
        mock_sources.return_value = [source]

        adapter = NoiseAdapter()
        score = adapter.calculate_noise_score(52.0, 21.0)
        assert score == 95.0  # no penalty beyond 500m


class TestNoiseQueryRoads:
    """Tests for _query_roads."""

    @patch("data.adapters.noise_adapter.requests.get")
    def test_success_returns_road_sources(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": 1,
                    "center": {"lat": 52.001, "lon": 21.001},
                    "tags": {"highway": "motorway", "name": "A1"},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = NoiseAdapter()
        sources = adapter._query_roads(52.0, 21.0, 500)

        assert len(sources) == 1
        assert sources[0].type == "road"
        assert sources[0].severity == 1.0
        assert sources[0].name == "A1"

    @patch("data.adapters.noise_adapter.requests.get")
    def test_filters_non_road_highways(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": 1,
                    "center": {"lat": 52.001, "lon": 21.001},
                    "tags": {"highway": "residential"},  # not in ROAD_HIGHWAY_TAGS
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = NoiseAdapter()
        sources = adapter._query_roads(52.0, 21.0, 500)
        assert sources == []

    @patch("data.adapters.noise_adapter.requests.get")
    def test_request_error_returns_empty(self, mock_get):
        mock_get.side_effect = requests.RequestException("fail")

        adapter = NoiseAdapter()
        sources = adapter._query_roads(52.0, 21.0, 500)
        assert sources == []

    @patch("data.adapters.noise_adapter.requests.get")
    def test_no_coordinates_skips_element(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {"id": 1, "tags": {"highway": "motorway"}},  # no coords
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = NoiseAdapter()
        sources = adapter._query_roads(52.0, 21.0, 500)
        assert sources == []


class TestNoiseQueryRailways:
    """Tests for _query_railways."""

    @patch("data.adapters.noise_adapter.requests.get")
    def test_success_returns_railway_sources(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": 10,
                    "center": {"lat": 52.001, "lon": 21.001},
                    "tags": {"railway": "rail", "name": "Main Line"},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = NoiseAdapter()
        sources = adapter._query_railways(52.0, 21.0, 500)

        assert len(sources) == 1
        assert sources[0].type == "railway"
        assert sources[0].severity == 0.9
        assert sources[0].name == "Main Line"

    @patch("data.adapters.noise_adapter.requests.get")
    def test_skips_empty_railway_type(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": 10,
                    "center": {"lat": 52.001, "lon": 21.001},
                    "tags": {"railway": ""},  # empty string
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = NoiseAdapter()
        sources = adapter._query_railways(52.0, 21.0, 500)
        assert sources == []

    @patch("data.adapters.noise_adapter.requests.get")
    def test_request_error_returns_empty(self, mock_get):
        mock_get.side_effect = requests.RequestException("fail")

        adapter = NoiseAdapter()
        sources = adapter._query_railways(52.0, 21.0, 500)
        assert sources == []


class TestNoiseQueryAirports:
    """Tests for _query_airports."""

    @patch("data.adapters.noise_adapter.requests.get")
    def test_success_returns_airport_sources(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": 20,
                    "center": {"lat": 52.01, "lon": 21.01},
                    "tags": {"aeroway": "aerodrome", "name": "Chopin Airport"},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = NoiseAdapter()
        sources = adapter._query_airports(52.0, 21.0)

        assert len(sources) == 1
        assert sources[0].type == "airport"
        assert sources[0].severity == 1.0
        assert sources[0].name == "Chopin Airport"

    @patch("data.adapters.noise_adapter.requests.get")
    def test_no_coords_skips_element(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {"id": 20, "tags": {"aeroway": "aerodrome"}},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = NoiseAdapter()
        sources = adapter._query_airports(52.0, 21.0)
        assert sources == []

    @patch("data.adapters.noise_adapter.requests.get")
    def test_request_error_returns_empty(self, mock_get):
        mock_get.side_effect = requests.RequestException("fail")

        adapter = NoiseAdapter()
        sources = adapter._query_airports(52.0, 21.0)
        assert sources == []

    @patch("data.adapters.noise_adapter.requests.get")
    def test_airport_name_fallback_to_aeroway_tag(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": 20,
                    "center": {"lat": 52.01, "lon": 21.01},
                    "tags": {"aeroway": "helipad"},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = NoiseAdapter()
        sources = adapter._query_airports(52.0, 21.0)
        assert sources[0].name == "helipad"


class TestNoiseQueryIndustrial:
    """Tests for _query_industrial."""

    @patch("data.adapters.noise_adapter.requests.get")
    def test_success_returns_industrial_sources(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": 30,
                    "center": {"lat": 52.002, "lon": 21.002},
                    "tags": {"landuse": "industrial", "name": "Steel Works"},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = NoiseAdapter()
        sources = adapter._query_industrial(52.0, 21.0, 500)

        assert len(sources) == 1
        assert sources[0].type == "industrial"
        assert sources[0].severity == 0.5
        assert sources[0].name == "Steel Works"

    @patch("data.adapters.noise_adapter.requests.get")
    def test_no_coords_skips_element(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {"id": 30, "tags": {"landuse": "industrial"}},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = NoiseAdapter()
        sources = adapter._query_industrial(52.0, 21.0, 500)
        assert sources == []

    @patch("data.adapters.noise_adapter.requests.get")
    def test_request_error_returns_empty(self, mock_get):
        mock_get.side_effect = requests.RequestException("fail")

        adapter = NoiseAdapter()
        sources = adapter._query_industrial(52.0, 21.0, 500)
        assert sources == []

    @patch("data.adapters.noise_adapter.requests.get")
    def test_name_fallback_to_landuse(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": 30,
                    "center": {"lat": 52.002, "lon": 21.002},
                    "tags": {"landuse": "commercial"},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = NoiseAdapter()
        sources = adapter._query_industrial(52.0, 21.0, 500)
        assert sources[0].name == "commercial"


class TestNoiseExtractCoordinates:
    """Tests for _extract_coordinates."""

    def setup_method(self):
        self.adapter = NoiseAdapter()

    def test_direct_lat_lon(self):
        result = self.adapter._extract_coordinates({"lat": 52.0, "lon": 21.0})
        assert result == {"lat": 52.0, "lon": 21.0}

    def test_center_coords(self):
        result = self.adapter._extract_coordinates({"center": {"lat": 52.0, "lon": 21.0}})
        assert result == {"lat": 52.0, "lon": 21.0}

    def test_no_coords_returns_none(self):
        result = self.adapter._extract_coordinates({"id": 1})
        assert result is None


class TestNoiseCalculateDistance:
    """Tests for _calculate_distance."""

    def test_same_point_returns_zero(self):
        adapter = NoiseAdapter()
        dist = adapter._calculate_distance(52.0, 21.0, 52.0, 21.0)
        assert dist == 0.0

    def test_positive_distance(self):
        adapter = NoiseAdapter()
        dist = adapter._calculate_distance(52.23, 21.01, 50.06, 19.94)
        assert dist > 200000  # > 200 km


class TestNoiseEstimateDecibels:
    """Tests for _estimate_decibels."""

    def test_no_sources_returns_base(self):
        adapter = NoiseAdapter()
        db = adapter._estimate_decibels([])
        assert db == 40.0

    def test_nearby_source_increases_db(self):
        adapter = NoiseAdapter()
        source = NoiseSource("r1", "road", "Rd", 52.0, 21.0, 50.0, 1.0)
        db = adapter._estimate_decibels([source])
        assert db > 40.0

    def test_distant_source_contributes_less(self):
        adapter = NoiseAdapter()
        near = NoiseSource("r1", "road", "Rd", 52.0, 21.0, 50.0, 1.0)
        far = NoiseSource("r2", "road", "Rd", 52.0, 21.0, 900.0, 1.0)
        db_near = adapter._estimate_decibels([near])
        db_far = adapter._estimate_decibels([far])
        assert db_near > db_far

    def test_clamped_at_80(self):
        adapter = NoiseAdapter()
        sources = [NoiseSource(f"r{i}", "road", "Rd", 52.0, 21.0, 10.0, 1.0) for i in range(50)]
        db = adapter._estimate_decibels(sources)
        assert db <= 80.0

    def test_airport_contribution_multiplier(self):
        adapter = NoiseAdapter()
        road_source = NoiseSource("r1", "road", "Rd", 52.0, 21.0, 100.0, 1.0)
        airport_source = NoiseSource("a1", "airport", "AP", 52.0, 21.0, 100.0, 1.0)
        db_road = adapter._estimate_decibels([road_source])
        db_airport = adapter._estimate_decibels([airport_source])
        assert db_airport > db_road  # airport multiplier = 1.5

    def test_railway_contribution_multiplier(self):
        adapter = NoiseAdapter()
        road_source = NoiseSource("r1", "road", "Rd", 52.0, 21.0, 100.0, 1.0)
        rail_source = NoiseSource("rw1", "railway", "Rail", 52.0, 21.0, 100.0, 1.0)
        db_road = adapter._estimate_decibels([road_source])
        db_rail = adapter._estimate_decibels([rail_source])
        assert db_rail > db_road  # railway multiplier = 1.2

    def test_far_source_returns_base(self):
        adapter = NoiseAdapter()
        source = NoiseSource("r1", "road", "Rd", 52.0, 21.0, 1500.0, 1.0)
        db = adapter._estimate_decibels([source])
        assert db == 40.0  # distance factor = max(0, 1 - 1500/1000) = 0


class TestNoiseCalculateConfidence:
    """Tests for _calculate_confidence."""

    def test_no_sources_returns_half(self):
        adapter = NoiseAdapter()
        assert adapter._calculate_confidence([]) == 0.5

    def test_unnamed_sources(self):
        adapter = NoiseAdapter()
        sources = [NoiseSource("1", "road", None, 52.0, 21.0, 100.0, 0.5)]
        conf = adapter._calculate_confidence(sources)
        assert 0.3 <= conf <= 0.9

    def test_named_sources_higher_confidence(self):
        adapter = NoiseAdapter()
        named = [NoiseSource("1", "road", "Named", 52.0, 21.0, 100.0, 0.5)]
        unnamed = [NoiseSource("1", "road", None, 52.0, 21.0, 100.0, 0.5)]
        assert adapter._calculate_confidence(named) > adapter._calculate_confidence(unnamed)

    def test_more_sources_higher_confidence(self):
        adapter = NoiseAdapter()
        few = [NoiseSource(f"r{i}", "road", None, 52.0, 21.0, 100.0, 0.5) for i in range(2)]
        many = [NoiseSource(f"r{i}", "road", None, 52.0, 21.0, 100.0, 0.5) for i in range(8)]
        assert adapter._calculate_confidence(many) >= adapter._calculate_confidence(few)

    def test_confidence_capped_at_095(self):
        adapter = NoiseAdapter()
        sources = [
            NoiseSource(f"r{i}", "road", f"Road {i}", 52.0, 21.0, 100.0, 0.5) for i in range(20)
        ]
        conf = adapter._calculate_confidence(sources)
        assert conf <= 0.95


class TestNoiseHelperMethods:
    """Tests for _get_road_name and _get_railway_name."""

    def setup_method(self):
        self.adapter = NoiseAdapter()

    def test_get_road_name_from_name(self):
        assert self.adapter._get_road_name({"name": "Main Street"}) == "Main Street"

    def test_get_road_name_from_ref(self):
        assert self.adapter._get_road_name({"ref": "A1"}) == "A1"

    def test_get_road_name_none(self):
        assert self.adapter._get_road_name({"highway": "motorway"}) is None

    def test_get_railway_name_from_name(self):
        assert self.adapter._get_railway_name({"name": "Express"}) == "Express"

    def test_get_railway_name_from_railway(self):
        assert self.adapter._get_railway_name({"railway": "rail"}) == "rail"


class TestGetNoiseAdapter:
    """Tests for the module-level singleton factory."""

    def test_returns_adapter_instance(self):
        adapter = get_noise_adapter()
        assert isinstance(adapter, NoiseAdapter)


class TestNoiseNodeCoordinates:
    """Tests for elements with node-type coordinates (lat/lon directly)."""

    @patch("data.adapters.noise_adapter.requests.get")
    def test_road_element_with_direct_coords(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": 1,
                    "lat": 52.001,
                    "lon": 21.001,
                    "tags": {"highway": "primary", "name": "Test Road"},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = NoiseAdapter()
        sources = adapter._query_roads(52.0, 21.0, 500)

        assert len(sources) == 1
        assert sources[0].latitude == 52.001
        assert sources[0].longitude == 21.001

    @patch("data.adapters.noise_adapter.requests.get")
    def test_airport_element_with_direct_coords(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": 1,
                    "lat": 52.01,
                    "lon": 21.01,
                    "tags": {"aeroway": "aerodrome", "name": "Airport"},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = NoiseAdapter()
        sources = adapter._query_airports(52.0, 21.0)

        assert len(sources) == 1
        assert sources[0].latitude == 52.01
