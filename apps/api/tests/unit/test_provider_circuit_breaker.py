"""
Unit tests for multi-provider and multi-API key circuit breaker.

Tests cover:
- Circuit breaker state transitions with keys
- Key rotation (round-robin)
- Provider fallback chain
- Retry logic with tenacity
"""

from datetime import UTC, datetime, timedelta

import pytest

from utils.circuit import (
    AuthenticationError,
    CircuitBreakerManager,
    CircuitState,
    KeySwitchError,
    ProviderCircuitBreaker,
    ProviderCircuitBreakerOpenError,
    is_retryable_error,
    with_llm_retry,
)


class TestRetryLogic:
    """Tests for retry logic with tenacity."""

    def test_is_retryable_error_rate_limit(self):
        """Test that 429 rate limit errors are retryable."""
        error = Exception("Rate limit exceeded (HTTP 429)")
        assert is_retryable_error(error) is True

    def test_is_retryable_error_server_error(self):
        """Test that 5xx server errors are retryable."""
        error = Exception("Internal server error (HTTP 500)")
        assert is_retryable_error(error) is True

    def test_is_retryable_error_connection_error(self):
        """Test that connection errors are retryable."""
        error = Exception("Connection timeout")
        assert is_retryable_error(error) is True

    def test_is_retryable_error_auth_error(self):
        """Test that 401 authentication errors are NOT retryable."""
        error = Exception("Unauthorized (HTTP 401)")
        assert is_retryable_error(error) is False

    def test_is_retryable_error_forbidden_error(self):
        """Test that 403 forbidden errors are NOT retryable."""
        error = Exception("Forbidden (HTTP 403)")
        assert is_retryable_error(error) is False

    def test_is_retryable_error_unknown_error(self):
        """Test that unknown errors are NOT retryable."""
        error = Exception("Unknown error")
        assert is_retryable_error(error) is False

    @pytest.mark.asyncio
    async def test_with_llm_retry_success_on_first_try(self):
        """Test that successful function is not retried."""
        call_count = 0

        async def test_func():
            nonlocal call_count
            call_count += 1
            return "success"

        wrapped_func = with_llm_retry(test_func, max_attempts=3)
        result = await wrapped_func()

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_with_llm_retry_retries_on_transient_error(self):
        """Test that transient errors trigger retries."""
        call_count = 0

        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Rate limit exceeded (HTTP 429)")
            return "success"

        wrapped_func = with_llm_retry(test_func, max_attempts=3)
        result = await wrapped_func()

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_with_llm_retry_fails_after_max_attempts(self):
        """Test that function fails after max attempts."""

        async def test_func():
            raise Exception("Rate limit exceeded (HTTP 429)")

        wrapped_func = with_llm_retry(test_func, max_attempts=3)

        with pytest.raises(Exception, match="Rate limit exceeded"):
            await wrapped_func()

    @pytest.mark.asyncio
    async def test_with_llm_retry_no_retry_on_auth_error(self):
        """Test that authentication errors are NOT retried."""
        call_count = 0

        async def test_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Unauthorized (HTTP 401)")

        wrapped_func = with_llm_retry(test_func, max_attempts=3)

        with pytest.raises(AuthenticationError):
            await wrapped_func()

        # Should only be called once (no retries)
        assert call_count == 1


