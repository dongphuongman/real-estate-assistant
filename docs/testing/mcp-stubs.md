# MCP Stub Testing Framework

This document describes how to use MCP stubs for deterministic unit testing without network access.

## Overview

The MCP Stub Testing Framework provides tools for testing MCP connectors without relying on external services. This ensures:

- **Deterministic tests**: No flaky tests due to network issues
- **Fast execution**: No network latency
- **Isolation**: Tests don't depend on external state
- **Reproducibility**: Same input always produces same output

## Quick Start

### Using EchoStubConnector

The simplest stub for testing:

```python
import pytest
from mcp.stubs import EchoStubConnector

@pytest.mark.asyncio
async def test_with_echo_stub():
    stub = EchoStubConnector()
    await stub.connect()

    result = await stub.execute("search", {"query": "test"})

    assert result.success
    assert result.data["operation"] == "search"
    assert result.data["params"]["query"] == "test"
```

### Using PropertyListingStub

For property data testing:

```python
import pytest
from data.schemas import Property, PropertyType
from mcp.stubs import PropertyListingStub

@pytest.mark.asyncio
async def test_property_search():
    properties = [
        Property(id="1", city="Krakow", rooms=2, price=1000),
        Property(id="2", city="Warsaw", rooms=3, price=1500),
    ]
    stub = PropertyListingStub(properties=properties)

    # Search by city
    result = await stub.execute("search", {"city": "Krakow"})

    assert result.success
    assert result.data.total_count == 1
    assert result.data.properties[0].city == "Krakow"
```

### Using NetworkGuard

Ensure no network calls:

```python
import pytest
from mcp.testing import NetworkGuard

def test_isolated():
    with NetworkGuard.enabled():
        # Any network call raises NetworkIsolationError
        # Your code here is guaranteed to be network-free
        pass
```

## Available Stubs

### EchoStubConnector

Echoes back the operation and parameters. Useful for testing connector interfaces.

```python
from mcp.stubs import EchoStubConnector

stub = EchoStubConnector(
    latency_ms=100,     # Simulate network latency
    fail_next=True,     # Fail on next call
)
```

**Operations:**
- Any operation echoes back the input

### PropertyListingStub

Provides configurable property data.

```python
from mcp.stubs import PropertyListingStub

stub = PropertyListingStub(properties=[...])
```

**Operations:**
- `get_all` - Return all properties
- `get_by_id` - Get property by ID (params: `id`)
- `search` - Filter by criteria (params: `city`, `min_price`, `max_price`, `min_rooms`, `max_rooms`, `property_type`, `has_parking`, `has_garden`, `has_elevator`)
- `count` - Return property count

### PropertySearchStub

Simulates search operations.

```python
from mcp.stubs import PropertySearchStub, SearchResult

stub = PropertySearchStub()

# Configure custom handler
def search_handler(query: str) -> SearchResult:
    return SearchResult(
        query=query,
        properties=[{"id": "1", "score": 0.95}],
        total=1,
    )

stub.set_search_handler(search_handler)
```

**Operations:**
- `search` - Execute search (params: `query`, `page`, `page_size`)
- `suggest` - Get suggestions (params: `prefix`)
- `facets` - Get available facets

## StubRegistry

Manage multiple stubs in tests:

```python
from mcp.testing import StubRegistry
from mcp.stubs import EchoStubConnector, PropertyListingStub

registry = StubRegistry()

# Register stubs
echo = registry.register(EchoStubConnector)
props = registry.register(PropertyListingStub, properties=[...])

# Use stubs
stub = registry.get("echo_stub")

# Verify no network calls
registry.verify_no_network_calls()

# Reset all stubs
registry.reset_all()
```

## Pytest Fixtures

Add to your `conftest.py`:

```python
# apps/api/tests/conftest.py

from mcp.testing.fixtures import *  # noqa: F401, F403
```

### Available Fixtures

