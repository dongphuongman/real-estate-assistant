"""
Streaming utilities for SSE (Server-Sent Events) resilience.

This module provides utilities for:
- Exponential backoff with jitter for reconnection
- Heartbeat mechanism for connection health
- Stream metrics collection
"""

import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class ReconnectionConfig:
    """Configuration for SSE reconnection with exponential backoff."""

    initial_delay_ms: int = 1000
    max_delay_ms: int = 30000
    backoff_multiplier: float = 2.0
    jitter_factor: float = 0.1
    max_retries: int = 10


@dataclass
class HeartbeatConfig:
    """Configuration for SSE heartbeat mechanism."""

    interval_seconds: int = 15
    timeout_seconds: int = 45  # 3x interval for tolerance

    @property
    def timeout_ms(self) -> int:
        """Timeout in milliseconds."""
        return self.timeout_seconds * 1000


@dataclass
class StreamMetrics:
    """
    Metrics collector for streaming sessions.

    Tracks latency, throughput, and error statistics for SSE streams.
    """

    session_id: str
    request_id: str
    start_time: float = field(default_factory=time.perf_counter)
    first_chunk_time: Optional[float] = None
    last_chunk_time: Optional[float] = None
    total_chunks: int = 0
    total_bytes: int = 0
    error_count: int = 0
    _completed: bool = False

    def record_chunk(self, size: int) -> None:
        """
        Record a chunk received from the stream.

        Args:
            size: Size of the chunk in bytes.
        """
        now = time.perf_counter()

        if self.first_chunk_time is None:
            self.first_chunk_time = now

        self.last_chunk_time = now
        self.total_chunks += 1
        self.total_bytes += size

    def record_error(self) -> None:
        """Record an error during streaming."""
        self.error_count += 1

    def complete(self) -> None:
        """Mark the stream as completed."""
        self._completed = True

    def get_latency_ms(self) -> float:
        """
        Get time to first chunk (TTFF) in milliseconds.

        Returns:
            Time from stream start to first chunk, or -1 if no chunks received.
        """
        if self.first_chunk_time is None:
            return -1.0
        return (self.first_chunk_time - self.start_time) * 1000.0

    def get_total_duration_ms(self) -> float:
        """
        Get total stream duration in milliseconds.

        Returns:
            Time from stream start to last chunk, or 0 if no chunks received.
        """
        if self.last_chunk_time is None:
            return 0.0
        return (self.last_chunk_time - self.start_time) * 1000.0

    def get_throughput_bps(self) -> float:
        """
        Get average throughput in bytes per second.

        Returns:
            Throughput in BPS, or 0 if no data transferred.
        """
        duration_s = self.get_total_duration_ms() / 1000.0
        if duration_s <= 0:
            return 0.0
        return self.total_bytes / duration_s

    def to_dict(self) -> dict[str, Any]:
        """
        Convert metrics to dictionary for serialization.

        Returns:
            Dictionary with all metrics values.
        """
        return {
            "session_id": self.session_id,
            "request_id": self.request_id,
            "latency_ms": round(self.get_latency_ms(), 2),
            "duration_ms": round(self.get_total_duration_ms(), 2),
            "throughput_bps": round(self.get_throughput_bps(), 2),
            "total_chunks": self.total_chunks,
            "total_bytes": self.total_bytes,
            "error_count": self.error_count,
            "completed": self._completed,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


def calculate_backoff(attempt: int, config: Optional[ReconnectionConfig] = None) -> int:
    """
    Calculate delay for reconnection attempt with exponential backoff and jitter.

    Uses full jitter strategy to avoid thundering herd problem.

    Args:
        attempt: Current attempt number (0-indexed).
        config: Reconnection configuration. Uses defaults if not provided.

    Returns:
        Delay in milliseconds.

    Example:
        >>> config = ReconnectionConfig(initial_delay_ms=1000, max_delay_ms=30000)
        >>> calculate_backoff(0, config)  # ~1000ms with jitter
        >>> calculate_backoff(5, config)  # ~32000ms capped to 30000ms
    """
    if config is None:
        config = ReconnectionConfig()

    # Calculate base delay with exponential backoff
    base_delay = config.initial_delay_ms * (config.backoff_multiplier**attempt)

    # Cap at max delay
    capped_delay = min(base_delay, config.max_delay_ms)

    # Apply full jitter (random value between 0 and calculated delay)
    # nosemgrep: weak-random.random - acceptable for retry jitter calculation
    jitter = capped_delay * config.jitter_factor * random.random()
    final_delay = capped_delay + jitter

    return int(final_delay)


def should_send_heartbeat(last_heartbeat: float, config: Optional[HeartbeatConfig] = None) -> bool:
    """
    Determine if a heartbeat should be sent based on elapsed time.

    Args:
        last_heartbeat: Timestamp of last heartbeat (from time.time()).
        config: Heartbeat configuration. Uses defaults if not provided.

    Returns:
        True if heartbeat should be sent, False otherwise.
    """
    if config is None:
        config = HeartbeatConfig()

    elapsed = time.time() - last_heartbeat
    return elapsed >= config.interval_seconds


def is_connection_stale(last_activity: float, config: Optional[HeartbeatConfig] = None) -> bool:
    """
    Check if connection is stale based on last activity time.

    Args:
        last_activity: Timestamp of last activity (from time.time()).
        config: Heartbeat configuration. Uses defaults if not provided.

    Returns:
        True if connection is stale (no activity for timeout period).
    """
    if config is None:
        config = HeartbeatConfig()

    elapsed = time.time() - last_activity
    return elapsed >= config.timeout_seconds


def format_sse_heartbeat() -> str:
    """
    Format SSE heartbeat comment.

    SSE comments start with ':' and are ignored by standard EventSource parsers,
    but keep the connection alive by sending data.

    Returns:
        Formatted SSE heartbeat comment.
    """
    return ": heartbeat\n\n"


def format_sse_retry(delay_ms: int) -> str:
    """
    Format SSE retry directive.

    Tells the client to wait specified milliseconds before reconnecting.

    Args:
        delay_ms: Reconnection delay in milliseconds.

    Returns:
        Formatted SSE retry directive.
    """
    return f"retry: {delay_ms}\n\n"


def format_sse_event(event: Optional[str], data: str) -> str:
    """
    Format an SSE event.

    Args:
        event: Optional event name. If None, only data is sent.
        data: Event data.

    Returns:
        Formatted SSE event string.
    """
    parts = []
    if event:
        parts.append(f"event: {event}\n")
    parts.append(f"data: {data}\n\n")
    return "".join(parts)


class StreamingHealthTracker:
    """
    Tracks streaming health for graceful degradation.

    Monitors consecutive failures to determine when to degrade
    from streaming to non-streaming mode.
    """

    def __init__(self, failure_threshold: int = 3):
        """
        Initialize health tracker.

        Args:
            failure_threshold: Number of consecutive failures before degradation.
        """
        self.failure_threshold = failure_threshold
        self._consecutive_failures: int = 0
        self._last_success: Optional[datetime] = None

    def record_success(self) -> None:
        """Record a successful stream."""
        self._consecutive_failures = 0
        self._last_success = datetime.utcnow()

    def record_failure(self) -> None:
        """Record a failed stream."""
        self._consecutive_failures += 1

    def should_degrade(self) -> bool:
        """
        Check if streaming should degrade to non-streaming mode.

        Returns:
            True if degradation threshold reached.
        """
        return self._consecutive_failures >= self.failure_threshold

    def reset(self) -> None:
        """Reset health tracker state."""
        self._consecutive_failures = 0
        self._last_success = None

    @property
    def consecutive_failures(self) -> int:
        """Get current consecutive failure count."""
        return self._consecutive_failures

    @property
    def last_success(self) -> Optional[datetime]:
        """Get timestamp of last successful stream."""
        return self._last_success
