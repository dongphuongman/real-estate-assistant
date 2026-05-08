"""Tests for air quality adapter."""

import time
from unittest.mock import MagicMock, patch

from data.adapters.air_quality_adapter import (
    CITY_AQI_AVERAGES,
    AirQualityAdapter,
    AirQualityResult,
    AirQualityStation,
    get_air_quality_adapter,
)


class TestAirQualityStation:
    def test_create_station(self):
        station = AirQualityStation(
            station_id="123",
            name="Test Station",
            latitude=52.2297,
            longitude=21.0122,
            aqi=65,
            distance_km=1.5,
        )
        assert station.station_id == "123"
        assert station.name == "Test Station"
        assert station.aqi == 65

    def test_create_station_no_name(self):
        station = AirQualityStation(
            station_id="456",
            name=None,
            latitude=50.0,
            longitude=20.0,
            aqi=30,
            distance_km=0.0,
        )
        assert station.name is None


class TestAirQualityResult:
    def test_create_result(self):
        result = AirQualityResult(
            score=85.0,
            aqi_value=30,
            pm25=10.5,
            pm10=18.0,
            data_source="waqi",
            confidence=1.0,
            station_name="Test",
        )
        assert result.score == 85.0
        assert result.data_source == "waqi"


class TestAirQualityAdapterInit:
    def test_init_with_api_key(self):
        adapter = AirQualityAdapter(api_key="test-key")
        assert adapter._api_key == "test-key"
        assert adapter._cache_ttl == 3600
        assert adapter._timeout == 30

    def test_init_without_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            adapter = AirQualityAdapter()
            assert adapter._api_key is None

    def test_init_custom_cache_ttl(self):
        with patch.dict("os.environ", {"AIR_QUALITY_CACHE_TTL": "7200"}):
            adapter = AirQualityAdapter(api_key="key")
            assert adapter._cache_ttl == 7200

    def test_init_custom_timeout(self):
        adapter = AirQualityAdapter(api_key="key", timeout=60)
        assert adapter._timeout == 60

    @patch.dict("os.environ", {"WAQI_API_KEY": "env-key", "AIR_QUALITY_CACHE_TTL": "1800"})
    def test_init_from_env(self):
        adapter = AirQualityAdapter()
        assert adapter._api_key == "env-key"
        assert adapter._cache_ttl == 1800


class TestAQIScoreCalculation:
    def setup_method(self):
        self.adapter = AirQualityAdapter(api_key="test-key")

    def test_aqi_score_good_0(self):
        score = self.adapter._calculate_aqi_score(0)
        assert score == 100.0

    def test_aqi_score_good_50(self):
        score = self.adapter._calculate_aqi_score(50)
        assert score == 90.0

    def test_aqi_score_moderate_51(self):
        score = self.adapter._calculate_aqi_score(51)
        assert 70.0 < score < 89.0

    def test_aqi_score_moderate_100(self):
        score = self.adapter._calculate_aqi_score(100)
        assert 70.0 <= score <= 89.0

    def test_aqi_score_unhealthy_sensitive_101(self):
        score = self.adapter._calculate_aqi_score(101)
        assert 50.0 < score < 70.0

    def test_aqi_score_unhealthy_151(self):
        score = self.adapter._calculate_aqi_score(151)
        assert 30.0 < score < 50.0

    def test_aqi_score_very_unhealthy_201(self):
        score = self.adapter._calculate_aqi_score(201)
        assert 10.0 < score < 30.0

    def test_aqi_score_hazardous_301(self):
        score = self.adapter._calculate_aqi_score(301)
        assert 0.0 <= score < 10.0

    def test_aqi_score_hazardous_500(self):
        score = self.adapter._calculate_aqi_score(500)
        assert score >= 0.0

    def test_aqi_score_none(self):
        score = self.adapter._calculate_aqi_score(None)
        assert score == 50.0


