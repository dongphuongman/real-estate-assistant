"""
Property Enrichment System (Task #78).

This module provides a standardized interface for optional property data
enrichment from external sources. The enrichment system allows augmenting
property data with additional information (air quality, safety scores,
transport data, etc.) during ingestion or on-demand.

Key Components:
- PropertyEnrichmentHook: Abstract base class for enrichment providers
- EnrichmentRegistry: Central registry for enrichment providers
- EnrichmentCache: TTL-based caching layer
- EnrichmentPipeline: Orchestrates multiple enrichers
- EnrichmentStatus: Status tracking for enrichment operations
"""

from data.enrichment.cache import EnrichmentCache
from data.enrichment.hooks import (
    EnrichmentConfig,
    EnrichmentContext,
    EnrichmentPriority,
    EnrichmentResult,
    EnrichmentStatus,
    PropertyEnrichmentHook,
)
from data.enrichment.pipeline import EnrichmentPipeline
from data.enrichment.registry import (
    EnrichmentRegistry,
    register_enricher,
)
from data.enrichment.status import EnrichmentStatusTracker, FallbackHandler

__all__ = [
    # Core interface
    "PropertyEnrichmentHook",
    "EnrichmentConfig",
    "EnrichmentContext",
    "EnrichmentResult",
    "EnrichmentStatus",
    "EnrichmentPriority",
    # Registry
    "EnrichmentRegistry",
    "register_enricher",
    # Cache
    "EnrichmentCache",
    # Pipeline
    "EnrichmentPipeline",
    # Status tracking
    "EnrichmentStatusTracker",
    "FallbackHandler",
]
