"""Tests for the FX rates currency conversion service."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from services.fx_rates import (
    CACHE_TTL_SECONDS,
    SUPPORTED_CURRENCIES,
    CurrencyConverter,
    _fetch_ecb_rates,
    _fetch_nbp_rates,
    get_currency_converter,
)

# ── ECB XML fixture ──────────────────────────────────────────────
ECB_XML = """<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
  xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
  <Cube>
    <Cube time="2025-01-15">
      <Cube currency="USD" rate="1.0900"/>
      <Cube currency="GBP" rate="0.8600"/>
      <Cube currency="PLN" rate="4.3200"/>
      <Cube currency="CHF" rate="0.9450"/>
      <Cube currency="CZK" rate="25.10"/>
      <Cube currency="JPY" rate="162.50"/>
    </Cube>
  </Cube>
</gesmes:Envelope>
"""

# ── NBP JSON fixture ─────────────────────────────────────────────
NBP_JSON = [
    {
        "table": "A",
        "no": "001/A/NBP/2025",
        "rates": [
            {"currency": "euro", "code": "EUR", "mid": 4.32},
            {"currency": "dolar amerykanski", "code": "USD", "mid": 3.96},
            {"currency": "funt szterling", "code": "GBP", "mid": 5.03},
        ],
    }
]


def _mock_urlopen(content: bytes):
    """Create a mock urlopen context manager returning content."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = content
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestFetchEcbRates:
    """Tests for _fetch_ecb_rates()."""

    @patch("services.fx_rates.urllib.request.urlopen")
    def test_parses_ecb_xml(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(ECB_XML.encode())
        rates = _fetch_ecb_rates()
        assert rates["EUR"] == 1.0
        assert rates["USD"] == 1.09
        assert rates["PLN"] == 4.32
        assert "GBP" in rates

    @patch("services.fx_rates.urllib.request.urlopen")
    def test_filters_to_supported_currencies(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(ECB_XML.encode())
        rates = _fetch_ecb_rates()
        for code in rates:
            assert code in SUPPORTED_CURRENCIES

    @patch("services.fx_rates.urllib.request.urlopen", side_effect=Exception("network error"))
    def test_returns_eur_on_failure(self, mock_urlopen):
        rates = _fetch_ecb_rates()
        assert rates == {"EUR": 1.0}


class TestFetchNbpRates:
    """Tests for _fetch_nbp_rates()."""

    @patch("services.fx_rates.urllib.request.urlopen")
    def test_parses_nbp_json(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(json.dumps(NBP_JSON).encode())
        rates = _fetch_nbp_rates()
        assert rates["PLN"] == 1.0
        assert rates["EUR"] == 4.32
        assert rates["USD"] == 3.96

    @patch("services.fx_rates.urllib.request.urlopen", side_effect=Exception("network error"))
    def test_returns_pln_on_failure(self, mock_urlopen):
        rates = _fetch_nbp_rates()
        assert rates == {"PLN": 1.0}


class TestCurrencyConverter:
    """Tests for CurrencyConverter class."""

    def _make_converter_with_rates(self) -> CurrencyConverter:
        """Create a converter with pre-built rates (no network calls)."""
        converter = CurrencyConverter(cache_dir="/tmp/test_fx_cache")
        converter._rates = converter._build_cross_rates(
            {"EUR": 1.0, "USD": 1.09, "GBP": 0.86, "PLN": 4.32}
        )
        return converter

    def test_convert_same_currency(self):
        conv = self._make_converter_with_rates()
        assert conv.convert(100.0, "EUR", "EUR") == 100.0

    def test_convert_eur_to_usd(self):
        conv = self._make_converter_with_rates()
        result = conv.convert(100.0, "EUR", "USD")
        assert result is not None
        assert abs(result - 109.0) < 0.01

    def test_convert_usd_to_eur(self):
        conv = self._make_converter_with_rates()
        result = conv.convert(109.0, "USD", "EUR")
        assert result is not None
        assert abs(result - 100.0) < 0.01

    def test_convert_case_insensitive(self):
        conv = self._make_converter_with_rates()
        assert conv.convert(100.0, "eur", "usd") == conv.convert(100.0, "EUR", "USD")

    def test_convert_unsupported_currency(self):
        conv = self._make_converter_with_rates()
        assert conv.convert(100.0, "XYZ", "EUR") is None

    def test_format_price_usd(self):
        conv = self._make_converter_with_rates()
        assert conv.format_price(1234.56, "USD") == "$1,234.56"

    def test_format_price_eur(self):
        conv = self._make_converter_with_rates()
        assert conv.format_price(1234.56, "EUR") == "1,234.56 €"

    def test_format_price_pln_german_locale(self):
        conv = self._make_converter_with_rates()
        result = conv.format_price(1234.56, "PLN", locale="de")
        assert "1.234,56" in result
        assert "zł" in result

    def test_build_cross_rates_reciprocal(self):
        conv = CurrencyConverter()
        cross = conv._build_cross_rates({"EUR": 1.0, "USD": 2.0})
        # EUR->USD = 2.0, USD->EUR = 0.5
        assert cross["EUR"]["USD"] == 2.0
        assert abs(cross["USD"]["EUR"] - 0.5) < 0.001


class TestCache:
    """Tests for cache loading and TTL."""

    def test_load_fresh_cache(self, tmp_path):
        cache_file = tmp_path / "rates.json"
        cache_data = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "rates": {"EUR": 1.0, "USD": 1.09},
        }
        cache_file.write_text(json.dumps(cache_data))

        conv = CurrencyConverter(cache_dir=str(tmp_path))
        cached = conv._load_cache()
        assert cached is not None
        assert cached["USD"] == 1.09

    def test_load_expired_cache(self, tmp_path):
        cache_file = tmp_path / "rates.json"
        old_time = datetime.now(timezone.utc) - timedelta(seconds=CACHE_TTL_SECONDS + 100)
        cache_data = {"fetched_at": old_time.isoformat(), "rates": {"EUR": 1.0}}
        cache_file.write_text(json.dumps(cache_data))

        conv = CurrencyConverter(cache_dir=str(tmp_path))
        assert conv._load_cache() is None

    def test_load_missing_cache(self, tmp_path):
        conv = CurrencyConverter(cache_dir=str(tmp_path))
        assert conv._load_cache() is None


class TestSingleton:
    """Tests for module-level singleton."""

    def test_get_currency_converter_returns_instance(self):
        # Reset singleton
        import services.fx_rates as mod

        mod._converter = None
        conv = get_currency_converter()
        assert isinstance(conv, CurrencyConverter)

    def test_singleton_returns_same_instance(self):
        import services.fx_rates as mod

        mod._converter = None
        a = get_currency_converter()
        b = get_currency_converter()
        assert a is b
        # Clean up
        mod._converter = None
