# ADR-0008: Streaming Error Handling Patterns

## Status

**Proposed** (2025-03-21)

## Context

The AI Real Estate Assistant uses Server-Sent Events (SSE) for real-time streaming of chat responses and anomaly notifications. The existing implementation lacked resilience features needed for production reliability:

- No automatic reconnection with backoff
- No connection health monitoring
- No recovery from interrupted streams
- Limited error visibility

This ADR documents the error handling patterns implemented to address these gaps (Task #74).

## Decision

We implement a comprehensive streaming error handling system with the following components:

### 1. Exponential Backoff for Reconnection

**Backend** (`apps/api/utils/streaming.py`):
```python
def calculate_backoff(attempt: int, config: ReconnectionConfig) -> int:
    base_delay = config.initial_delay_ms * (config.backoff_multiplier ** attempt)
    capped_delay = min(base_delay, config.max_delay_ms)
    jitter = capped_delay * config.jitter_factor * random.random()
    return int(capped_delay + jitter)
```

**Configuration**:
- Initial delay: 1000ms (1 second)
- Max delay: 30000ms (30 seconds)
- Backoff multiplier: 2.0 (exponential)
- Jitter factor: 0.1 (10% randomization to avoid thundering herd)

**Frontend** (`apps/web/src/lib/streaming/ReconnectingEventSource.ts`):
```typescript
const delay = Math.min(
  this.options.initialDelay * Math.pow(this.options.backoffMultiplier, attempt),
  this.options.maxDelay
)
```

### 2. Heartbeat Mechanism

**Backend** sends SSE comments as keep-alive signals:
```python
def format_sse_heartbeat() -> str:
    return ": heartbeat\n\n"
```

Heartbeats are injected during streaming when no data has been sent for `stream_heartbeat_interval_seconds` (default: 15s).

**Frontend** monitors connection health:
```typescript
class HeartbeatMonitor {
  check(): boolean  // Returns true if connection is stalled
  handleHeartbeat(): void  // Called when heartbeat comment received
}
```

### 3. Stream Buffer for Recovery

**Frontend** buffers chunks for interrupted stream recovery:
```typescript
class StreamBuffer {
  add(content: string, sequence: number): number
  getBufferedContent(): string
  persist(): void  // Save to sessionStorage
  restore(): boolean  // Restore from sessionStorage
}
```

Buffer is persisted to `sessionStorage` on error and restored on page reload.

### 4. Graceful Degradation

**Backend** tracks streaming health:
```python
class StreamingHealthTracker:
    def record_success(self): ...
    def record_failure(self): ...
    def should_degrade(self) -> bool: ...
```

After `stream_degradation_threshold` (default: 3) consecutive failures, the system can fall back to non-streaming mode.

### 5. Streaming Metrics

**Backend** collects metrics per stream:
```python
class StreamMetrics:
    latency_ms: float  # Time to first chunk
    duration_ms: float  # Total stream duration
    throughput_bps: float  # Bytes per second
    total_chunks: int
    total_bytes: int
    error_count: int
```

Metrics are emitted as SSE `event: metrics` at stream end.

## Error Types

| Error Type | HTTP Status | Recovery Strategy |
|------------|-------------|-------------------|
| Network | 0 | Exponential backoff reconnect |
| Timeout | 408, 504 | Retry with backoff |
| Rate Limit | 429 | Respect `Retry-After` header |
| Server | 502, 503 | Exponential backoff |
| Auth | 401, 403 | No retry (requires re-auth) |
| Validation | 400, 422 | No retry (client error) |

## API Contract

### New SSE Events

```
: heartbeat\n\n                    # Keep-alive comment
event: metrics\ndata: {...}\n\n    # Metrics at stream end
retry: 2000\n\n                    # Reconnection delay hint
```

### New Response Headers

```
X-Heartbeat-Interval: 15
X-Stream-Timeout: 300
```

### New Request Parameters

```typescript
interface ChatRequest {
  // ... existing fields
  include_metrics?: boolean;  // Request metrics in response
}
```

## Configuration

### Backend Environment Variables

```bash
STREAM_HEARTBEAT_INTERVAL_SECONDS=15
STREAM_TIMEOUT_SECONDS=300
STREAM_BACKOFF_INITIAL_MS=1000
STREAM_BACKOFF_MAX_MS=30000
STREAM_METRICS_ENABLED=true
STREAM_DEGRADATION_THRESHOLD=3
```

### Frontend Options

```typescript
streamChatMessage(request, onChunk, onStart, onMeta, {
  enableHeartbeat: true,
  heartbeatTimeoutSeconds: 45,
  enableBuffer: false,
  bufferSessionId: 'optional-session-id'
})
```

## Consequences

### Positive

- **Resilience**: Automatic recovery from transient network failures
- **Observability**: Metrics provide visibility into streaming performance
- **User Experience**: Buffer recovery prevents lost work on interruption
- **Backward Compatible**: All changes are additive, existing clients continue working

### Negative

- **Complexity**: Additional state management for buffers and health tracking
- **Memory**: Buffer stores up to 1000 chunks in memory
- **Storage**: Session persistence uses `sessionStorage`

### Neutral

- **Jitter**: Random delay variation may cause slightly unpredictable reconnection times
- **Heartbeat Overhead**: Minimal network overhead (~15 bytes per heartbeat)

## Migration Path

1. **Phase 1**: Backend utilities deployed (non-breaking)
2. **Phase 2**: Frontend utilities integrated
3. **Phase 3**: Buffer recovery UI added
4. **Phase 4**: Metrics dashboard created

All phases are backward compatible. Clients can ignore new events and headers.

## Testing

### Backend Tests
- `apps/api/tests/unit/utils/test_streaming.py`
- `apps/api/tests/integration/api/test_api_chat_sse.py`

### Frontend Tests
- `apps/web/src/lib/streaming/__tests__/HeartbeatMonitor.test.ts`
- `apps/web/src/lib/streaming/__tests__/StreamBuffer.test.ts`
- `apps/web/src/lib/streaming/__tests__/ReconnectingEventSource.test.ts`

## References

- [Server-Sent Events Specification](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [Exponential Backoff Algorithm](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
- Task #74: Response Streaming Improvements