class TestGetAQIScore:
    def setup_method(self):
        self.adapter = AirQualityAdapter(api_key="test-key")

    @patch.object(AirQualityAdapter, "_fetch_from_api")
    def test_get_aqi_score_with_api_result(self, mock_fetch):
        mock_fetch.return_value = AirQualityResult(
            score=90.0,
            aqi_value=25,
            pm25=8.0,
            pm10=15.0,
            data_source="waqi",
            confidence=1.0,
            station_name="Station1",
        )
        result = self.adapter.get_aqi_score(52.2297, 21.0122)
        assert result.score == 90.0
        assert result.data_source == "waqi"

    @patch.object(AirQualityAdapter, "_fetch_from_api")
    def test_get_aqi_score_fallback_to_city(self, mock_fetch):
        mock_fetch.return_value = None
        result = self.adapter.get_aqi_score(52.2297, 21.0122, city="Warsaw")
        assert result.data_source == "fallback"
        assert result.confidence == 0.5

    @patch.object(AirQualityAdapter, "_fetch_from_api")
    def test_get_aqi_score_fallback_no_city(self, mock_fetch):
        mock_fetch.return_value = None
        result = self.adapter.get_aqi_score(52.2297, 21.0122)
        assert result.data_source == "fallback"
        assert result.confidence == 0.3
        assert result.aqi_value == 50

    @patch.object(AirQualityAdapter, "_fetch_from_api")
    def test_get_aqi_score_fallback_unknown_city(self, mock_fetch):
        mock_fetch.return_value = None
        result = self.adapter.get_aqi_score(52.2297, 21.0122, city="NonexistentCity")
        assert result.data_source == "fallback"
        assert result.aqi_value == 50

    def test_get_aqi_score_no_api_key(self):
        adapter = AirQualityAdapter(api_key=None)
        with patch.dict("os.environ", {}, clear=True):
            adapter._api_key = None
            result = adapter.get_aqi_score(52.2297, 21.0122, city="Krakow")
            assert result.data_source == "fallback"
            assert result.aqi_value == 75

    @patch.object(AirQualityAdapter, "_fetch_from_api")
    def test_get_aqi_score_fallback_krakow(self, mock_fetch):
        mock_fetch.return_value = None
        result = self.adapter.get_aqi_score(50.0, 20.0, city="krakow")
        assert result.aqi_value == 75
        assert result.pm25 == 22.0
        assert result.pm10 == 35.0

    @patch.object(AirQualityAdapter, "_fetch_from_api")
    def test_get_aqi_score_fallback_empty_city(self, mock_fetch):
        mock_fetch.return_value = None
        result = self.adapter.get_aqi_score(50.0, 20.0, city="")
        assert result.confidence == 0.3


