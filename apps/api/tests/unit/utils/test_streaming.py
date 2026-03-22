"""
Unit tests for streaming utilities.

Task #74: Response Streaming Improvements
"""

import time

from utils.streaming import (
    HeartbeatConfig,
    ReconnectionConfig,
    StreamingHealthTracker,
    StreamMetrics,
    calculate_backoff,
    format_sse_event,
    format_sse_heartbeat,
    format_sse_retry,
    is_connection_stale,
    should_send_heartbeat,
)


class TestCalculateBackoff:
    """Tests for calculate_backoff function."""

    def test_initial_delay(self):
        """First attempt should return approximately initial delay."""
        config = ReconnectionConfig(
            initial_delay_ms=1000,
            max_delay_ms=30000,
            backoff_multiplier=2.0,
            jitter_factor=0.1,
        )
        delay = calculate_backoff(0, config)
        # With jitter, should be within 10% of initial
        assert 900 <= delay <= 1100

    def test_exponential_growth(self):
        """Backoff should grow exponentially."""
        config = ReconnectionConfig(
            initial_delay_ms=1000,
            max_delay_ms=30000,
            backoff_multiplier=2.0,
            jitter_factor=0.0,  # No jitter for predictable testing
        )
        assert calculate_backoff(0, config) == 1000
        assert calculate_backoff(1, config) == 2000
        assert calculate_backoff(2, config) == 4000
        assert calculate_backoff(3, config) == 8000

    def test_max_delay_cap(self):
        """Backoff should cap at max_delay."""
        config = ReconnectionConfig(
            initial_delay_ms=1000,
            max_delay_ms=10000,
            backoff_multiplier=2.0,
            jitter_factor=0.0,
        )
        # Attempt 10 would be 1024s without cap
        delay = calculate_backoff(10, config)
        assert delay == 10000

    def test_default_config(self):
        """Should work with default config."""
        delay = calculate_backoff(0)
        assert 900 <= delay <= 1100  # Default is 1000 with 10% jitter

    def test_jitter_applied(self):
        """Jitter should randomize delay."""
        config = ReconnectionConfig(
            initial_delay_ms=1000,
            max_delay_ms=30000,
            backoff_multiplier=2.0,
            jitter_factor=0.5,  # 50% jitter
        )
        # Run multiple times to verify randomness
        delays = [calculate_backoff(0, config) for _ in range(100)]
        # Should have variation
        assert min(delays) < max(delays)
        # All should be within expected range
        for delay in delays:
            assert 1000 <= delay <= 1500


class TestShouldSendHeartbeat:
    """Tests for should_send_heartbeat function."""

    def test_no_heartbeat_needed_initially(self):
        """Should not need heartbeat right after start."""
        config = HeartbeatConfig(interval_seconds=15)
        assert not should_send_heartbeat(time.time(), config)

    def test_heartbeat_needed_after_interval(self):
        """Should need heartbeat after interval elapsed."""
        config = HeartbeatConfig(interval_seconds=15)
        last_heartbeat = time.time() - 20  # 20 seconds ago
        assert should_send_heartbeat(last_heartbeat, config)

    def test_custom_interval(self):
        """Should respect custom interval."""
        config = HeartbeatConfig(interval_seconds=5)
        last_heartbeat = time.time() - 6  # 6 seconds ago
        assert should_send_heartbeat(last_heartbeat, config)


class TestIsConnectionStale:
    """Tests for is_connection_stale function."""

    def test_not_stale_initially(self):
        """Connection should not be stale initially."""
        config = HeartbeatConfig(timeout_seconds=45)
        assert not is_connection_stale(time.time(), config)

    def test_stale_after_timeout(self):
        """Connection should be stale after timeout."""
        config = HeartbeatConfig(timeout_seconds=45)
        last_activity = time.time() - 50  # 50 seconds ago
        assert is_connection_stale(last_activity, config)


