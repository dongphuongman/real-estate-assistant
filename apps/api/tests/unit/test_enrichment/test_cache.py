"""
Unit tests for Enrichment Cache (Task #78).
"""

import time

from data.enrichment.cache import (
    CacheEntry,
    EnrichmentCache,
    InMemoryEnrichmentCache,
    clear_cache,
    get_enrichment_cache,
)


class TestCacheEntry:
    """Tests for CacheEntry."""

    def test_is_expired(self):
        """Test expiration check."""
        entry = CacheEntry(
            value="test",
            source="test_source",
            enrichment_field="test_field",
            cached_at=time.time() - 3600,  # 1 hour ago
            ttl=1800,  # 30 min TTL
        )
        assert entry.is_expired() is True

        entry = CacheEntry(
            value="test",
            source="test_source",
            enrichment_field="test_field",
            cached_at=time.time(),
            ttl=3600,
        )
        assert entry.is_expired() is False

    def test_is_stale(self):
        """Test staleness check (80% of TTL)."""
        entry = CacheEntry(
            value="test",
            source="test_source",
            enrichment_field="test_field",
            cached_at=time.time() - 2900,  # ~80% of 3600
            ttl=3600,
        )
        assert entry.is_stale() is True

        entry = CacheEntry(
            value="test",
            source="test_source",
            enrichment_field="test_field",
            cached_at=time.time() - 1000,
            ttl=3600,
        )
        assert entry.is_stale() is False

    def test_age_seconds(self):
        """Test age calculation."""
        entry = CacheEntry(
            value="test",
            source="test_source",
            enrichment_field="test_field",
            cached_at=time.time() - 100,
            ttl=3600,
        )
        assert 99 <= entry.age_seconds() <= 101

    def test_remaining_ttl(self):
        """Test remaining TTL calculation."""
        entry = CacheEntry(
            value="test",
            source="test_source",
            enrichment_field="test_field",
            cached_at=time.time() - 1000,
            ttl=3600,
        )
        remaining = entry.remaining_ttl()
        assert 2599 <= remaining <= 2601

    def test_to_dict_and_from_dict(self):
        """Test serialization round-trip."""
        entry = CacheEntry(
            value={"key": "value"},
            source="test_source",
            enrichment_field="test_field",
            cached_at=time.time(),
            ttl=3600,
            metadata={"extra": "data"},
        )
        data = entry.to_dict()
        restored = CacheEntry.from_dict(data)

        assert restored.value == entry.value
        assert restored.source == entry.source
        assert restored.enrichment_field == entry.enrichment_field
        assert restored.ttl == entry.ttl
        assert restored.metadata == entry.metadata


class TestInMemoryEnrichmentCache:
    """Tests for InMemoryEnrichmentCache."""

    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = InMemoryEnrichmentCache()
        entry = CacheEntry(
            value="test_value",
            source="test",
            enrichment_field="field",
            cached_at=time.time(),
            ttl=3600,
        )
        cache.set("test_key", entry)

        retrieved = cache.get("test_key")
        assert retrieved is not None
        assert retrieved.value == "test_value"

    def test_get_expired_returns_none(self):
        """Test that expired entries return None."""
        cache = InMemoryEnrichmentCache()
        entry = CacheEntry(
            value="test_value",
            source="test",
            enrichment_field="field",
            cached_at=time.time() - 3600,
            ttl=1800,  # Already expired
        )
        cache.set("test_key", entry)

        retrieved = cache.get("test_key")
        assert retrieved is None

    def test_delete(self):
        """Test delete operation."""
        cache = InMemoryEnrichmentCache()
        entry = CacheEntry(
            value="test_value",
            source="test",
            enrichment_field="field",
            cached_at=time.time(),
            ttl=3600,
        )
        cache.set("test_key", entry)

        assert cache.delete("test_key") is True
        assert cache.get("test_key") is None
        assert cache.delete("nonexistent") is False

    def test_clear(self):
        """Test clear operation."""
        cache = InMemoryEnrichmentCache()
        entry = CacheEntry(
            value="test",
            source="test",
            enrichment_field="field",
            cached_at=time.time(),
            ttl=3600,
        )
        cache.set("key1", entry)
        cache.set("key2", entry)

        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_eviction_at_max_size(self):
        """Test eviction when cache reaches max size."""
        cache = InMemoryEnrichmentCache(max_size=5)

        for i in range(10):
            entry = CacheEntry(
                value=f"value_{i}",
                source="test",
                enrichment_field="field",
                cached_at=time.time() + i,  # Vary timestamp
                ttl=3600,
            )
            cache.set(f"key_{i}", entry)

        # Cache should have evicted some entries
        # After eviction, we should have at most max_size entries
        with cache._lock:
            count = len(cache._cache)
        assert count <= 5