class TestProviderCircuitBreaker:
    """Tests for ProviderCircuitBreaker with multi-key support."""

    @pytest.fixture
    def provider_breaker(self):
        """Create a provider circuit breaker with 3 keys."""
        return ProviderCircuitBreaker(
            provider="test_provider",
            total_keys=3,
            key_failure_threshold=3,
            provider_failure_threshold=9,
        )

    @pytest.mark.asyncio
    async def test_initial_state(self, provider_breaker):
        """Test that breaker starts in CLOSED state for all keys."""
        assert provider_breaker.stats.current_state == CircuitState.CLOSED
        assert provider_breaker.stats.active_key_index == 0

        for key_stats in provider_breaker.stats.key_stats:
            assert key_stats.current_state == CircuitState.CLOSED
            assert key_stats.failed_calls == 0

    @pytest.mark.asyncio
    async def test_successful_call_increments_success_count(self, provider_breaker):
        """Test that successful call increments success counters."""

        async def test_func():
            return "result"

        result = await provider_breaker.call(test_func, key_index=0)

        assert result == "result"
        assert provider_breaker.stats.successful_calls == 1
        assert provider_breaker.stats.failed_calls == 0

        key_stats = provider_breaker.stats.key_stats[0]
        assert key_stats.successful_calls == 1
        assert key_stats.failed_calls == 0

    @pytest.mark.asyncio
    async def test_key_opens_after_threshold(self, provider_breaker):
        """Test that key opens after failure threshold is exceeded."""

        async def test_func():
            raise Exception("API error")

        # Trigger failures to open key 0
        for _ in range(3):
            with pytest.raises(Exception):  # noqa: B017 - We expect any Exception to trigger circuit breaker
                await provider_breaker.call(test_func, key_index=0)

        # Key 0 should be OPEN now
        key_stats = provider_breaker.stats.key_stats[0]
        assert key_stats.current_state == CircuitState.OPEN
        assert key_stats.failed_calls == 3

    @pytest.mark.asyncio
    async def test_switch_to_next_key_on_failure(self, provider_breaker):
        """Test that breaker switches to next key when current key fails."""
        # First, open key 0
        provider_breaker.stats.key_stats[0].current_state = CircuitState.OPEN
        provider_breaker.stats.key_stats[0].failed_calls = 3
        provider_breaker.stats.key_stats[0].last_failure_time = datetime.now(UTC)

        async def test_func():
            return "success"

        # Call with key 0 should trigger switch to key 1
        with pytest.raises(KeySwitchError) as exc_info:
            await provider_breaker.call(test_func, key_index=0)

        assert exc_info.value.provider == "test_provider"
        assert exc_info.value.failed_key_index == 0
        assert exc_info.value.next_key_index == 1

        # Active key should be updated
        assert provider_breaker.stats.active_key_index == 1

    @pytest.mark.asyncio
    async def test_provider_opens_when_all_keys_open(self, provider_breaker):
        """Test that provider opens when all keys are OPEN."""
        # Mark all keys as OPEN
        for i in range(3):
            provider_breaker.stats.key_stats[i].current_state = CircuitState.OPEN
            provider_breaker.stats.key_stats[i].failed_calls = 3
            provider_breaker.stats.key_stats[i].last_failure_time = datetime.now(UTC)

        async def test_func():
            return "success"

        # Calling with any key should raise ProviderCircuitBreakerOpenError
        with pytest.raises(ProviderCircuitBreakerOpenError):
            await provider_breaker.call(test_func, key_index=0)

        assert provider_breaker.stats.current_state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_get_stats(self, provider_breaker):
        """Test that get_stats returns correct information."""
        provider_breaker.stats.key_stats[0].failed_calls = 2

        stats = provider_breaker.get_stats()

        assert stats["provider"] == "test_provider"
        assert stats["total_keys"] == 3
        assert stats["active_key_index"] == 0
        assert stats["state"] == "closed"
        assert len(stats["key_stats"]) == 3

        # Check key stats
        assert stats["key_stats"][0]["failed_calls"] == 2

    @pytest.mark.asyncio
    async def test_reset(self, provider_breaker):
        """Test that reset clears all failure tracking."""
        # Simulate some failures
        provider_breaker.stats.failed_calls = 5
        provider_breaker.stats.key_stats[0].failed_calls = 3
        provider_breaker.stats.current_state = CircuitState.OPEN

        provider_breaker.reset()

        # Verify reset
        assert provider_breaker.stats.current_state == CircuitState.CLOSED
        assert provider_breaker.stats.failed_calls == 0
        assert provider_breaker.stats.key_stats[0].failed_calls == 0


