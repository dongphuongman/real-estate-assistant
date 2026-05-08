"""Tests for data.enrichment.cache module."""

import time
from unittest.mock import MagicMock

from data.enrichment.cache import (
    CacheEntry,
    EnrichmentCache,
    InMemoryEnrichmentCache,
    clear_cache,
    get_enrichment_cache,
)


class TestCacheEntry:
    def test_not_expired(self):
        entry = CacheEntry(
            value="test", source="src", enrichment_field="field", cached_at=time.time(), ttl=300
        )
        assert entry.is_expired() is False

    def test_expired(self):
        entry = CacheEntry(
            value="test",
            source="src",
            enrichment_field="field",
            cached_at=time.time() - 400,
            ttl=300,
        )
        assert entry.is_expired() is True

    def test_not_stale(self):
        entry = CacheEntry(
            value="test", source="src", enrichment_field="field", cached_at=time.time(), ttl=300
        )
        assert entry.is_stale() is False

    def test_stale_at_80_percent(self):
        entry = CacheEntry(
            value="test",
            source="src",
            enrichment_field="field",
            cached_at=time.time() - 250,
            ttl=300,
        )
        assert entry.is_stale() is True

    def test_age_seconds(self):
        past = time.time() - 10
        entry = CacheEntry(
            value="test", source="src", enrichment_field="field", cached_at=past, ttl=300
        )
        age = entry.age_seconds()
        assert 9 < age < 12

    def test_remaining_ttl(self):
        past = time.time() - 100
        entry = CacheEntry(
            value="test", source="src", enrichment_field="field", cached_at=past, ttl=300
        )
        remaining = entry.remaining_ttl()
        assert 190 <= remaining <= 200

    def test_remaining_ttl_zero_minimum(self):
        past = time.time() - 500
        entry = CacheEntry(
            value="test", source="src", enrichment_field="field", cached_at=past, ttl=300
        )
        assert entry.remaining_ttl() == 0

    def test_to_dict(self):
        entry = CacheEntry(
            value="test",
            source="src",
            enrichment_field="field",
            cached_at=1000.0,
            ttl=300,
            metadata={"k": "v"},
        )
        d = entry.to_dict()
        assert d["value"] == "test"
        assert d["source"] == "src"
        assert d["field"] == "field"
        assert d["ttl"] == 300
        assert d["metadata"] == {"k": "v"}

    def test_from_dict(self):
        d = {
            "value": "test",
            "source": "src",
            "field": "field",
            "cached_at": 1000.0,
            "ttl": 300,
            "metadata": {},
        }
        entry = CacheEntry.from_dict(d)
        assert entry.value == "test"
        assert entry.source == "src"
        assert entry.enrichment_field == "field"

    def test_from_dict_default_metadata(self):
        d = {"value": "test", "source": "src", "field": "field", "cached_at": 1000.0, "ttl": 300}
        entry = CacheEntry.from_dict(d)
        assert entry.metadata == {}

    def test_roundtrip(self):
        entry = CacheEntry(
            value=[1, 2], source="src", enrichment_field="f", cached_at=1000.0, ttl=300
        )
        d = entry.to_dict()
        restored = CacheEntry.from_dict(d)
        assert restored.value == [1, 2]
        assert restored.source == entry.source


