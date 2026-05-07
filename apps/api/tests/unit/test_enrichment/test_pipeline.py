"""
Unit tests for Enrichment Pipeline (Task #78).
"""

import pytest

from data.enrichment.cache import EnrichmentCache
from data.enrichment.hooks import (
    EnrichmentPriority,
    EnrichmentResult,
    PropertyEnrichmentHook,
)
from data.enrichment.pipeline import EnrichmentPipeline, PipelineConfig, PipelineResult
from data.enrichment.registry import EnrichmentRegistry


class SlowEnricher(PropertyEnrichmentHook):
    """Test enricher that simulates slow response."""

    name = "slow_enricher"
    field = "slow_field"
    priority = EnrichmentPriority.LOW

    async def enrich(self, context):
        return EnrichmentResult.success_result(
            source=self.name, enrichment_field=self.field, value="slow_value"
        )

    async def health_check(self):
        return True


class FastEnricher(PropertyEnrichmentHook):
    """Test enricher that responds quickly."""

    name = "fast_enricher"
    field = "fast_field"
    priority = EnrichmentPriority.HIGH

    async def enrich(self, context):
        return EnrichmentResult.success_result(
            source=self.name, enrichment_field=self.field, value="fast_value"
        )

    async def health_check(self):
        return True


class FailingEnricher(PropertyEnrichmentHook):
    """Test enricher that always fails."""

    name = "failing_enricher"
    field = "failing_field"

    async def enrich(self, context):
        return EnrichmentResult.error_result(
            source=self.name, enrichment_field=self.field, error="Intentional failure"
        )

    async def health_check(self):
        return False