class TestCircuitBreakerManager:
    """Tests for CircuitBreakerManager with multi-provider fallback."""

    @pytest.fixture
    def manager(self):
        """Create a circuit breaker manager."""
        return CircuitBreakerManager()

    @pytest.mark.asyncio
    async def test_successful_call_on_first_provider(self, manager):
        """Test that successful call on first provider returns result."""
        provider_keys = {
            "provider1": ["key1", "key2"],
            "provider2": ["key1"],
        }

        async def test_func(provider, key_index, api_key):
            return f"{provider}-{key_index}-{api_key}"

        result = await manager.call_with_fallback(
            providers=["provider1", "provider2"],
            provider_keys=provider_keys,
            func=test_func,
        )

        assert result == "provider1-0-key1"

    @pytest.mark.asyncio
    async def test_fallback_to_second_provider(self, manager):
        """Test that failed provider triggers fallback to next provider."""
        provider_keys = {
            "provider1": ["key1"],
            "provider2": ["key1"],
        }

        async def test_func(provider, key_index, api_key):
            if provider == "provider1":
                raise Exception("Provider1 failed")
            return f"success-{provider}"

        result = await manager.call_with_fallback(
            providers=["provider1", "provider2"],
            provider_keys=provider_keys,
            func=test_func,
        )

        assert result == "success-provider2"

    @pytest.mark.asyncio
    async def test_fallback_to_second_key(self, manager):
        """Test that failed key triggers fallback to next key within provider."""
        provider_keys = {
            "provider1": ["key1", "key2"],
        }

        call_count = {"key1": 0, "key2": 0}

        async def test_func(provider, key_index, api_key):
            call_count[api_key] += 1
            if api_key == "key1":
                raise Exception("Key1 failed")
            return f"success-{api_key}"

        result = await manager.call_with_fallback(
            providers=["provider1"],
            provider_keys=provider_keys,
            func=test_func,
        )

        # Should have tried key1 once, then succeeded with key2
        assert call_count["key1"] >= 1
        assert result == "success-key2"

    @pytest.mark.asyncio
    async def test_all_providers_fail_raises_error(self, manager):
        """Test that failure of all providers raises RuntimeError."""
        provider_keys = {
            "provider1": ["key1"],
            "provider2": ["key1"],
        }

        async def test_func(provider, key_index, api_key):
            raise Exception(f"{provider} failed")

        with pytest.raises(RuntimeError, match="All providers and keys failed"):
            await manager.call_with_fallback(
                providers=["provider1", "provider2"],
                provider_keys=provider_keys,
                func=test_func,
            )

    @pytest.mark.asyncio
    async def test_get_all_stats(self, manager):
        """Test that get_all_stats returns stats for all providers."""
        provider_keys = {
            "provider1": ["key1", "key2"],
        }

        async def test_func(provider, key_index, api_key):
            return "success"

        await manager.call_with_fallback(
            providers=["provider1"],
            provider_keys=provider_keys,
            func=test_func,
        )

        stats = manager.get_all_stats()
        assert "provider1" in stats
        assert stats["provider1"]["total_keys"] == 2

    @pytest.mark.asyncio
    async def test_reset_all(self, manager):
        """Test that reset_all clears all breaker state."""
        provider_keys = {
            "provider1": ["key1"],
        }

        async def test_func(provider, key_index, api_key):
            raise Exception("Failed")

        # Trigger some failures
        with pytest.raises(RuntimeError):
            await manager.call_with_fallback(
                providers=["provider1"],
                provider_keys=provider_keys,
                func=test_func,
            )

        # Verify we have a breaker with failures
        stats = manager.get_all_stats()
        assert stats["provider1"]["failed_calls"] > 0

        # Reset
        await manager.reset_all()

        # Verify reset
        stats = manager.get_all_stats()
        assert stats["provider1"]["failed_calls"] == 0
        assert stats["provider1"]["state"] == "closed"


class TestCircuitBreakerRecovery:
    """Tests for circuit breaker recovery from failures."""

    @pytest.mark.asyncio
    async def test_key_recovers_after_timeout(self):
        """Test that key transitions to CLOSED after successful call following timeout."""
        breaker = ProviderCircuitBreaker(
            provider="test",
            total_keys=2,
            timeout_seconds=0.1,  # Short timeout for testing
        )

        # Mark key 0 as OPEN
        breaker.stats.key_stats[0].current_state = CircuitState.OPEN
        breaker.stats.key_stats[0].failed_calls = 5
        breaker.stats.key_stats[0].last_failure_time = datetime.now(tz=UTC) - timedelta(seconds=1)

        async def test_func():
            return "success"

        # Call should trigger transition to HALF_OPEN, then to CLOSED on success
        result = await breaker.call(test_func, key_index=0)

        assert result == "success"
        # After successful call, the key should transition to CLOSED
        assert breaker.stats.key_stats[0].current_state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_key_closes_after_success_in_half_open(self):
        """Test that key closes after success in HALF_OPEN state."""
        breaker = ProviderCircuitBreaker(
            provider="test",
            total_keys=1,
            timeout_seconds=0.1,
        )

        # Set key to HALF_OPEN
        breaker.stats.key_stats[0].current_state = CircuitState.HALF_OPEN

        async def test_func():
            return "success"

        # Successful call should close the circuit
        await breaker.call(test_func, key_index=0)

        assert breaker.stats.key_stats[0].current_state == CircuitState.CLOSED
