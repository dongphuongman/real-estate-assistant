"""
Built-in enrichment providers (Task #78).

This package contains ready-to-use enrichment hooks that integrate with
existing data adapters in the application.
"""

from data.enrichment.enrichers.air_quality import AirQualityEnricher

__all__ = [
    "AirQualityEnricher",
]