class TestEnrichmentCache:
    """Tests for EnrichmentCache with in-memory fallback."""

    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = EnrichmentCache(redis_url=None, fallback_to_in_memory=True)

        cache.set(
            source="test_source",
            property_id="prop_123",
            enrichment_field="test_field",
            value={"data": "value"},
            ttl=3600,
        )

        entry = cache.get(
            source="test_source",
            property_id="prop_123",
            enrichment_field="test_field",
        )

        assert entry is not None
        assert entry.value == {"data": "value"}
        assert entry.source == "test_source"

    def test_get_nonexistent(self):
        """Test getting non-existent entry."""
        cache = EnrichmentCache(redis_url=None, fallback_to_in_memory=True)

        entry = cache.get("source", "prop", "field")
        assert entry is None

    def test_delete(self):
        """Test delete operation."""
        cache = EnrichmentCache(redis_url=None, fallback_to_in_memory=True)

        cache.set("source", "prop", "field", "value", ttl=3600)
        assert cache.delete("source", "prop", "field") is True
        assert cache.get("source", "prop", "field") is None

    def test_invalidate_property(self):
        """Test invalidating all entries for a property."""
        cache = EnrichmentCache(redis_url=None, fallback_to_in_memory=True)

        cache.set("source1", "prop_1", "field1", "value1", ttl=3600)
        cache.set("source2", "prop_1", "field2", "value2", ttl=3600)
        cache.set("source1", "prop_2", "field1", "value3", ttl=3600)

        count = cache.invalidate_property("prop_1")
        assert count >= 2

        assert cache.get("source1", "prop_1", "field1") is None
        assert cache.get("source2", "prop_1", "field2") is None
        assert cache.get("source1", "prop_2", "field1") is not None

    def test_clear(self):
        """Test clear operation."""
        cache = EnrichmentCache(redis_url=None, fallback_to_in_memory=True)

        cache.set("s1", "p1", "f1", "v1", ttl=3600)
        cache.set("s2", "p2", "f2", "v2", ttl=3600)

        cache.clear()

        assert cache.get("s1", "p1", "f1") is None
        assert cache.get("s2", "p2", "f2") is None

    def test_get_stats(self):
        """Test getting cache statistics."""
        cache = EnrichmentCache(redis_url=None, fallback_to_in_memory=True)

        stats = cache.get_stats()
        assert "redis_enabled" in stats
        assert "fallback_enabled" in stats
        assert stats["fallback_enabled"] is True


class TestGlobalCache:
    """Tests for global cache functions."""

    def test_get_enrichment_cache_singleton(self):
        """Test that get_enrichment_cache returns singleton."""
        clear_cache()
        cache1 = get_enrichment_cache()
        cache2 = get_enrichment_cache()
        assert cache1 is cache2

    def test_clear_cache(self):
        """Test clear_cache function."""
        cache = get_enrichment_cache()
        cache.set("source", "prop", "field", "value", ttl=3600)

        clear_cache()
        cache = get_enrichment_cache()
        assert cache.get("source", "prop", "field") is None
