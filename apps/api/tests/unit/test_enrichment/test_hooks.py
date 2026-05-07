"""
Unit tests for Property Enrichment Hook interface (Task #78).
"""

import pytest

from data.enrichment.hooks import (
    EnrichmentConfig,
    EnrichmentContext,
    EnrichmentPriority,
    EnrichmentResult,
    EnrichmentStatus,
    PropertyEnrichmentHook,
)


class MockEnricher(PropertyEnrichmentHook[str]):
    """Mock enricher for testing."""

    name = "mock_enricher"
    display_name = "Mock Enricher"
    description = "A mock enricher for testing"
    field = "mock_field"

    async def enrich(self, context: EnrichmentContext) -> EnrichmentResult[str]:
        return EnrichmentResult.success_result(
            source=self.name,
            enrichment_field=self.field,
            value="mock_value",
        )

    async def health_check(self) -> bool:
        return True


class TestEnrichmentConfig:
    """Tests for EnrichmentConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = EnrichmentConfig()
        assert config.enabled is True
        assert config.ttl_seconds == 3600
        assert config.timeout_seconds == 30.0
        assert config.fallback_value is None
        assert config.required is False
        assert config.priority == EnrichmentPriority.NORMAL
        assert config.cache_enabled is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = EnrichmentConfig(
            enabled=False,
            ttl_seconds=7200,
            timeout_seconds=60.0,
            fallback_value="fallback",
            required=True,
            priority=EnrichmentPriority.HIGH,
        )
        assert config.enabled is False
        assert config.ttl_seconds == 7200
        assert config.timeout_seconds == 60.0
        assert config.fallback_value == "fallback"
        assert config.required is True
        assert config.priority == EnrichmentPriority.HIGH

    def test_to_dict(self):
        """Test serialization to dictionary."""
        config = EnrichmentConfig(ttl_seconds=1800)
        result = config.to_dict()
        assert result["ttl_seconds"] == 1800
        assert result["enabled"] is True


class TestEnrichmentContext:
    """Tests for EnrichmentContext."""

    def test_from_property(self):
        """Test creating context from property data."""
        property_data = {
            "id": "123",
            "address": "123 Main St",
            "city": "Berlin",
            "latitude": 52.5200,
            "longitude": 13.4050,
            "postal_code": "10115",
            "country": "Germany",
            "price": 500000,
        }
        context = EnrichmentContext.from_property(property_data)

        assert context.property_id == "123"
        assert context.address == "123 Main St"
        assert context.city == "Berlin"
        assert context.latitude == 52.5200
        assert context.longitude == 13.4050
        assert context.postal_code == "10115"
        assert context.country == "Germany"
        assert context.extra["price"] == 500000

    def test_from_property_minimal(self):
        """Test creating context from minimal property data."""
        context = EnrichmentContext.from_property({"id": 456})
        assert context.property_id == "456"
        assert context.address is None
        assert context.city is None


class TestEnrichmentResult:
    """Tests for EnrichmentResult."""

    def test_success_result(self):
        """Test creating a successful result."""
        result = EnrichmentResult.success_result(
            source="test",
            enrichment_field="value",
            value=42,
            ttl_seconds=3600,
        )
        assert result.success is True
        assert result.status == EnrichmentStatus.COMPLETED
        assert result.value == 42
        assert result.cached is False

    def test_cached_result(self):
        """Test creating a cached result."""
        result = EnrichmentResult.cached_result(
            source="test",
            enrichment_field="value",
            value=42,
        )
        assert result.success is True
        assert result.status == EnrichmentStatus.CACHED
        assert result.cached is True

    def test_error_result(self):
        """Test creating an error result."""
        result = EnrichmentResult.error_result(
            source="test",
            enrichment_field="value",
            error="Something went wrong",
        )
        assert result.success is False
        assert result.status == EnrichmentStatus.FAILED
        assert result.error == "Something went wrong"

    def test_skipped_result(self):
        """Test creating a skipped result."""
        result = EnrichmentResult.skipped_result(
            source="test",
            enrichment_field="value",
            reason="Missing data",
        )
        assert result.success is False
        assert result.status == EnrichmentStatus.SKIPPED
        assert result.metadata["reason"] == "Missing data"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        result = EnrichmentResult.success_result(
            source="test",
            enrichment_field="value",
            value="data",
        )
        data = result.to_dict()
        assert data["source"] == "test"
        assert data["field"] == "value"
        assert data["value"] == "data"
        assert data["status"] == "completed"


class TestPropertyEnrichmentHook:
    """Tests for PropertyEnrichmentHook base class."""

    def test_enricher_initialization(self):
        """Test enricher initialization."""
        enricher = MockEnricher()
        assert enricher.name == "mock_enricher"
        assert enricher.field == "mock_field"
        assert enricher.is_enabled() is True

    def test_enricher_custom_config(self):
        """Test enricher with custom config."""
        config = EnrichmentConfig(enabled=False, ttl_seconds=7200)
        enricher = MockEnricher(config=config)
        assert enricher.is_enabled() is False
        assert enricher.get_config().ttl_seconds == 7200

    def test_get_cache_key(self):
        """Test cache key generation."""
        enricher = MockEnricher()
        key = enricher.get_cache_key("property-123")
        assert key == "enrichment:mock_enricher:property-123:mock_field"

    def test_enricher_without_name_raises(self):
        """Test that enricher without name raises error."""

        class InvalidEnricher(PropertyEnrichmentHook):
            field = "test"

            async def enrich(self, context):
                pass

            async def health_check(self):
                return True

        with pytest.raises(ValueError, match="must have a 'name' attribute"):
            InvalidEnricher()

    def test_enricher_without_field_raises(self):
        """Test that enricher without field raises error."""

        class InvalidEnricher(PropertyEnrichmentHook):
            name = "test"

            async def enrich(self, context):
                pass

            async def health_check(self):
                return True

        with pytest.raises(ValueError, match="must have a 'field' attribute"):
            InvalidEnricher()

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager usage."""
        async with MockEnricher() as enricher:
            assert enricher.is_connected() is True
        assert enricher.is_connected() is False

    def test_get_status(self):
        """Test get_status method."""
        enricher = MockEnricher()
        status = enricher.get_status()
        assert status["name"] == "mock_enricher"
        assert status["field"] == "mock_field"
        assert status["enabled"] is True
