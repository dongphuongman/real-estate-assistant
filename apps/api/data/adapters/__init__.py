"""
External portal adapters for fetching property data from real estate portals.

This package provides an extensible adapter system for ingesting property data
from external APIs and web scraping sources.
"""

from data.adapters.base import (
    ExternalSourceAdapter,
    PortalFetchResult,
    PortalFilter,
)
from data.adapters.overpass_adapter import OverpassAdapter
from data.adapters.registry import (
    AdapterRegistry,
    get_adapter,
    register_adapter,
)

# Register built-in adapters
AdapterRegistry.register(OverpassAdapter)

__all__ = [
    "ExternalSourceAdapter",
    "PortalFetchResult",
    "PortalFilter",
    "AdapterRegistry",
    "get_adapter",
    "register_adapter",
    "OverpassAdapter",
]