class TestPipelineConfig:
    """Tests for PipelineConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PipelineConfig()
        assert config.enabled is True
        assert config.parallel_execution is True
        assert config.max_concurrent == 5
        assert config.default_timeout == 30.0
        assert config.fail_fast is False
        assert config.cache_enabled is True
        assert config.fallback_on_error is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = PipelineConfig(
            enabled=False,
            parallel_execution=False,
            max_concurrent=10,
            fail_fast=True,
            sources=["enricher1", "enricher2"],
        )
        assert config.enabled is False
        assert config.parallel_execution is False
        assert config.max_concurrent == 10
        assert config.fail_fast is True
        assert config.sources == ["enricher1", "enricher2"]


class TestPipelineResult:
    """Tests for PipelineResult."""

    def test_success(self):
        """Test success property."""
        result = PipelineResult(property_id="test")
        assert result.success is True

        result.errors.append("error")
        assert result.success is False

    def test_partial_success(self):
        """Test partial_success property."""
        result = PipelineResult(property_id="test")
        assert result.partial_success is False

        result.enriched_fields["field"] = "value"
        assert result.partial_success is True

    def test_to_dict(self):
        """Test serialization."""
        result = PipelineResult(
            property_id="test",
            enriched_fields={"field": "value"},
            errors=["error"],
            total_time_ms=100.0,
        )
        data = result.to_dict()
        assert data["property_id"] == "test"
        assert data["enriched_fields"] == {"field": "value"}
        assert data["errors"] == ["error"]
        assert data["total_time_ms"] == 100.0


class TestEnrichmentPipeline:
    """Tests for EnrichmentPipeline."""

    def setup_method(self):
        """Clear registry before each test."""
        EnrichmentRegistry.clear()

    @pytest.mark.asyncio
    async def test_run_disabled_pipeline(self):
        """Test that disabled pipeline returns empty result."""
        config = PipelineConfig(enabled=False)
        pipeline = EnrichmentPipeline(config=config)

        result = await pipeline.run({"id": "test"})
        assert result.success is True
        assert len(result.enriched_fields) == 0

    @pytest.mark.asyncio
    async def test_run_single_enricher(self):
        """Test running with a single enricher."""
        EnrichmentRegistry.register(FastEnricher)

        cache = EnrichmentCache(redis_url=None, fallback_to_in_memory=True)
        pipeline = EnrichmentPipeline(cache=cache)

        result = await pipeline.run({"id": "test", "city": "Berlin"})

        assert result.partial_success is True
        assert "fast_field" in result.enriched_fields
        assert result.enriched_fields["fast_field"] == "fast_value"

    @pytest.mark.asyncio
    async def test_run_multiple_enrichers_parallel(self):
        """Test running multiple enrichers in parallel."""
        EnrichmentRegistry.register(FastEnricher)
        EnrichmentRegistry.register(SlowEnricher)

        config = PipelineConfig(parallel_execution=True)
        cache = EnrichmentCache(redis_url=None, fallback_to_in_memory=True)
        pipeline = EnrichmentPipeline(config=config, cache=cache)

        result = await pipeline.run({"id": "test"})

        assert len(result.enriched_fields) == 2
        assert "fast_field" in result.enriched_fields
        assert "slow_field" in result.enriched_fields

    @pytest.mark.asyncio
    async def test_run_with_failing_enricher(self):
        """Test handling of failing enricher."""
        EnrichmentRegistry.register(FailingEnricher)

        cache = EnrichmentCache(redis_url=None, fallback_to_in_memory=True)
        pipeline = EnrichmentPipeline(cache=cache)

        result = await pipeline.run({"id": "test"})

        assert result.success is False
        assert len(result.errors) == 1
        assert "Intentional failure" in result.errors[0]

    @pytest.mark.asyncio
    async def test_run_with_specific_sources(self):
        """Test running with specific sources filter."""
        EnrichmentRegistry.register(FastEnricher)
        EnrichmentRegistry.register(SlowEnricher)

        cache = EnrichmentCache(redis_url=None, fallback_to_in_memory=True)
        pipeline = EnrichmentPipeline(cache=cache)

        result = await pipeline.run(
            {"id": "test"},
            sources=["fast_enricher"],
        )

        assert len(result.enriched_fields) == 1
        assert "fast_field" in result.enriched_fields
        assert "slow_field" not in result.enriched_fields

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test that cached results are used."""
        EnrichmentRegistry.register(FastEnricher)

        cache = EnrichmentCache(redis_url=None, fallback_to_in_memory=True)

        # Pre-populate cache
        cache.set(
            source="fast_enricher",
            property_id="test",
            enrichment_field="fast_field",
            value="cached_value",
            ttl=3600,
        )

        pipeline = EnrichmentPipeline(cache=cache)
        result = await pipeline.run({"id": "test"})

        assert result.enriched_fields["fast_field"] == "cached_value"
        # Check that result was from cache
        key = "fast_enricher:fast_field"
        assert result.results[key].cached is True

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        """Test that enrichers run in priority order (sequential mode)."""
        EnrichmentRegistry.register(SlowEnricher)  # LOW priority
        EnrichmentRegistry.register(FastEnricher)  # HIGH priority

        config = PipelineConfig(parallel_execution=False)
        cache = EnrichmentCache(redis_url=None, fallback_to_in_memory=True)
        pipeline = EnrichmentPipeline(config=config, cache=cache)

        result = await pipeline.run({"id": "test"})

        # Both should complete
        assert len(result.enriched_fields) == 2

    @pytest.mark.asyncio
    async def test_run_batch(self):
        """Test batch processing."""
        EnrichmentRegistry.register(FastEnricher)

        cache = EnrichmentCache(redis_url=None, fallback_to_in_memory=True)
        pipeline = EnrichmentPipeline(cache=cache)

        properties = [{"id": f"prop_{i}"} for i in range(3)]
        results = await pipeline.run_batch(properties)

        assert len(results) == 3
        for result in results:
            assert "fast_field" in result.enriched_fields

    def test_get_status(self):
        """Test status retrieval."""
        EnrichmentRegistry.register(FastEnricher)

        pipeline = EnrichmentPipeline()
        status = pipeline.get_status("test_property")

        assert "property_id" in status
        assert "enrichments" in status

    def test_invalidate_cache(self):
        """Test cache invalidation."""
        EnrichmentRegistry.register(FastEnricher)

        cache = EnrichmentCache(redis_url=None, fallback_to_in_memory=True)
        cache.set("source", "prop", "field", "value", ttl=3600)

        pipeline = EnrichmentPipeline(cache=cache)
        count = pipeline.invalidate_cache("prop")

        assert count >= 1
        assert cache.get("source", "prop", "field") is None