class TestInMemoryEnrichmentCache:
    def test_get_miss(self):
        cache = InMemoryEnrichmentCache()
        assert cache.get("nonexistent") is None

    def test_set_and_get(self):
        cache = InMemoryEnrichmentCache()
        entry = CacheEntry(
            value="data", source="s", enrichment_field="f", cached_at=time.time(), ttl=300
        )
        cache.set("key1", entry)
        result = cache.get("key1")
        assert result is not None
        assert result.value == "data"

    def test_get_expired(self):
        cache = InMemoryEnrichmentCache()
        entry = CacheEntry(
            value="data", source="s", enrichment_field="f", cached_at=time.time() - 400, ttl=300
        )
        cache.set("key1", entry)
        assert cache.get("key1") is None

    def test_delete(self):
        cache = InMemoryEnrichmentCache()
        cache.set(
            "key1",
            CacheEntry(value="x", source="s", enrichment_field="f", cached_at=time.time(), ttl=300),
        )
        assert cache.delete("key1") is True
        assert cache.delete("key1") is False

    def test_clear(self):
        cache = InMemoryEnrichmentCache()
        cache.set(
            "k1",
            CacheEntry(value="x", source="s", enrichment_field="f", cached_at=time.time(), ttl=300),
        )
        cache.set(
            "k2",
            CacheEntry(value="x", source="s", enrichment_field="f", cached_at=time.time(), ttl=300),
        )
        cache.clear()
        assert cache.get("k1") is None

    def test_eviction_at_capacity(self):
        cache = InMemoryEnrichmentCache(max_size=5)
        for i in range(6):
            cache.set(
                f"key{i}",
                CacheEntry(value=i, source="s", enrichment_field="f", cached_at=float(i), ttl=300),
            )
        assert len(cache._cache) <= 5

    def test_evict_oldest(self):
        cache = InMemoryEnrichmentCache(max_size=5)
        for i in range(5):
            cache.set(
                f"key{i}",
                CacheEntry(value=i, source="s", enrichment_field="f", cached_at=float(i), ttl=300),
            )
        cache._evict_oldest()
        assert len(cache._cache) < 5

    def test_evict_oldest_empty(self):
        cache = InMemoryEnrichmentCache()
        cache._evict_oldest()  # should not raise


class TestEnrichmentCacheMemoryOnly:
    def test_no_redis_uses_memory(self):
        cache = EnrichmentCache(redis_url=None)
        assert cache._redis_client is None
        assert cache._fallback_cache is not None

    def test_set_and_get(self):
        cache = EnrichmentCache(redis_url=None)
        cache.set("src", "prop-1", "field", "value", ttl=300)
        result = cache.get("src", "prop-1", "field")
        assert result is not None
        assert result.value == "value"

    def test_get_miss(self):
        cache = EnrichmentCache(redis_url=None)
        assert cache.get("src", "nonexistent", "field") is None

    def test_delete(self):
        cache = EnrichmentCache(redis_url=None)
        cache.set("src", "prop-1", "field", "value")
        assert cache.delete("src", "prop-1", "field") is True
        assert cache.get("src", "prop-1", "field") is None

    def test_clear(self):
        cache = EnrichmentCache(redis_url=None)
        cache.set("src", "prop-1", "field", "value")
        cache.clear()
        assert cache.get("src", "prop-1", "field") is None

    def test_invalidate_property(self):
        cache = EnrichmentCache(redis_url=None)
        cache.set("src1", "prop-1", "field1", "v1")
        cache.set("src2", "prop-1", "field2", "v2")
        cache.set("src1", "prop-2", "field1", "v3")
        count = cache.invalidate_property("prop-1")
        assert count == 2
        assert cache.get("src1", "prop-2", "field1") is not None

    def test_get_stats(self):
        cache = EnrichmentCache(redis_url=None)
        stats = cache.get_stats()
        assert stats["redis_enabled"] is False
        assert stats["fallback_enabled"] is True
        assert "prefix" in stats

    def test_make_key(self):
        cache = EnrichmentCache(redis_url=None, prefix="test")
        key = cache._make_key("src", "prop-1", "field")
        assert key == "test:src:prop-1:field"

    def test_set_with_metadata(self):
        cache = EnrichmentCache(redis_url=None)
        cache.set("src", "prop-1", "field", "value", metadata={"k": "v"})
        result = cache.get("src", "prop-1", "field")
        assert result is not None
        assert result.metadata == {"k": "v"}

    def test_set_expired_returns_none(self):
        cache = EnrichmentCache(redis_url=None)
        cache.set("src", "prop-1", "field", "value", ttl=1)
        # Manually expire the entry
        entry = cache._fallback_cache._cache.get(cache._make_key("src", "prop-1", "field"))
        if entry:
            entry.cached_at = time.time() - 100
        assert cache.get("src", "prop-1", "field") is None


