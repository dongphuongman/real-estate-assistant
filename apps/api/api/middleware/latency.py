"""
P95 latency monitoring middleware for search and chat endpoints (Task #120).

Tracks request durations per endpoint-group in a sliding window and computes
real-time p95 values.  SLA targets:
  - search (retrieval): p95 < 2000 ms
  - chat   (complex):   p95 < 8000 ms

The middleware stores latency data on ``app.state.latency_tracker`` so it can
be read by the admin metrics endpoint without any external dependency.
"""

from __future__ import annotations

import logging
import math
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Any

from fastapi import FastAPI, Request

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SLA_TARGETS: dict[str, float] = {
    "search": 2_000.0,  # ms
    "chat": 8_000.0,  # ms
}

# Map URL path prefixes to endpoint groups.
_ENDPOINT_GROUPS: list[tuple[str, str]] = [
    ("/api/v1/search", "search"),
    ("/api/v1/chat", "chat"),
    ("/api/v1/rag", "search"),  # RAG is retrieval-class
]


def _classify_endpoint(path: str) -> str | None:
    """Return the endpoint group for *path*, or ``None`` if not tracked."""
    for prefix, group in _ENDPOINT_GROUPS:
        if path.startswith(prefix):
            return group
    return None


# ---------------------------------------------------------------------------
# Latency tracker (thread-safe, sliding-window percentile calculator)
# ---------------------------------------------------------------------------


class LatencyTracker:
    """Thread-safe sliding-window p95 latency tracker."""

    def __init__(
        self,
        window_seconds: float = 300.0,
        max_samples: int = 10_000,
    ) -> None:
        self._window_seconds = window_seconds
        self._max_samples = max_samples
        self._lock = Lock()
        # group -> deque of (timestamp, duration_ms)
        self._samples: dict[str, deque[tuple[float, float]]] = defaultdict(deque)
        # Alert state: group -> last alert epoch seconds (cooldown)
        self._last_alert: dict[str, float] = {}

    # -- public API ----------------------------------------------------------

    def record(self, group: str, duration_ms: float) -> None:
        """Record a latency sample for *group*."""
        now = time.time()
        with self._lock:
            q = self._samples[group]
            q.append((now, duration_ms))
            # Evict old entries
            cutoff = now - self._window_seconds
            while q and q[0][0] < cutoff:
                q.popleft()
            # Hard cap to prevent unbounded growth
            while len(q) > self._max_samples:
                q.popleft()

    def get_p95(self, group: str) -> float | None:
        """Return p95 latency in ms for *group*, or ``None`` if no samples."""
        with self._lock:
            now = time.time()
            cutoff = now - self._window_seconds
            q = self._samples.get(group)
            if not q:
                return None
            # Filter out-of-window
            durations = [d for ts, d in q if ts >= cutoff]
            if not durations:
                return None
            durations.sort()
            idx = int(math.ceil(0.95 * len(durations))) - 1
            idx = max(0, min(idx, len(durations) - 1))
            return durations[idx]

    def get_stats(self) -> dict[str, Any]:
        """Return full latency report for all tracked groups."""
        result: dict[str, Any] = {"sla_targets": SLA_TARGETS, "endpoints": {}}
        for group in SLA_TARGETS:
            with self._lock:
                now = time.time()
                cutoff = now - self._window_seconds
                q = self._samples.get(group)
                durations = [d for ts, d in q if ts >= cutoff] if q else []
                sample_count = len(durations)

            p95 = None
            if durations:
                durations_sorted = sorted(durations)
                idx = int(math.ceil(0.95 * len(durations_sorted))) - 1
                idx = max(0, min(idx, len(durations_sorted) - 1))
                p95 = durations_sorted[idx]

            sla_target = SLA_TARGETS[group]
            sla_breached = p95 is not None and p95 > sla_target

            result["endpoints"][group] = {
                "p95_ms": round(p95, 2) if p95 is not None else None,
                "sla_target_ms": sla_target,
                "sla_breached": sla_breached,
                "sample_count": sample_count,
                "window_seconds": self._window_seconds,
            }
        return result


# ---------------------------------------------------------------------------
# Middleware registration helper
# ---------------------------------------------------------------------------


def add_latency_middleware(app: FastAPI) -> None:
    """Register the p95 latency tracking middleware on *app*."""

    tracker = LatencyTracker()
    app.state.latency_tracker = tracker  # type: ignore[attr-defined]

    @app.middleware("http")
    async def _latency_middleware(request: Request, call_next):
        group = _classify_endpoint(request.url.path)
        if group is None:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1_000.0

        tracker.record(group, duration_ms)

        # Check SLA breach for proactive alerting
        sla_target = SLA_TARGETS.get(group)
        if sla_target and duration_ms > sla_target:
            # Cooldown: log at most once per 60 seconds per group
            now = time.time()
            last = tracker._last_alert.get(group, 0)
            if now - last > 60:
                tracker._last_alert[group] = now
                logger.warning(
                    "sla_breach",
                    extra={
                        "event": "sla_breach",
                        "endpoint_group": group,
                        "duration_ms": round(duration_ms, 2),
                        "sla_target_ms": sla_target,
                        "path": request.url.path,
                        "method": request.method,
                    },
                )

        return response
