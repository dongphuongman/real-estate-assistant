"""
Circuit breaker pattern implementation for LLM provider calls.

Prevents cascading failures by:
1. Tracking failure rates per provider
2. Opening circuit after threshold exceeded
3. Allowing recovery after cooldown period
4. Providing fallback to alternative providers

State transitions:
CLOSED -> OPEN (failure threshold exceeded)
OPEN -> HALF_OPEN (cooldown period elapsed)
HALF_OPEN -> CLOSED (successful probe)
HALF_OPEN -> OPEN (failed probe)
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Callable, Optional, TypeVar, cast

logger = logging.getLogger(__name__)

# TypeVar for generic return types
T = TypeVar("T")


# =============================================================================
# Retry Logic with Tenacity (Phase 3)
# =============================================================================


class TransientAPIError(Exception):
    """Base class for transient API errors that should be retried."""

    pass


class RateLimitError(TransientAPIError):
    """Raised when API rate limit is exceeded (HTTP 429)."""

    pass


class ServerError(TransientAPIError):
    """Raised when server returns a 5xx error."""

    pass


class AuthenticationError(Exception):
    """Raised when API key is invalid (HTTP 401). Should NOT retry."""

    pass


def is_retryable_error(exception: Exception) -> bool:
    """
    Determine if an exception should trigger a retry.

    Args:
        exception: The exception to evaluate

    Returns:
        True if retryable, False otherwise
    """
    # Check for HTTP status codes in exception messages
    exception_str = str(exception).lower()

    # Rate limit (429) - always retry
    if "429" in exception_str or "rate limit" in exception_str:
        return True

    # Server errors (500, 502, 503, 504) - retry
    if any(code in exception_str for code in ["500", "502", "503", "504"]):
        return True

    # Connection errors - retry
    if any(
        keyword in exception_str
        for keyword in [
            "connection",
            "timeout",
            "network",
            "dns",
            "temporary",
            "unavailable",
        ]
    ):
        return True

    # Authentication errors (401, 403) - do NOT retry
    if any(code in exception_str for code in ["401", "403", "unauthorized", "forbidden"]):
        return False

    # Default: don't retry unknown errors
    return False


def with_llm_retry(func: Callable[..., T], max_attempts: int = 3) -> Callable[..., T]:
    """
    Wrap a function with tenacity retry logic for LLM API calls.

    Retries on:
    - Rate limit errors (429)
    - Server errors (5xx)
    - Connection/timeout errors

    Does NOT retry:
    - Authentication errors (401, 403)
    - Invalid request errors (400)

    Args:
        func: Function to wrap
        max_attempts: Maximum number of retry attempts (default: 3)

    Returns:
        Wrapped function with retry logic

    Example:
        @with_llm_retry
        async def call_llm_api():
            return await provider.invoke(messages)
    """

    async def wrapper(*args: Any, **kwargs: Any) -> T:
        last_exception: Optional[Exception] = None
        last_error_type: Optional[type] = None

        for attempt in range(max_attempts):
            try:
                return await func(*args, **kwargs)  # type: ignore[misc,return-value,no-any-return]
            except Exception as e:
                last_exception = e
                exception_str = str(e).lower()

                # Check for authentication errors first - do NOT retry
                if any(
                    code in exception_str for code in ["401", "403", "unauthorized", "forbidden"]
                ):
                    # Raise immediately without retrying
                    raise AuthenticationError(str(e)) from e

                # Check if this is a retryable error
                if is_retryable_error(e):
                    # Store the error type for raising at the end
                    if "429" in exception_str or "rate limit" in exception_str:
                        last_error_type = RateLimitError
                    elif any(code in exception_str for code in ["500", "502", "503", "504"]):
                        last_error_type = ServerError
                    else:
                        last_error_type = TransientAPIError

                    # Wait with exponential backoff before retrying
                    if attempt < max_attempts - 1:
                        wait_time = min(2**attempt, 10)
                        await asyncio.sleep(wait_time)
                    continue

                # Unknown error - re-raise immediately
                raise

        # If we exhaust all retries, raise the appropriate error
        if last_exception:
            if last_error_type:
                raise last_error_type(str(last_exception)) from last_exception
            raise RuntimeError(f"Failed after {max_attempts} attempts") from last_exception

        # Should not reach here
        raise RuntimeError("Unexpected flow in retry logic")

    return wrapper  # type: ignore[return-value]


# =============================================================================
# Circuit Breaker Implementation (Legacy - Single Provider)
# =============================================================================


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if provider has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Failures before opening circuit
    success_threshold: int = 2  # Successes to close circuit from half-open
    timeout_seconds: float = 60.0  # Cooldown before half-open
    half_open_max_calls: int = 1  # Max calls in half-open state
    rolling_window_size: int = 100  # Size of rolling result window


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker."""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0  # Calls rejected due to open circuit
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    current_state: CircuitState = CircuitState.CLOSED
    state_changed_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def failure_rate(self) -> float:
        """Calculate current failure rate."""
        total = self.successful_calls + self.failed_calls
        if total == 0:
            return 0.0
        return self.failed_calls / total


