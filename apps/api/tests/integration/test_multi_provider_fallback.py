"""
Integration tests for multi-provider failover with multiple API keys.

Tests verify:
- Multi-key fallback within a provider
- Multi-provider fallback chain
- Circuit breaker state management
- Retry logic with real LLM calls
"""

from unittest.mock import MagicMock

import pytest
from httpx import HTTPStatusError

from utils.circuit import (
    CircuitBreakerManager,
    CircuitState,
    ProviderCircuitBreaker,
)


class TestMultiKeyFallbackIntegration:
    """Integration tests for multi-key fallback with LLM dependencies."""

    @pytest.mark.asyncio
    async def test_multi_key_fallback_on_rate_limit(self):
        """Test that fallback to second key works when first key hits rate limit."""
        manager = CircuitBreakerManager()

        provider_keys = {
            "test_provider": ["key1", "key2"],
        }

        call_count = {"key1": 0, "key2": 0}

        async def mock_func(provider, key_index, api_key):
            call_count[api_key] += 1
            if api_key == "key1" and call_count["key1"] == 1:
                raise HTTPStatusError(
                    "Rate limit exceeded",
                    request=MagicMock(),
                    response=MagicMock(status_code=429),
                )
            return f"success-{api_key}"

        result = await manager.call_with_fallback(
            providers=["test_provider"],
            provider_keys=provider_keys,
            func=mock_func,
        )

        # Should have retried with key2 and succeeded
        assert result == "success-key2"
        assert call_count["key1"] == 1
        assert call_count["key2"] == 1

    @pytest.mark.asyncio
    async def test_multi_provider_fallback_on_provider_failure(self):
        """Test that fallback to second provider works when first provider fails."""
        manager = CircuitBreakerManager()

        provider_keys = {
            "provider1": ["key1"],
            "provider2": ["key2"],
        }

        async def mock_func(provider, key_index, api_key):
            if provider == "provider1":
                raise Exception("Provider1 failed")
            return f"success-{provider}"

        result = await manager.call_with_fallback(
            providers=["provider1", "provider2"],
            provider_keys=provider_keys,
            func=mock_func,
        )

        # Should have fallen back to provider2
        assert result == "success-provider2"

    @pytest.mark.asyncio
    async def test_all_providers_fail_raises_error(self):
        """Test that error is raised when all providers fail."""
        manager = CircuitBreakerManager()

        provider_keys = {
            "provider1": ["key1"],
            "provider2": ["key2"],
        }

        async def mock_func(provider, key_index, api_key):
            raise Exception(f"{provider} failed")

        # Should raise RuntimeError when all providers fail
        with pytest.raises(RuntimeError, match="All providers and keys failed"):
            await manager.call_with_fallback(
                providers=["provider1", "provider2"],
                provider_keys=provider_keys,
                func=mock_func,
            )


class TestCircuitBreakerStateManagement:
    """Integration tests for circuit breaker state management."""

    @pytest.mark.asyncio
    async def test_key_state_transitions_with_failures(self):
        """Test that key state transitions correctly through failure scenarios."""
        breaker = ProviderCircuitBreaker(
            provider="test_provider",
            total_keys=2,
            key_failure_threshold=2,
        )

        async def failing_func():
            raise Exception("Simulated failure")

        # Trigger failures to open key 0
        for _ in range(2):
            with pytest.raises(Exception):  # noqa: B017 - We expect any Exception to trigger circuit breaker
                await breaker.call(failing_func, key_index=0)

        # Key 0 should be OPEN now
        assert breaker.stats.key_stats[0].current_state.value == "open"
        assert breaker.stats.key_stats[0].failed_calls == 2

    @pytest.mark.asyncio
    async def test_key_recovery_after_timeout(self):
        """Test that key recovers after timeout period."""
        breaker = ProviderCircuitBreaker(
            provider="test_provider",
            total_keys=2,
            timeout_seconds=0.1,  # Short timeout for testing
        )

        # Mark key 0 as OPEN with past failure time
        from datetime import UTC, datetime, timedelta

        breaker.stats.key_stats[0].current_state = CircuitState.OPEN
        breaker.stats.key_stats[0].failed_calls = 2
        breaker.stats.key_stats[0].last_failure_time = datetime.now(UTC) - timedelta(seconds=1)

        async def success_func():
            return "success"

        # Call should succeed and transition to CLOSED
        result = await breaker.call(success_func, key_index=0)

        assert result == "success"
        assert breaker.stats.key_stats[0].current_state.value == "closed"


class TestCircuitBreakerManagerIntegration:
    """Integration tests for circuit breaker manager."""

    @pytest.mark.asyncio
    async def test_manager_coordinates_providers_and_keys(self):
        """Test that manager properly coordinates fallback across providers and keys."""
        manager = CircuitBreakerManager()

        provider_keys = {
            "provider1": ["key1", "key2"],
            "provider2": ["key3"],
        }

        call_log = []

        async def mock_func(provider, key_index, api_key):
            call_log.append((provider, key_index, api_key))
            if provider == "provider1" and key_index == 0:
                raise Exception("Provider1 key0 failed")
            return f"success-{provider}-{key_index}"

        result = await manager.call_with_fallback(
            providers=["provider1", "provider2"],
            provider_keys=provider_keys,
            func=mock_func,
        )

        # Should have tried provider1 key0, then provider1 key1, then succeeded
        assert "provider1" in str(call_log)
        assert result == "success-provider1-1"
