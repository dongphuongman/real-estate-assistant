"""Tests for utils.response_cache module."""

import time
from unittest.mock import MagicMock

import pytest

from utils.response_cache import (
    CacheConfig,
    CacheEntry,
    InMemoryCache,
    ResponseCache,
    cached_response,
)


class TestCacheConfig:
    def test_defaults(self):
        config = CacheConfig()
        assert config.enabled is True
        assert config.ttl_seconds == 300
        assert config.prefix == "api_cache"

    def test_custom(self):
        config = CacheConfig(ttl_seconds=60, prefix="test")
        assert config.ttl_seconds == 60
        assert config.prefix == "test"


class TestCacheEntry:
    def test_not_expired(self):
        entry = CacheEntry(data={"key": "val"}, status_code=200, ttl=300)
        assert entry.is_expired() is False

    def test_expired(self):
        entry = CacheEntry(data={"key": "val"}, status_code=200, ttl=1, cached_at=time.time() - 5)
        assert entry.is_expired() is True

    def test_not_stale(self):
        entry = CacheEntry(data={"key": "val"}, status_code=200, ttl=300)
        assert entry.is_stale() is False

    def test_stale(self):
        entry = CacheEntry(data={"key": "val"}, status_code=200, ttl=1, cached_at=time.time() - 5)
        assert entry.is_stale() is True

    def test_age_seconds(self):
        past = time.time() - 10
        entry = CacheEntry(data={}, status_code=200, cached_at=past)
        age = entry.age_seconds()
        assert 9.5 < age < 11

    def test_age_with_now(self):
        now = time.time()
        entry = CacheEntry(data={}, status_code=200, cached_at=now - 5)
        assert entry.age_seconds(now) == 5.0


class TestInMemoryCache:
    def test_get_miss(self):
        cache = InMemoryCache()
        assert cache.get("nonexistent") is None

    def test_set_and_get(self):
        cache = InMemoryCache()
        entry = CacheEntry(data={"x": 1}, status_code=200)
        cache.set("key1", entry)
        result = cache.get("key1")
        assert result is not None
        assert result.data == {"x": 1}

    def test_get_expired(self):
        cache = InMemoryCache()
        entry = CacheEntry(data={"x": 1}, status_code=200, ttl=1, cached_at=time.time() - 5)
        cache.set("key1", entry)
        assert cache.get("key1") is None

    def test_delete(self):
        cache = InMemoryCache()
        cache.set("key1", CacheEntry(data={}, status_code=200))
        assert cache.delete("key1") is True
        assert cache.delete("key1") is False

    def test_clear(self):
        cache = InMemoryCache()
        cache.set("k1", CacheEntry(data={}, status_code=200))
        cache.set("k2", CacheEntry(data={}, status_code=200))
        cache.clear()
        assert cache.size() == 0

    def test_size(self):
        cache = InMemoryCache()
        assert cache.size() == 0
        cache.set("k1", CacheEntry(data={}, status_code=200))
        assert cache.size() == 1

    def test_lru_eviction(self):
        cache = InMemoryCache(max_size=5)
        for i in range(6):
            cache.set(f"key{i}", CacheEntry(data={"i": i}, status_code=200, cached_at=float(i)))
        assert cache.size() <= 5


class TestResponseCache:
    def _make_request(self, method="GET", path="/api/v1/search", query=None):
        request = MagicMock()
        request.method = method
        request.url.path = path
        request.query_params.items.return_value = query or []
        return request

    def test_disabled(self):
        config = CacheConfig(enabled=False)
        cache = ResponseCache(config)
        assert cache._backend is None

    def test_in_memory_backend(self):
        config = CacheConfig()
        cache = ResponseCache(config)
        assert isinstance(cache._backend, InMemoryCache)

    @pytest.mark.asyncio
    async def test_get_miss(self):
        cache = ResponseCache(CacheConfig())
        request = self._make_request()
        result = await cache.get(request)
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        cache = ResponseCache(CacheConfig())
        request = self._make_request()
        await cache.set(request, {"result": "data"})
        result = await cache.get(request)
        assert result is not None
        assert result.data == {"result": "data"}

    @pytest.mark.asyncio
    async def test_delete(self):
        cache = ResponseCache(CacheConfig())
        request = self._make_request()
        await cache.set(request, {"x": 1})
        deleted = await cache.delete(request)
        assert deleted is True

    @pytest.mark.asyncio
    async def test_clear_all(self):
        cache = ResponseCache(CacheConfig())
        request = self._make_request()
        await cache.set(request, {"x": 1})
        await cache.clear_all()
        result = await cache.get(request)
        assert result is None

    @pytest.mark.asyncio
    async def test_stats(self):
        cache = ResponseCache(CacheConfig())
        stats = cache.get_stats()
        assert stats["enabled"] is True
        assert stats["backend"] == "memory"

    @pytest.mark.asyncio
    async def test_stats_disabled(self):
        cache = ResponseCache(CacheConfig(enabled=False))
        stats = cache.get_stats()
        assert stats["enabled"] is False

    @pytest.mark.asyncio
    async def test_hit_rate(self):
        cache = ResponseCache(CacheConfig())
        request = self._make_request()
        await cache.get(request)  # miss
        await cache.set(request, {"x": 1})
        await cache.get(request)  # hit
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5

    def test_path_prefix(self):
        assert ResponseCache._path_prefix("/api/v1/search") == "/api/v1/search"
        assert ResponseCache._path_prefix("/short") == "/short"
        assert ResponseCache._path_prefix("/api/v1/search/something") == "/api/v1/search"

    def test_invalidate_by_prefix(self):
        cache = ResponseCache(CacheConfig())
        self._make_request(path="/api/v1/search")
        self._make_request(path="/api/v1/properties")
        cache._backend = InMemoryCache()
        cache._backend.set("k1", CacheEntry(data={}, status_code=200))
        cache._backend.set("k2", CacheEntry(data={}, status_code=200))
        cache._prefix_index["/api/v1/search"] = {"k1"}
        cache._prefix_index["/api/v1/properties"] = {"k2"}
        deleted = cache.invalidate_by_prefix("/api/v1/search")
        assert deleted == 1

    def test_invalidate_no_backend(self):
        cache = ResponseCache(CacheConfig(enabled=False))
        assert cache.invalidate_by_prefix("/api") == 0


class TestCachedResponseDecorator:
    @pytest.mark.asyncio
    async def test_no_request_no_cache(self):
        @cached_response(ttl_seconds=60)
        async def my_endpoint():
            return {"data": "result"}

        result = await my_endpoint()
        assert result == {"data": "result"}

    @pytest.mark.asyncio
    async def test_with_request_and_cache(self):
        @cached_response(ttl_seconds=60)
        async def my_endpoint(request=None):
            return {"data": "fresh"}

        app_mock = MagicMock()
        cache = ResponseCache(CacheConfig())
        app_mock.state.response_cache = cache
        request = MagicMock()
        request.method = "GET"
        request.url.path = "/test"
        request.query_params.items.return_value = []
        request.app = app_mock

        result = await my_endpoint(request=request)
        assert result == {"data": "fresh"}

        # Second call should hit cache
        result2 = await my_endpoint(request=request)
        assert result2 == {"data": "fresh"}