class TestStreamMetrics:
    """Tests for StreamMetrics class."""

    def test_record_chunk(self):
        """Recording chunks should update metrics."""
        metrics = StreamMetrics(session_id="test", request_id="req-123")

        metrics.record_chunk(100)
        assert metrics.total_chunks == 1
        assert metrics.total_bytes == 100

        metrics.record_chunk(200)
        assert metrics.total_chunks == 2
        assert metrics.total_bytes == 300

    def test_record_error(self):
        """Recording errors should increment count."""
        metrics = StreamMetrics(session_id="test", request_id="req-123")

        metrics.record_error()
        assert metrics.error_count == 1

        metrics.record_error()
        assert metrics.error_count == 2

    def test_latency_calculation(self):
        """Latency should be time to first chunk."""
        metrics = StreamMetrics(session_id="test", request_id="req-123")

        # No chunks yet
        assert metrics.get_latency_ms() == -1.0

        # Record a chunk
        time.sleep(0.01)  # Small delay
        metrics.record_chunk(100)

        # Should have positive latency
        assert metrics.get_latency_ms() > 0

    def test_throughput_calculation(self):
        """Throughput should be bytes per second."""
        metrics = StreamMetrics(session_id="test", request_id="req-123")

        # No data yet
        assert metrics.get_throughput_bps() == 0.0

        # Record chunks
        metrics.record_chunk(1000)
        metrics.record_chunk(1000)

        # Should have positive throughput
        assert metrics.get_throughput_bps() > 0

    def test_to_dict(self):
        """Should serialize to dictionary."""
        metrics = StreamMetrics(session_id="test", request_id="req-123")
        metrics.record_chunk(100)
        metrics.complete()

        data = metrics.to_dict()

        assert data["session_id"] == "test"
        assert data["request_id"] == "req-123"
        assert data["total_chunks"] == 1
        assert data["total_bytes"] == 100
        assert data["completed"] is True
        assert "timestamp" in data


class TestStreamingHealthTracker:
    """Tests for StreamingHealthTracker class."""

    def test_no_degradation_initially(self):
        """Should not degrade initially."""
        tracker = StreamingHealthTracker(failure_threshold=3)
        assert not tracker.should_degrade()

    def test_degradation_after_threshold(self):
        """Should degrade after threshold failures."""
        tracker = StreamingHealthTracker(failure_threshold=3)

        tracker.record_failure()
        tracker.record_failure()
        assert not tracker.should_degrade()

        tracker.record_failure()
        assert tracker.should_degrade()

    def test_success_resets_failures(self):
        """Success should reset failure count."""
        tracker = StreamingHealthTracker(failure_threshold=3)

        tracker.record_failure()
        tracker.record_failure()
        tracker.record_success()

        assert not tracker.should_degrade()
        assert tracker.consecutive_failures == 0

    def test_reset(self):
        """Reset should clear all state."""
        tracker = StreamingHealthTracker(failure_threshold=3)

        tracker.record_failure()
        tracker.record_failure()
        tracker.reset()

        assert not tracker.should_degrade()
        assert tracker.consecutive_failures == 0


class TestSSEFormatters:
    """Tests for SSE formatting functions."""

    def test_format_heartbeat(self):
        """Heartbeat should be SSE comment."""
        heartbeat = format_sse_heartbeat()
        assert heartbeat == ": heartbeat\n\n"

    def test_format_retry(self):
        """Retry should be retry directive."""
        retry = format_sse_retry(2000)
        assert retry == "retry: 2000\n\n"

    def test_format_event_with_name(self):
        """Event with name should include event line."""
        event = format_sse_event("meta", '{"sources": []}')
        assert event == 'event: meta\ndata: {"sources": []}\n\n'

    def test_format_event_without_name(self):
        """Event without name should only have data."""
        event = format_sse_event(None, '{"content": "hello"}')
        assert event == 'data: {"content": "hello"}\n\n'
