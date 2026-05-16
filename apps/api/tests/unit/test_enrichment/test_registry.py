"""
Unit tests for Enrichment Registry (Task #78).
"""

from data.enrichment.hooks import (
    EnrichmentConfig,
    EnrichmentPriority,
    EnrichmentResult,
    PropertyEnrichmentHook,
)
from data.enrichment.registry import EnrichmentRegistry, register_enricher


class TestEnricherA(PropertyEnrichmentHook):
    """Test enricher A."""

    name = "test_a"
    display_name = "Test A"
    field = "field_a"
    priority = EnrichmentPriority.HIGH

    async def enrich(self, context):
        return EnrichmentResult.success_result(
            source=self.name, enrichment_field=self.field, value="a"
        )

    async def health_check(self):
        return True


class TestEnricherB(PropertyEnrichmentHook):
    """Test enricher B."""

    name = "test_b"
    display_name = "Test B"
    field = "field_b"
    priority = EnrichmentPriority.LOW

    async def enrich(self, context):
        return EnrichmentResult.success_result(
            source=self.name, enrichment_field=self.field, value="b"
        )

    async def health_check(self):
        return True


class TestEnrichmentRegistry:
    """Tests for EnrichmentRegistry."""

    def setup_method(self):
        """Clear registry before each test."""
        EnrichmentRegistry.clear()

    def test_register(self):
        """Test registering an enricher."""
        EnrichmentRegistry.register(TestEnricherA)
        assert "test_a" in EnrichmentRegistry.list_enrichers()

    def test_unregister(self):
        """Test unregistering an enricher."""
        EnrichmentRegistry.register(TestEnricherA)
        EnrichmentRegistry.unregister("test_a")
        assert "test_a" not in EnrichmentRegistry.list_enrichers()

    def test_get_enricher(self):
        """Test getting an enricher instance."""
        EnrichmentRegistry.register(TestEnricherA)
        enricher = EnrichmentRegistry.get_enricher("test_a")
        assert enricher is not None
        assert enricher.name == "test_a"

    def test_get_enricher_not_found(self):
        """Test getting a non-existent enricher."""
        enricher = EnrichmentRegistry.get_enricher("nonexistent")
        assert enricher is None

    def test_get_enricher_with_config(self):
        """Test getting an enricher with custom config."""
        EnrichmentRegistry.register(TestEnricherA)
        config = EnrichmentConfig(ttl_seconds=7200)
        enricher = EnrichmentRegistry.get_enricher("test_a", config=config)
        assert enricher.get_config().ttl_seconds == 7200

    def test_list_enrichers(self):
        """Test listing enrichers."""
        EnrichmentRegistry.register(TestEnricherA)
        EnrichmentRegistry.register(TestEnricherB)
        enrichers = EnrichmentRegistry.list_enrichers()
        assert "test_a" in enrichers
        assert "test_b" in enrichers

    def test_list_enrichers_by_priority(self):
        """Test listing enrichers sorted by priority."""
        EnrichmentRegistry.register(TestEnricherB)  # LOW priority
        EnrichmentRegistry.register(TestEnricherA)  # HIGH priority
        enrichers = EnrichmentRegistry.list_enrichers_by_priority()
        # HIGH (20) should come before LOW (40)
        assert enrichers.index("test_a") < enrichers.index("test_b")

    def test_is_enabled(self):
        """Test checking if enricher is enabled."""
        EnrichmentRegistry.register(TestEnricherA)
        assert EnrichmentRegistry.is_enabled("test_a") is True

        # Set disabled config
        EnrichmentRegistry.set_config("test_a", EnrichmentConfig(enabled=False))
        assert EnrichmentRegistry.is_enabled("test_a") is False

    def test_set_config(self):
        """Test setting configuration."""
        EnrichmentRegistry.register(TestEnricherA)
        config = EnrichmentConfig(ttl_seconds=1800, enabled=False)
        EnrichmentRegistry.set_config("test_a", config)

        stored = EnrichmentRegistry.get_config("test_a")
        assert stored.ttl_seconds == 1800
        assert stored.enabled is False

    def test_get_all_enrichers(self):
        """Test getting all enricher instances."""
        EnrichmentRegistry.register(TestEnricherA)
        EnrichmentRegistry.register(TestEnricherB)
        enrichers = EnrichmentRegistry.get_all_enrichers()
        assert len(enrichers) == 2

    def test_get_all_enrichers_enabled_only(self):
        """Test getting only enabled enrichers."""
        EnrichmentRegistry.register(TestEnricherA)
        EnrichmentRegistry.register(TestEnricherB)
        EnrichmentRegistry.set_config("test_b", EnrichmentConfig(enabled=False))

        enrichers = EnrichmentRegistry.get_all_enrichers(enabled_only=True)
        assert len(enrichers) == 1
        assert enrichers[0].name == "test_a"

    def test_get_enricher_info(self):
        """Test getting enricher info."""
        EnrichmentRegistry.register(TestEnricherA)
        info = EnrichmentRegistry.get_enricher_info("test_a")
        assert info["name"] == "test_a"
        assert info["field"] == "field_a"
        assert info["enabled"] is True

    def test_register_decorator(self):
        """Test register_enricher decorator."""

        @register_enricher
        class DecoratedEnricher(PropertyEnrichmentHook):
            name = "decorated"
            field = "decorated_field"

            async def enrich(self, context):
                return EnrichmentResult.success_result(
                    source=self.name, enrichment_field=self.field, value="decorated"
                )

            async def health_check(self):
                return True

        assert "decorated" in EnrichmentRegistry.list_enrichers()

    def test_register_with_config_decorator(self):
        """Test register_enricher decorator with config."""

        @register_enricher(config=EnrichmentConfig(ttl_seconds=9999))
        class ConfiguredEnricher(PropertyEnrichmentHook):
            name = "configured"
            field = "configured_field"

            async def enrich(self, context):
                return EnrichmentResult.success_result(
                    source=self.name, enrichment_field=self.field, value="configured"
                )

            async def health_check(self):
                return True

        config = EnrichmentRegistry.get_config("configured")
        assert config.ttl_seconds == 9999

    def test_instance_caching(self):
        """Test that instances are cached."""
        EnrichmentRegistry.register(TestEnricherA)
        instance1 = EnrichmentRegistry.get_enricher("test_a")
        instance2 = EnrichmentRegistry.get_enricher("test_a")
        assert instance1 is instance2

    def test_instance_cache_invalidation_on_config_change(self):
        """Test that cache is invalidated when config changes."""
        EnrichmentRegistry.register(TestEnricherA)
        instance1 = EnrichmentRegistry.get_enricher("test_a")

        EnrichmentRegistry.set_config("test_a", EnrichmentConfig(ttl_seconds=5000))
        instance2 = EnrichmentRegistry.get_enricher("test_a")

        # Should be different instances after config change
        assert instance1 is not instance2
