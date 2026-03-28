"""Circuit breaker pattern for external service calls (Task #96).

Prevents cascading failures when external services (LLM providers, ChromaDB,
database) are unavailable. Implements the standard circuit breaker pattern with
CLOSED → OPEN → HALF_OPEN state transitions.

Usage:
    breaker = get_breaker("llm_provider")
    try:
        result = await breaker.call(my_async_func, arg1, arg2)
    except ServiceDegradedError:
        # Handle degraded mode
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_FAILURE_THRESHOLD = 5
DEFAULT_RECOVERY_TIMEOUT = 60.0  # seconds before trying half-open
DEFAULT_HALF_OPEN_MAX_CALLS = 3  # calls allowed in half-open to probe
DEFAULT_SUCCESS_THRESHOLD = 3  # consecutive successes to close circuit
DEFAULT_CALL_TIMEOUT = 30.0  # seconds per call


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing fast, rejecting calls
    HALF_OPEN = "half_open"  # Probing with limited calls


class ServiceDegradedError(Exception):
    """Raised when circuit breaker is open and rejects a call."""

    def __init__(self, service_name: str, state: CircuitState, detail: str = ""):
        self.service_name = service_name
        self.state = state
        self.detail = detail
        super().__init__(
            f"Service '{service_name}' is {state.value}. {detail or 'Please retry later.'}"
        )


class CircuitBreaker:
    """Circuit breaker for a single external service.

    State transitions:
        CLOSED  → (failure_threshold reached) → OPEN
        OPEN    → (recovery_timeout elapsed)   → HALF_OPEN
        HALF_OPEN → (success_threshold reached) → CLOSED
        HALF_OPEN → (any failure)               → OPEN
    """

    def __init__(
        self,
        service_name: str,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
        recovery_timeout: float = DEFAULT_RECOVERY_TIMEOUT,
        half_open_max_calls: int = DEFAULT_HALF_OPEN_MAX_CALLS,
        success_threshold: int = DEFAULT_SUCCESS_THRESHOLD,
        call_timeout: float = DEFAULT_CALL_TIMEOUT,
    ):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.success_threshold = success_threshold
        self.call_timeout = call_timeout

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time: Optional[float] = None
        self._last_success_time: Optional[float] = None
        self._state_changed_at = time.monotonic()
        self._total_calls = 0
        self._total_failures = 0

    @property
    def state(self) -> CircuitState:
        """Current circuit state, with automatic OPEN → HALF_OPEN transition."""
        if self._state == CircuitState.OPEN and self._last_failure_time is not None:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
        return self._state

    @property
    def is_available(self) -> bool:
        """Whether the circuit allows requests through."""
        return self.state != CircuitState.OPEN

    @property
    def is_degraded(self) -> bool:
        """Whether the circuit is in degraded (half-open) state."""
        return self.state == CircuitState.HALF_OPEN

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def success_count(self) -> int:
        return self._success_count

    @property
    def last_failure_time(self) -> Optional[float]:
        return self._last_failure_time

    @property
    def last_success_time(self) -> Optional[float]:
        return self._last_success_time

    def get_status(self) -> dict[str, Any]:
        """Return current breaker status as a dict."""
        return {
            "service": self.service_name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_calls": self._total_calls,
            "total_failures": self._total_failures,
            "last_failure_time": self._last_failure_time,
            "last_success_time": self._last_success_time,
        }

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute an async callable with circuit breaker protection.

        Args:
            func: Async callable to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            Result of func(*args, **kwargs).

        Raises:
            ServiceDegradedError: If circuit is OPEN.
            Any: Re-raises exceptions from func (and records failures).
        """
        current_state = self.state  # triggers OPEN→HALF_OPEN if timeout elapsed

        if current_state == CircuitState.OPEN:
            raise ServiceDegradedError(
                self.service_name, CircuitState.OPEN, "Circuit breaker is open"
            )

        if current_state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                raise ServiceDegradedError(
                    self.service_name,
                    CircuitState.HALF_OPEN,
                    "Half-open probe limit reached",
                )
            self._half_open_calls += 1

        self._total_calls += 1

        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.call_timeout,
            )
        except asyncio.TimeoutError:
            await self._record_failure()
            raise ServiceDegradedError(
                self.service_name, self.state, f"Call timed out after {self.call_timeout}s"
            ) from None
        except Exception:
            await self._record_failure()
            raise

        self._record_success()
        return result

    def _record_success(self) -> None:
        """Record a successful call."""
        self._success_count += 1
        self._last_success_time = time.monotonic()
        self._failure_count = 0  # reset consecutive failures

        if self._state == CircuitState.HALF_OPEN:
            if self._success_count >= self.success_threshold:
                self._transition_to(CircuitState.CLOSED)
                logger.info(
                    "Circuit CLOSED for '%s' after %d consecutive successes",
                    self.service_name,
                    self._success_count,
                )

    async def _record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._total_failures += 1
        self._last_failure_time = time.monotonic()
        self._success_count = 0  # reset consecutive successes

        if self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open immediately reopens
            self._transition_to(CircuitState.OPEN)
            logger.warning(
                "Circuit re-OPENED for '%s' (failure during half-open probe)",
                self.service_name,
            )
        elif self._failure_count >= self.failure_threshold:
            self._transition_to(CircuitState.OPEN)
            logger.warning(
                "Circuit OPENED for '%s' after %d consecutive failures (threshold=%d)",
                self.service_name,
                self._failure_count,
                self.failure_threshold,
            )

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state and reset counters."""
        old_state = self._state
        self._state = new_state
        self._state_changed_at = time.monotonic()

        if new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._success_count = 0
        elif new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0

        logger.debug("Circuit '%s': %s → %s", self.service_name, old_state.value, new_state.value)

    def reset(self) -> None:
        """Manually reset the breaker to CLOSED state."""
        self._transition_to(CircuitState.CLOSED)
        self._total_calls = 0
        self._total_failures = 0
        logger.info("Circuit manually reset for '%s'", self.service_name)


# ---------------------------------------------------------------------------
# Global registry
# ---------------------------------------------------------------------------

_breakers: dict[str, CircuitBreaker] = {}


def get_breaker(service_name: str, **kwargs: Any) -> CircuitBreaker:
    """Get or create a circuit breaker for a named service."""
    if service_name not in _breakers:
        _breakers[service_name] = CircuitBreaker(service_name, **kwargs)
    return _breakers[service_name]


def reset_all_breakers() -> None:
    """Reset all circuit breakers (useful for testing)."""
    _breakers.clear()
    logger.info("All circuit breakers have been reset")


def get_all_breaker_states() -> dict[str, dict[str, Any]]:
    """Get the state of all registered circuit breakers."""
    return {name: breaker.get_status() for name, breaker in _breakers.items()}