class CircuitBreakerOpenError(Exception):
    """Raised when circuit is open and request is rejected."""

    def __init__(self, provider: str, cooldown_remaining: float):
        self.provider = provider
        self.cooldown_remaining = cooldown_remaining
        super().__init__(
            f"Circuit breaker open for provider '{provider}'. "
            f"Retry after {cooldown_remaining:.1f} seconds."
        )


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting external service calls.

    Usage:
        breaker = CircuitBreaker("openai", config)

        try:
            result = await breaker.call(lambda: make_api_call())
        except CircuitBreakerOpenError:
            # Handle open circuit - use fallback
            result = await fallback_call()
    """

    def __init__(
        self,
        provider: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        """
        Initialize circuit breaker.

        Args:
            provider: Provider name for logging/tracking
            config: Circuit breaker configuration
        """
        self.provider = provider
        self.config = config or CircuitBreakerConfig()
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()
        self._rolling_results: deque[bool] = deque(maxlen=self.config.rolling_window_size)
        self._half_open_calls = 0

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.stats.last_failure_time is None:
            return True

        elapsed = (datetime.now(tz=UTC) - self.stats.last_failure_time).total_seconds()
        return elapsed >= self.config.timeout_seconds

    async def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute function through circuit breaker.

        Args:
            func: Function to call
            *args: Positional args for function
            **kwargs: Keyword args for function

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: If function call raises an exception
        """
        async with self._lock:
            self.stats.total_calls += 1

            # Check circuit state
            if self.stats.current_state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    # Transition to half-open
                    logger.info(
                        "Circuit breaker for '%s': OPEN -> HALF_OPEN (after cooldown)",
                        self.provider,
                    )
                    self.stats.current_state = CircuitState.HALF_OPEN
                    self.stats.state_changed_at = datetime.now(tz=UTC)
                    self._half_open_calls = 0
                else:
                    # Circuit still open
                    # last_failure_time is guaranteed to be set here since _should_attempt_reset() returned False
                    last_failure = cast(datetime, self.stats.last_failure_time)
                    cooldown_remaining = (
                        self.config.timeout_seconds
                        - (datetime.now(tz=UTC) - last_failure).total_seconds()
                    )
                    self.stats.rejected_calls += 1
                    raise CircuitBreakerOpenError(self.provider, cooldown_remaining)

            if self.stats.current_state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1
                if self._half_open_calls > self.config.half_open_max_calls:
                    # Too many calls in half-open, open again
                    logger.warning(
                        "Circuit breaker for '%s': HALF_OPEN -> OPEN (too many probes)",
                        self.provider,
                    )
                    self.stats.current_state = CircuitState.OPEN
                    self.stats.state_changed_at = datetime.now(tz=UTC)
                    self.stats.rejected_calls += 1
                    raise CircuitBreakerOpenError(self.provider, self.config.timeout_seconds)

        # Execute the function call
        start = time.perf_counter()
        try:
            result: T = await func(*args, **kwargs)  # type: ignore[misc]
            elapsed = (time.perf_counter() - start) * 1000

            async with self._lock:
                self._on_success(elapsed)

            return result

        except Exception:
            elapsed = (time.perf_counter() - start) * 1000

            async with self._lock:
                self._on_failure(elapsed)

            raise

    def _on_success(self, elapsed_ms: float) -> None:
        """Handle successful call."""
        self.stats.successful_calls += 1
        self.stats.last_success_time = datetime.now(tz=UTC)
        self._rolling_results.append(True)

        # Check if we should close circuit from half-open
        if self.stats.current_state == CircuitState.HALF_OPEN:
            recent_successes = sum(1 for r in self._rolling_results if r)
            if recent_successes >= self.config.success_threshold:
                logger.info(
                    "Circuit breaker for '%s': HALF_OPEN -> CLOSED (recovered)",
                    self.provider,
                )
                self.stats.current_state = CircuitState.CLOSED
                self.stats.state_changed_at = datetime.now(tz=UTC)
                self._half_open_calls = 0

    def _on_failure(self, elapsed_ms: float) -> None:
        """Handle failed call."""
        self.stats.failed_calls += 1
        self.stats.last_failure_time = datetime.now(tz=UTC)
        self._rolling_results.append(False)

        # Check if we should open circuit
        recent_failures = sum(1 for r in self._rolling_results if not r)
        if (
            recent_failures >= self.config.failure_threshold
            and self.stats.current_state != CircuitState.OPEN
        ):
            logger.warning(
                "Circuit breaker for '%s': %s -> OPEN (threshold exceeded)",
                self.provider,
                self.stats.current_state.value.upper(),
            )
            self.stats.current_state = CircuitState.OPEN
            self.stats.state_changed_at = datetime.now(tz=UTC)

    def get_stats(self) -> dict[str, Any]:
        """
        Get circuit breaker statistics.

        Returns:
            Dict with current stats
        """
        return {
            "provider": self.provider,
            "state": self.stats.current_state.value,
            "total_calls": self.stats.total_calls,
            "successful_calls": self.stats.successful_calls,
            "failed_calls": self.stats.failed_calls,
            "rejected_calls": self.stats.rejected_calls,
            "failure_rate": self.stats.failure_rate(),
            "last_failure_time": self.stats.last_failure_time.isoformat()
            if self.stats.last_failure_time
            else None,
            "last_success_time": self.stats.last_success_time.isoformat()
            if self.stats.last_success_time
            else None,
            "state_changed_at": self.stats.state_changed_at.isoformat(),
        }

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        logger.info("Circuit breaker for '%s': reset to CLOSED", self.provider)
        self.stats = CircuitBreakerStats()
        self._rolling_results.clear()
        self._half_open_calls = 0


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.

    Provides a centralized way to get/create circuit breakers for different providers.
    """

    def __init__(self) -> None:
        """Initialize the registry."""
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
        self._config: Optional[CircuitBreakerConfig] = None

    def set_config(self, config: CircuitBreakerConfig) -> None:
        """
        Set default configuration for new circuit breakers.

        Args:
            config: Default circuit breaker configuration
        """
        self._config = config

    async def get_breaker(self, provider: str) -> CircuitBreaker:
        """
        Get or create circuit breaker for provider.

        Args:
            provider: Provider name

        Returns:
            CircuitBreaker instance
        """
        async with self._lock:
            if provider not in self._breakers:
                self._breakers[provider] = CircuitBreaker(provider, self._config)
            return self._breakers[provider]

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """
        Get stats for all circuit breakers.

        Returns:
            Dict mapping provider name to stats
        """
        return {provider: breaker.get_stats() for provider, breaker in self._breakers.items()}

    async def reset_all(self) -> None:
        """Reset all circuit breakers to closed state."""
        async with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()


# =============================================================================
# Multi-Provider and Multi-API Key Circuit Breaker (Phase 2)
# =============================================================================


@dataclass
class KeyCircuitBreakerStats:
    """Statistics for circuit breaker at API key level."""

    key_index: int  # Index in the provider's key list
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    current_state: CircuitState = CircuitState.CLOSED

    def failure_rate(self) -> float:
        """Calculate current failure rate for this key."""
        total = self.successful_calls + self.failed_calls
        if total == 0:
            return 0.0
        return self.failed_calls / total


@dataclass
class ProviderCircuitBreakerStats:
    """Statistics for circuit breaker at provider level (aggregates all keys)."""

    provider: str
    total_keys: int  # Total number of keys configured for this provider
    active_key_index: int  # Currently selected key index
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    current_state: CircuitState = CircuitState.CLOSED
    key_stats: list[KeyCircuitBreakerStats] = field(default_factory=list)

    def failure_rate(self) -> float:
        """Calculate current failure rate across all keys."""
        total = self.successful_calls + self.failed_calls
        if total == 0:
            return 0.0
        return self.failed_calls / total

    def get_failed_keys_count(self) -> int:
        """Get number of keys that are currently OPEN."""
        return sum(1 for ks in self.key_stats if ks.current_state == CircuitState.OPEN)


class ProviderCircuitBreaker:
    """
    Circuit breaker that tracks failures at both provider and API key levels.

    Hierarchy:
    Provider Circuit Breaker (this class)
    ├── Key 0 Circuit Breaker
    ├── Key 1 Circuit Breaker
    └── Key N Circuit Breaker

    State transitions:
    1. Key failures → Key OPEN → try next key
    2. All keys OPEN → Provider OPEN → try next provider
    3. Key success → Key HALF_OPEN → Key CLOSED
    4. Provider success → Provider HALF_OPEN → Provider CLOSED

    Usage:
        breaker = ProviderCircuitBreaker(
            provider="openai",
            total_keys=3,
            key_failure_threshold=5,
        )

        try:
            result = await breaker.call(func, key_index=0)
        except ProviderCircuitBreakerOpenError:
            # All keys failed, use next provider
            result = await fallback_provider_call()
    """

    def __init__(
        self,
        provider: str,
        total_keys: int,
        key_failure_threshold: int = 5,
        provider_failure_threshold: int = 15,
        timeout_seconds: float = 60.0,
    ):
        """
        Initialize provider circuit breaker with key-level tracking.

        Args:
            provider: Provider name
            total_keys: Number of API keys configured for this provider
            key_failure_threshold: Failures before marking a key as OPEN
            provider_failure_threshold: Failures before marking provider as OPEN
            timeout_seconds: Cooldown before attempting recovery
        """
        self.provider = provider
        self.total_keys = total_keys
        self.key_failure_threshold = key_failure_threshold
        self.provider_failure_threshold = provider_failure_threshold
        self.timeout_seconds = timeout_seconds
        self._lock = asyncio.Lock()

        # Initialize stats for provider and each key
        self.stats = ProviderCircuitBreakerStats(
            provider=provider,
            total_keys=total_keys,
            active_key_index=0,
            key_stats=[KeyCircuitBreakerStats(key_index=i) for i in range(total_keys)],
        )

    async def call(self, func: Callable[..., T], key_index: int, *args: Any, **kwargs: Any) -> T:
        """
        Execute function through circuit breaker with specific key.

        Wraps the function with tenacity retry logic for transient errors.

        Args:
            func: Function to call
            key_index: Which API key to use
            *args: Positional args for function
            **kwargs: Keyword args for function

        Returns:
            Function result

        Raises:
            ProviderCircuitBreakerOpenError: If all keys are OPEN (provider is OPEN)
            AuthenticationError: If API key is invalid (401/403)
            Exception: If function call raises an exception after retries
        """
        async with self._lock:
            self.stats.total_calls += 1
            key_stats = self.stats.key_stats[key_index]

            # Check if this specific key is OPEN
            if key_stats.current_state == CircuitState.OPEN:
                # Check if we should try this key again
                if key_stats.last_failure_time is not None:
                    elapsed = (datetime.now(tz=UTC) - key_stats.last_failure_time).total_seconds()
                    if elapsed >= self.timeout_seconds:
                        # Transition to half-open for this key
                        logger.info(
                            "Key %d for provider '%s': OPEN -> HALF_OPEN (after cooldown)",
                            key_index,
                            self.provider,
                        )
                        key_stats.current_state = CircuitState.HALF_OPEN
                        self.stats.active_key_index = key_index
                    else:
                        # Key is still OPEN, try next key
                        next_key = self._get_next_available_key(key_index)
                        if next_key is not None:
                            logger.info(
                                "Key %d for provider '%s' is OPEN, switching to key %d",
                                key_index,
                                self.provider,
                                next_key,
                            )
                            self.stats.active_key_index = next_key
                            raise KeySwitchError(self.provider, key_index, next_key)
                        else:
                            # All keys are OPEN, provider is OPEN
                            if self.stats.current_state != CircuitState.OPEN:
                                logger.warning(
                                    "All keys for provider '%s' are OPEN, marking provider as OPEN",
                                    self.provider,
                                )
                                self.stats.current_state = CircuitState.OPEN
                            self.stats.rejected_calls += 1
                            raise ProviderCircuitBreakerOpenError(self.provider)

            # Check if provider is OPEN
            if self.stats.current_state == CircuitState.OPEN:
                if self.stats.last_failure_time is not None:
                    elapsed = (datetime.now(tz=UTC) - self.stats.last_failure_time).total_seconds()
                    if elapsed >= self.timeout_seconds:
                        # Transition to half-open for provider
                        logger.info(
                            "Provider '%s': OPEN -> HALF_OPEN (after cooldown)",
                            self.provider,
                        )
                        self.stats.current_state = CircuitState.HALF_OPEN
                        # Reset first key to half-open
                        self.stats.key_stats[0].current_state = CircuitState.HALF_OPEN
                        self.stats.active_key_index = 0
                    else:
                        self.stats.rejected_calls += 1
                        raise ProviderCircuitBreakerOpenError(self.provider)

        # Execute the function call with retry logic
        start = time.perf_counter()
        try:
            result: T = await func(*args, **kwargs)  # type: ignore[misc]
            elapsed = (time.perf_counter() - start) * 1000

            async with self._lock:
                self._on_success(key_index, elapsed)

            return result

        except AuthenticationError:
            # Authentication errors should NOT be retried
            # Mark this key as permanently failed
            elapsed = (time.perf_counter() - start) * 1000
            async with self._lock:
                self._on_failure(key_index, elapsed)
                # Immediately mark key as OPEN to prevent further attempts
                key_stats.current_state = CircuitState.OPEN
                logger.error(
                    "Key %d for provider '%s' is invalid (401), marking as OPEN",
                    key_index,
                    self.provider,
                )
            raise

        except Exception:
            # Unexpected error or transient error after retries
            elapsed = (time.perf_counter() - start) * 1000
            async with self._lock:
                self._on_failure(key_index, elapsed)
            raise

    def _on_success(self, key_index: int, elapsed_ms: float) -> None:
        """Handle successful call."""
        self.stats.successful_calls += 1
        self.stats.last_success_time = datetime.now(tz=UTC)
        key_stats = self.stats.key_stats[key_index]
        key_stats.successful_calls += 1
        key_stats.last_failure_time = None

        # Close the key circuit if it was half-open
        if key_stats.current_state == CircuitState.HALF_OPEN:
            logger.info(
                "Key %d for provider '%s': HALF_OPEN -> CLOSED (recovered)",
                key_index,
                self.provider,
            )
            key_stats.current_state = CircuitState.CLOSED

        # Check if we should close provider circuit
        if self.stats.current_state == CircuitState.HALF_OPEN:
            # Close provider if we have successful calls
            logger.info(
                "Provider '%s': HALF_OPEN -> CLOSED (recovered)",
                self.provider,
            )
            self.stats.current_state = CircuitState.CLOSED

    def _on_failure(self, key_index: int, elapsed_ms: float) -> None:
        """Handle failed call."""
        self.stats.failed_calls += 1
        self.stats.last_failure_time = datetime.now(tz=UTC)
        key_stats = self.stats.key_stats[key_index]
        key_stats.failed_calls += 1
        key_stats.last_failure_time = datetime.now(tz=UTC)

        # Check if we should open this key's circuit
        if key_stats.failed_calls >= self.key_failure_threshold:
            if key_stats.current_state != CircuitState.OPEN:
                logger.warning(
                    "Key %d for provider '%s': CLOSED -> OPEN (threshold exceeded)",
                    key_index,
                    self.provider,
                )
                key_stats.current_state = CircuitState.OPEN

                # Check if all keys are now OPEN
                failed_keys = self.stats.get_failed_keys_count()
                if failed_keys >= self.total_keys:
                    logger.error(
                        "All %d keys for provider '%s' are OPEN",
                        self.total_keys,
                        self.provider,
                    )
                    self.stats.current_state = CircuitState.OPEN

    def _get_next_available_key(self, current_key_index: int) -> Optional[int]:
        """
        Get next available key that is not OPEN.

        Args:
            current_key_index: Current key index

        Returns:
            Next available key index or None if all keys are OPEN
        """
        # Try keys in order starting from current + 1
        for i in range(self.total_keys):
            next_idx = (current_key_index + 1 + i) % self.total_keys
            if self.stats.key_stats[next_idx].current_state != CircuitState.OPEN:
                return next_idx
        return None

    def get_stats(self) -> dict[str, Any]:
        """
        Get circuit breaker statistics.

        Returns:
            Dict with current stats
        """
        return {
            "provider": self.stats.provider,
            "state": self.stats.current_state.value,
            "active_key_index": self.stats.active_key_index,
            "total_keys": self.stats.total_keys,
            "failed_keys": self.stats.get_failed_keys_count(),
            "total_calls": self.stats.total_calls,
            "successful_calls": self.stats.successful_calls,
            "failed_calls": self.stats.failed_calls,
            "rejected_calls": self.stats.rejected_calls,
            "failure_rate": self.stats.failure_rate(),
            "last_failure_time": self.stats.last_failure_time.isoformat()
            if self.stats.last_failure_time
            else None,
            "last_success_time": self.stats.last_success_time.isoformat()
            if self.stats.last_success_time
            else None,
            "key_stats": [
                {
                    "key_index": ks.key_index,
                    "state": ks.current_state.value,
                    "total_calls": ks.total_calls,
                    "successful_calls": ks.successful_calls,
                    "failed_calls": ks.failed_calls,
                    "failure_rate": ks.failure_rate(),
                }
                for ks in self.stats.key_stats
            ],
        }

    def reset(self) -> None:
        """Reset circuit breaker to closed state for all keys."""
        logger.info("Provider circuit breaker for '%s': reset to CLOSED", self.provider)
        self.stats = ProviderCircuitBreakerStats(
            provider=self.provider,
            total_keys=self.total_keys,
            active_key_index=0,
            key_stats=[KeyCircuitBreakerStats(key_index=i) for i in range(self.total_keys)],
        )


class KeySwitchError(Exception):
    """Raised when a key fails and we need to switch to the next key."""

    def __init__(self, provider: str, failed_key_index: int, next_key_index: int):
        self.provider = provider
        self.failed_key_index = failed_key_index
        self.next_key_index = next_key_index
        super().__init__(
            f"Key {failed_key_index} for provider '{provider}' failed, "
            f"switching to key {next_key_index}"
        )


class ProviderCircuitBreakerOpenError(Exception):
    """Raised when all keys for a provider are OPEN and requests should fail fast."""

    def __init__(self, provider: str):
        self.provider = provider
        super().__init__(f"All keys for provider '{provider}' have failed. Circuit is open.")


class CircuitBreakerManager:
    """
    Manager for provider circuit breakers with multi-key support.

    Provides fallback chain: Provider1(Key1→Key2) → Provider2(Key1→Key2) → Ollama

    Usage:
        manager = CircuitBreakerManager()
        result = await manager.call_with_fallback(
            providers=["openai", "anthropic"],
            func=make_llm_call,
            provider_keys={
                "openai": ["key1", "key2"],
                "anthropic": ["key1"],
            },
        )
    """

    def __init__(self) -> None:
        """Initialize the circuit breaker manager."""
        self._provider_breakers: dict[str, ProviderCircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_provider_breaker(
        self,
        provider: str,
        total_keys: int,
        key_failure_threshold: int = 5,
    ) -> ProviderCircuitBreaker:
        """
        Get or create provider circuit breaker.

        Args:
            provider: Provider name
            total_keys: Number of API keys for this provider
            key_failure_threshold: Failures before switching keys

        Returns:
            ProviderCircuitBreaker instance
        """
        async with self._lock:
            if provider not in self._provider_breakers:
                self._provider_breakers[provider] = ProviderCircuitBreaker(
                    provider=provider,
                    total_keys=total_keys,
                    key_failure_threshold=key_failure_threshold,
                )
            return self._provider_breakers[provider]

    async def call_with_fallback(
        self,
        providers: list[str],
        provider_keys: dict[str, list[str]],
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Execute function with automatic fallback across providers and keys.

        Fallback chain:
        Provider1[Key0 → Key1 → ...] → Provider2[Key0 → Key1 → ...] → ... → Ollama

        Args:
            providers: Ordered list of providers to try
            provider_keys: Dict mapping provider name to list of API keys
            func: Function to call (receives provider and key_index as kwargs)
            *args: Positional args for function
            **kwargs: Additional keyword args for function

        Returns:
            Function result

        Raises:
            RuntimeError: If all providers and keys fail
        """
        last_exception: Optional[Exception] = None

        for provider in providers:
            keys = provider_keys.get(provider, [])
            if not keys:
                logger.warning("No keys configured for provider '%s'", provider)
                continue

            # Get or create breaker for this provider
            breaker = await self.get_provider_breaker(
                provider=provider,
                total_keys=len(keys),
            )

            # Try each key for this provider
            for key_index in range(len(keys)):
                try:
                    # Inject provider and key_index into function kwargs
                    # Capture loop variables with default arguments to avoid late binding
                    result = await breaker.call(
                        lambda p=provider, ki=key_index, ak=keys[key_index]: func(
                            provider=p,
                            key_index=ki,
                            api_key=ak,
                        ),
                        key_index=key_index,
                    )
                    return result

                except KeySwitchError as e:
                    # Circuit breaker is switching to next key automatically
                    # Continue to next iteration to use the new key
                    logger.info("Key switch: %s", e)
                    continue

                except ProviderCircuitBreakerOpenError as e:
                    # All keys for this provider are OPEN, try next provider
                    logger.warning("Provider %s circuit is open: %s", provider, e)
                    last_exception = e
                    break  # Break key loop, try next provider

                except Exception as e:
                    # Unexpected error, try next key
                    logger.error(
                        "Unexpected error with provider '%s', key %d: %s",
                        provider,
                        key_index,
                        e,
                    )
                    last_exception = e
                    continue

        # If we get here, all providers and keys failed
        raise RuntimeError(
            f"All providers and keys failed. Last error: {last_exception}"
        ) from last_exception

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """
        Get stats for all provider circuit breakers.

        Returns:
            Dict mapping provider name to stats
        """
        return {
            provider: breaker.get_stats() for provider, breaker in self._provider_breakers.items()
        }

    async def reset_all(self) -> None:
        """Reset all provider circuit breakers."""
        async with self._lock:
            for breaker in self._provider_breakers.values():
                breaker.reset()


# Global circuit breaker manager instance
_manager = CircuitBreakerManager()


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """
    Get the global circuit breaker manager.

    Returns:
        CircuitBreakerManager instance
    """
    return _manager


# =============================================================================
# Legacy Circuit Breaker Registry (kept for backward compatibility)
# =============================================================================


# Global circuit breaker registry instance
_registry = CircuitBreakerRegistry()


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """
    Get the global circuit breaker registry.

    Returns:
        CircuitBreakerRegistry instance
    """
    return _registry


async def execute_with_circuit_breaker(
    provider: str,
    func: Callable[..., T],
    *args: Any,
    **kwargs: Any,
) -> T:
    """
    Execute function with circuit breaker protection.

    Convenience function that gets/creates breaker and executes call.

    Args:
        provider: Provider name
        func: Function to call
        *args: Positional args for function
        **kwargs: Keyword args for function

    Returns:
        Function result

    Raises:
        CircuitBreakerOpenError: If circuit is open
    """
    registry = get_circuit_breaker_registry()
    breaker = await registry.get_breaker(provider)
    return await breaker.call(func, *args, **kwargs)