class TestFetchFromAPI:
    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_fetch_success(self, mock_get):
        adapter = AirQualityAdapter(api_key="test-key")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "ok",
            "data": {
                "aqi": 45,
                "city": {"name": "Test City", "geo": [52.0, 21.0]},
                "iaqi": {
                    "pm25": {"v": 12.5},
                    "pm10": {"v": 20.0},
                },
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = adapter._fetch_from_api(52.0, 21.0)
        assert result is not None
        assert result.aqi_value == 45
        assert result.pm25 == 12.5
        assert result.pm10 == 20.0
        assert result.data_source == "waqi"
        assert result.confidence == 1.0

    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_fetch_api_error_status(self, mock_get):
        adapter = AirQualityAdapter(api_key="test-key")
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "error"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = adapter._fetch_from_api(52.0, 21.0)
        assert result is None

    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_fetch_request_exception(self, mock_get):
        import requests

        adapter = AirQualityAdapter(api_key="test-key")
        mock_get.side_effect = requests.RequestException("timeout")

        result = adapter._fetch_from_api(52.0, 21.0)
        assert result is None

    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_fetch_parse_error(self, mock_get):
        adapter = AirQualityAdapter(api_key="test-key")
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "data": None}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = adapter._fetch_from_api(52.0, 21.0)
        assert result is None

    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_fetch_no_pm_data(self, mock_get):
        adapter = AirQualityAdapter(api_key="test-key")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "ok",
            "data": {
                "aqi": 30,
                "city": {"name": "City", "geo": [52.0, 21.0]},
                "iaqi": {},
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = adapter._fetch_from_api(52.0, 21.0)
        assert result is not None
        assert result.pm25 is None
        assert result.pm10 is None

    def test_fetch_from_cache(self):
        adapter = AirQualityAdapter(api_key="test-key")
        cached = AirQualityResult(
            score=90.0,
            aqi_value=20,
            pm25=5.0,
            pm10=10.0,
            data_source="waqi",
            confidence=1.0,
            station_name="Cached",
        )
        adapter._cache["aqi:52.0:21.0"] = (cached, time.time())

        result = adapter._fetch_from_api(52.0, 21.0)
        assert result is cached


class TestGetNearestStation:
    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_get_station_success(self, mock_get):
        adapter = AirQualityAdapter(api_key="test-key")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "ok",
            "data": {
                "idx": "station1",
                "city": {"name": "Test Station", "geo": [52.23, 21.01]},
                "aqi": 55,
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        station = adapter.get_nearest_station(52.2297, 21.0122)
        assert station is not None
        assert station.station_id == "station1"
        assert station.name == "Test Station"
        assert station.aqi == 55

    def test_get_station_no_api_key(self):
        adapter = AirQualityAdapter(api_key=None)
        adapter._api_key = None
        station = adapter.get_nearest_station(52.0, 21.0)
        assert station is None

    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_get_station_api_error(self, mock_get):
        import requests

        adapter = AirQualityAdapter(api_key="test-key")
        mock_get.side_effect = requests.RequestException("error")

        station = adapter.get_nearest_station(52.0, 21.0)
        assert station is None

    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_get_station_from_cache(self, mock_get):
        adapter = AirQualityAdapter(api_key="test-key")
        cached_station = AirQualityStation(
            station_id="cached",
            name="Cached",
            latitude=52.0,
            longitude=21.0,
            aqi=40,
            distance_km=0.5,
        )
        adapter._cache["station:52.0:21.0"] = (cached_station, time.time())

        station = adapter.get_nearest_station(52.0, 21.0)
        assert station is cached_station
        mock_get.assert_not_called()

    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_get_station_error_status(self, mock_get):
        adapter = AirQualityAdapter(api_key="test-key")
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "error"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        station = adapter.get_nearest_station(52.0, 21.0)
        assert station is None

    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_get_station_no_data(self, mock_get):
        adapter = AirQualityAdapter(api_key="test-key")
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "data": {}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        station = adapter.get_nearest_station(52.0, 21.0)
        assert station is None

    @patch("data.adapters.air_quality_adapter.requests.get")
    def test_get_station_parse_error(self, mock_get):
        adapter = AirQualityAdapter(api_key="test-key")
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("bad json")
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        station = adapter.get_nearest_station(52.0, 21.0)
        assert station is None


class TestCache:
    def setup_method(self):
        self.adapter = AirQualityAdapter(api_key="test-key")
        self.adapter._cache_ttl = 10  # Short TTL for testing

    def test_put_and_get_from_cache(self):
        self.adapter._put_in_cache("key1", "value1")
        result = self.adapter._get_from_cache("key1")
        assert result == "value1"

    def test_cache_miss(self):
        result = self.adapter._get_from_cache("nonexistent")
        assert result is None

    def test_cache_expired(self):
        self.adapter._cache["key1"] = ("value1", time.time() - 100)
        result = self.adapter._get_from_cache("key1")
        assert result is None

    def test_station_cache(self):
        station = AirQualityStation(
            station_id="1",
            name="S1",
            latitude=52.0,
            longitude=21.0,
            aqi=40,
            distance_km=1.0,
        )
        self.adapter._put_in_cache("station:key", station)
        result = self.adapter._get_station_from_cache("station:key")
        assert result is station

    def test_station_cache_expired(self):
        station = AirQualityStation(
            station_id="1",
            name="S1",
            latitude=52.0,
            longitude=21.0,
            aqi=40,
            distance_km=1.0,
        )
        self.adapter._cache["station:key"] = (station, time.time() - 100)
        result = self.adapter._get_station_from_cache("station:key")
        assert result is None
        assert "station:key" not in self.adapter._cache

    def test_aqi_result_cache(self):
        result_obj = AirQualityResult(
            score=85.0,
            aqi_value=30,
            pm25=10.0,
            pm10=18.0,
            data_source="waqi",
            confidence=1.0,
            station_name="Test",
        )
        self.adapter._put_in_cache("aqi:key", result_obj)
        result = self.adapter._get_aqi_result_from_cache("aqi:key")
        assert result is result_obj

    def test_aqi_result_cache_expired(self):
        result_obj = AirQualityResult(
            score=85.0,
            aqi_value=30,
            pm25=10.0,
            pm10=18.0,
            data_source="waqi",
            confidence=1.0,
            station_name="Test",
        )
        self.adapter._cache["aqi:key"] = (result_obj, time.time() - 100)
        result = self.adapter._get_aqi_result_from_cache("aqi:key")
        assert result is None
        assert "aqi:key" not in self.adapter._cache


class TestHaversine:
    def setup_method(self):
        self.adapter = AirQualityAdapter(api_key="test-key")

    def test_same_point(self):
        dist = self.adapter._haversine_distance(52.0, 21.0, 52.0, 21.0)
        assert dist == 0.0

    def test_known_distance(self):
        dist = self.adapter._haversine_distance(52.2297, 21.0122, 51.1079, 17.0385)
        assert 250 < dist < 350  # Warsaw to Wroclaw ~300km


class TestGetStatus:
    def test_status_with_api_key(self):
        adapter = AirQualityAdapter(api_key="test-key")
        status = adapter.get_status()
        assert status["adapter"] == "AirQualityAdapter"
        assert status["api_configured"] is True
        assert status["cache_ttl"] == 3600

    def test_status_without_api_key(self):
        adapter = AirQualityAdapter(api_key=None)
        adapter._api_key = None
        status = adapter.get_status()
        assert status["api_configured"] is False


class TestGetAdapter:
    def test_get_adapter_creates_instance(self):
        import data.adapters.air_quality_adapter as mod

        original = mod._default_adapter
        mod._default_adapter = None
        try:
            adapter = get_air_quality_adapter()
            assert isinstance(adapter, AirQualityAdapter)
        finally:
            mod._default_adapter = original

    def test_get_adapter_returns_same_instance(self):
        import data.adapters.air_quality_adapter as mod

        original = mod._default_adapter
        mod._default_adapter = None
        try:
            adapter1 = get_air_quality_adapter()
            adapter2 = get_air_quality_adapter()
            assert adapter1 is adapter2
        finally:
            mod._default_adapter = original


class TestCityAverages:
    def test_all_cities_have_required_fields(self):
        for _city, data in CITY_AQI_AVERAGES.items():
            assert "aqi" in data
            assert "pm25" in data
            assert "pm10" in data
            assert data["aqi"] > 0

    def test_fallback_uses_city_average(self):
        adapter = AirQualityAdapter(api_key="test-key")
        result = adapter._get_fallback_result("Katowice")
        assert result.aqi_value == 80
        assert result.pm25 == 25.0
        assert result.confidence == 0.5