class TestEnrichmentCacheRedis:
    """Redis tests use direct _redis_client injection since redis is imported locally."""

    def _make_redis_cache(self, fallback=False):
        cache = EnrichmentCache(redis_url=None, fallback_to_in_memory=fallback)
        cache._redis_client = MagicMock()
        cache._redis_client.ping.return_value = True
        return cache

    def test_redis_get_hit(self):
        cache = self._make_redis_cache()
        entry_json = (
            '{"value": "data", "source": "src", "field": "f", "cached_at": %f, "ttl": 300, "metadata": {}}'
            % time.time()
        )
        cache._redis_client.get.return_value = entry_json.encode()

        result = cache.get("src", "prop-1", "field")
        assert result is not None
        assert result.value == "data"

    def test_redis_get_expired_deleted(self):
        cache = self._make_redis_cache()
        entry_json = (
            '{"value": "data", "source": "src", "field": "f", "cached_at": %f, "ttl": 1, "metadata": {}}'
            % (time.time() - 10)
        )
        cache._redis_client.get.return_value = entry_json.encode()

        cache.get("src", "prop-1", "field")
        cache._redis_client.delete.assert_called()

    def test_redis_get_miss(self):
        cache = self._make_redis_cache()
        cache._redis_client.get.return_value = None

        result = cache.get("src", "prop-1", "field")
        assert result is None

    def test_redis_set_success(self):
        cache = self._make_redis_cache()
        result = cache.set("src", "prop-1", "field", "value")
        assert result is True
        cache._redis_client.setex.assert_called_once()

    def test_redis_set_failure_no_fallback(self):
        cache = self._make_redis_cache()
        cache._redis_client.setex.side_effect = Exception("Redis error")
        result = cache.set("src", "prop-1", "field", "value")
        assert result is False

    def test_redis_delete(self):
        cache = self._make_redis_cache()
        cache._redis_client.delete.return_value = 1
        result = cache.delete("src", "prop-1", "field")
        assert result is True

    def test_redis_delete_error(self):
        cache = self._make_redis_cache()
        cache._redis_client.delete.side_effect = Exception("error")
        result = cache.delete("src", "prop-1", "field")
        assert result is False

    def test_redis_clear(self):
        cache = self._make_redis_cache()
        cache._redis_client.keys.return_value = ["enrichment:a:b:c"]
        cache.clear()
        cache._redis_client.delete.assert_called()

    def test_redis_clear_no_keys(self):
        cache = self._make_redis_cache()
        cache._redis_client.keys.return_value = []
        cache.clear()

    def test_redis_invalidate_property(self):
        cache = self._make_redis_cache()
        cache._redis_client.keys.return_value = ["enrichment:src:prop-1:field"]
        cache._redis_client.delete.return_value = 1
        count = cache.invalidate_property("prop-1")
        assert count == 1

    def test_redis_get_error_falls_back_to_memory(self):
        cache = self._make_redis_cache(fallback=True)
        cache._redis_client.get.side_effect = Exception("Redis error")
        # Should fall back to in-memory cache (empty)
        result = cache.get("src", "prop-1", "field")
        assert result is None

    def test_redis_get_error_no_fallback(self):
        cache = self._make_redis_cache()
        cache._redis_client.get.side_effect = Exception("Redis error")
        result = cache.get("src", "prop-1", "field")
        assert result is None

    def test_no_redis_no_fallback(self):
        cache = EnrichmentCache(redis_url=None, fallback_to_in_memory=False)
        assert cache.set("src", "prop-1", "field", "value") is False
        assert cache.get("src", "prop-1", "field") is None

    def test_redis_set_error_falls_back_to_memory(self):
        cache = self._make_redis_cache(fallback=True)
        cache._redis_client.setex.side_effect = Exception("Redis error")
        result = cache.set("src", "prop-1", "field", "value")
        assert result is True
        # Verify it went to fallback
        assert cache._fallback_cache.get(cache._make_key("src", "prop-1", "field")) is not None


class TestGlobalCache:
    def test_get_enrichment_cache(self):
        clear_cache()
        cache = get_enrichment_cache()
        assert isinstance(cache, EnrichmentCache)

    def test_singleton(self):
        clear_cache()
        cache1 = get_enrichment_cache()
        cache2 = get_enrichment_cache()
        assert cache1 is cache2

    def test_clear_cache(self):
        get_enrichment_cache()
        clear_cache()
        from data.enrichment.cache import _cache

        assert _cache is None
