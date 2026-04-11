"""Currency conversion service using free ECB/NBP exchange rates.

Provides FX rate caching and price normalization across currencies.
Uses European Central Bank (ECB) and National Bank of Poland (NBP) APIs.

CE scope: Free ECB/NBP APIs with daily caching.
Pro gets premium real-time FX feeds later.
"""

import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ECB provides free daily EUR-based rates
ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
# NBP provides PLN rates (table A)
NBP_URL = "https://api.nbp.pl/api/exchangerates/tables/A?format=json"

SUPPORTED_CURRENCIES = {
    "EUR",
    "USD",
    "GBP",
    "PLN",
    "CHF",
    "CZK",
    "UAH",
    "TRY",
    "ARS",
    "BRL",
    "CNY",
    "JPY",
    "KRW",
}

CACHE_DIR = Path("cache/fx_rates")
CACHE_TTL_SECONDS = 86400  # 24 hours


def _fetch_ecb_rates() -> dict[str, float]:
    """Fetch exchange rates from ECB (EUR-based)."""
    rates = {"EUR": 1.0}
    try:
        req = urllib.request.Request(ECB_URL, headers={"User-Agent": "fx-rates/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode()

        # Parse XML manually (avoid xmltodict dependency)
        import re

        for match in re.finditer(r'currency=[\'"](\w+)[\'"].*rate=[\'"]([\d.]+)[\'"]', content):
            currency, rate = match.group(1), float(match.group(2))
            if currency in SUPPORTED_CURRENCIES:
                rates[currency] = rate

        logger.info("ECB rates fetched: %d currencies", len(rates))
    except Exception as e:
        logger.warning("Failed to fetch ECB rates: %s", e)

    return rates


def _fetch_nbp_rates() -> dict[str, float]:
    """Fetch exchange rates from NBP (PLN-based)."""
    rates = {"PLN": 1.0}
    try:
        req = urllib.request.Request(NBP_URL, headers={"User-Agent": "fx-rates/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        for table in data:
            for rate_info in table.get("rates", []):
                code = rate_info.get("code", "")
                mid = rate_info.get("mid")
                if code in SUPPORTED_CURRENCIES and mid is not None:
                    rates[code] = float(mid)

        logger.info("NBP rates fetched: %d currencies", len(rates))
    except Exception as e:
        logger.warning("Failed to fetch NBP rates: %s", e)

    return rates


class CurrencyConverter:
    """Currency converter with daily rate caching."""

    def __init__(self, cache_dir: Optional[str] = None):
        self._cache_dir = Path(cache_dir) if cache_dir else CACHE_DIR
        self._rates: dict[str, dict[str, float]] = {}

    def _load_cache(self) -> dict[str, float] | None:
        """Load cached rates if fresh enough."""
        cache_file = self._cache_dir / "rates.json"
        if not cache_file.exists():
            return None

        try:
            with open(cache_file) as f:
                cached = json.load(f)

            # Check cache age
            fetched = cached.get("fetched_at", "")
            if fetched:
                fetched_dt = datetime.fromisoformat(fetched)
                age = (datetime.now(timezone.utc) - fetched_dt).total_seconds()
                if age < CACHE_TTL_SECONDS:
                    return cached.get("rates", {})
        except Exception:
            pass

        return None

    def _save_cache(self, rates: dict[str, float]) -> None:
        """Save rates to cache."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self._cache_dir / "rates.json"
        try:
            with open(cache_file, "w") as f:
                json.dump(
                    {
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "rates": rates,
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.warning("Failed to save FX cache: %s", e)

    def _build_cross_rates(self, base_rates: dict[str, float]) -> dict[str, dict[str, float]]:
        """Build cross-currency conversion table from EUR-based rates."""
        cross: dict[str, dict[str, float]] = {}
        currencies = [c for c in SUPPORTED_CURRENCIES if c in base_rates]

        for src in currencies:
            cross[src] = {}
            src_in_eur = base_rates.get(src, 1.0) if src != "EUR" else 1.0
            for dst in currencies:
                dst_in_eur = base_rates.get(dst, 1.0) if dst != "EUR" else 1.0
                # src -> EUR -> dst
                cross[src][dst] = dst_in_eur / src_in_eur

        return cross

    def refresh_rates(self) -> dict[str, float]:
        """Fetch fresh rates and update cache."""
        # Try ECB first (more comprehensive)
        rates = _fetch_ecb_rates()

        # Supplement with NBP for PLN accuracy
        nbp_rates = _fetch_nbp_rates()
        if "PLN" not in rates and "PLN" in nbp_rates:
            # Convert NBP PLN-based to EUR-based
            eur_to_pln = nbp_rates.get("EUR", 4.3)  # approximate fallback
            rates["PLN"] = 1.0 / eur_to_pln  # PLN expressed as 1 PLN = X EUR
            for code, pln_rate in nbp_rates.items():
                if code not in rates and code in SUPPORTED_CURRENCIES:
                    rates[code] = pln_rate / eur_to_pln

        if len(rates) > 1:
            self._save_cache(rates)

        self._rates = self._build_cross_rates(rates)
        return rates

    def get_rates(self) -> dict[str, dict[str, float]]:
        """Get conversion rates, loading from cache or fetching fresh."""
        if self._rates:
            return self._rates

        cached = self._load_cache()
        if cached:
            self._rates = self._build_cross_rates(cached)
            return self._rates

        self.refresh_rates()
        return self._rates

    def convert(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
    ) -> Optional[float]:
        """Convert amount between currencies.

        Args:
            amount: Amount to convert
            from_currency: Source currency code (e.g. "PLN")
            to_currency: Target currency code (e.g. "EUR")

        Returns:
            Converted amount, or None if conversion not available
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        if from_currency == to_currency:
            return amount

        rates = self.get_rates()
        if from_currency not in rates or to_currency not in rates.get(from_currency, {}):
            logger.warning("No rate for %s -> %s", from_currency, to_currency)
            return None

        rate = rates[from_currency][to_currency]
        return round(amount * rate, 2)

    def format_price(
        self,
        amount: float,
        currency: str,
        locale: str = "en",
    ) -> str:
        """Format a price amount with currency symbol.

        Args:
            amount: Price amount
            currency: Currency code
            locale: Locale for formatting

        Returns:
            Formatted price string
        """
        currency_symbols = {
            "EUR": "€",
            "USD": "$",
            "GBP": "£",
            "PLN": "zł",
            "CHF": "CHF",
            "CZK": "Kč",
            "UAH": "₴",
            "TRY": "₺",
            "ARS": "$",
            "BRL": "R$",
            "CNY": "¥",
            "JPY": "¥",
            "KRW": "₩",
        }
        symbol = currency_symbols.get(currency, currency)

        # Format with thousands separator
        if locale in ("de", "es", "it", "pt", "fr"):
            formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            formatted = f"{amount:,.2f}"

        # EUR-style: symbol after amount
        if currency in ("EUR", "PLN", "CZK", "UAH", "TRY", "CHF"):
            return f"{formatted} {symbol}"
        return f"{symbol}{formatted}"


# Module-level singleton
_converter: Optional[CurrencyConverter] = None


def get_currency_converter() -> CurrencyConverter:
    """Get or create the global currency converter instance."""
    global _converter
    if _converter is None:
        _converter = CurrencyConverter()
    return _converter