| Fixture | Description |
|---------|-------------|
| `mcp_stub_registry` | Fresh StubRegistry for each test |
| `echo_stub` | EchoStubConnector instance |
| `network_isolated` | NetworkGuard context manager |
| `stub_property_responses` | Sample property response data |
| `stub_search_responses` | Sample search response data |

## Creating Custom Stubs

Extend `MCPStub` to create custom stubs:

```python
from mcp.stubs.base_stub import MCPStub
from mcp.result import MCPConnectorResult

class MyCustomStub(MCPStub[dict]):
    name = "my_custom_stub"
    display_name = "My Custom Stub"
    description = "Custom stub for testing"

    async def execute(self, operation, params=None, **kwargs):
        await self._simulate_latency()

        # Check for queued errors
        if self._error_queue:
            error = self._error_queue.popleft()
            return MCPConnectorResult.error_result(
                errors=[error],
                connector_name=self.name,
                operation=operation,
            )

        # Check for queued responses
        if self._response_queue:
            response = self._response_queue.popleft()
            return MCPConnectorResult.success_result(
                data=response,
                connector_name=self.name,
                operation=operation,
            )

        # Default behavior
        self._call_count += 1
        self._record_call(operation, params, kwargs)

        return MCPConnectorResult.success_result(
            data={"operation": operation, "params": params},
            connector_name=self.name,
            operation=operation,
        )
```

## Network Isolation

### Why Network Isolation?

Unit tests should be:
- **Fast**: No network latency
- **Deterministic**: Same result every time
- **Isolated**: No external dependencies
- **Reliable**: No flaky tests due to service outages

### Using NetworkGuard

```python
from mcp.testing import NetworkGuard, NetworkIsolationError

# As context manager
with NetworkGuard.enabled():
    # Network calls raise NetworkIsolationError
    await my_function()

# As decorator
from mcp.testing.network_guard import assert_no_network_calls

@assert_no_network_calls
def test_my_stub():
    # Network calls blocked here
    pass

# As pytest fixture
def test_with_fixture(network_isolated):
    # Network calls blocked here
    pass
```

### Marking Integration Tests

Integration tests that need network access should be marked:

```python
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_api_call():
    # This test can make network calls
    pass
```

Run only unit tests (excludes integration):

```bash
pytest -m "not integration"
```

## CI Integration

The CI pipeline includes network isolation verification:

```bash
# Run network isolation check
python scripts/ci/network_isolation_check.py

# With verbose output
python scripts/ci/network_isolation_check.py --verbose

# Specific test path
python scripts/ci/network_isolation_check.py --path tests/unit/mcp
```

### GitHub Actions

Network isolation is verified in `.github/workflows/ci.yml`:

```yaml
- name: Run unit tests with network isolation
  run: |
    python scripts/ci/network_isolation_check.py
```

## Best Practices

1. **Always use stubs for unit tests**: Never make real network calls
2. **Use queued responses**: Configure expected responses upfront
3. **Record calls**: Use `get_call_history()` to verify behavior
4. **Test edge cases**: Use `add_error()` to test error handling
5. **Simulate latency**: Use `latency_ms` to test timeout behavior
6. **Use StubRegistry**: For tests with multiple stubs

## Troubleshooting

### NetworkIsolationError in tests

If you see this error, your test is trying to make a network call:

```
NetworkIsolationError: Network call attempted during isolated test.
Use MCP stubs instead of real connectors.
```

**Solution**: Replace real connectors with stubs.

### Stub returns None

If queued responses are exhausted, stubs return default (None):

```python
stub = ConcreteStub(responses=[{"data": 1}])

result1 = await stub.execute("op", {})  # {"data": 1}
result2 = await stub.execute("op", {})  # None (default)
```

**Solution**: Add more responses or configure a default handler.

### Tests fail with latency

High latency settings can cause timeout failures:

```python
stub = ConcreteStub(latency_ms=5000)  # 5 seconds!
```

**Solution**: Use lower latency for tests (50-100ms).
