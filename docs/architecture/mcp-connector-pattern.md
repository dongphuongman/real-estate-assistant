# MCP Connector Implementation Pattern

This document describes how to create custom MCP (Model Context Protocol) connectors for the AI Real Estate Assistant.

## Overview

The MCP connector system provides a standardized interface for integrating external tools and data sources. All connectors follow a consistent pattern with:

- **Generic typing** for type-safe response handling
- **Lifecycle management** (connect, disconnect, health check)
- **Automatic audit logging** with PII protection
- **Edition-based access control** (Community, Pro, Enterprise)
- **Rate limiting** and **retry logic** support

## Architecture

```
Request
    ↓
MCPConnectorRegistry
    ↓
┌────────────────────────────────────┐
│  MCPConnector[T]                   │
│  ├── connect()                     │
│  ├── disconnect()                  │
│  ├── health_check()                │
│  └── execute(operation, params)    │
└────────────────────────────────────┘
    ↓
MCPConnectorResult[T]
    ↓
Audit Logger (with PII redaction)
```

## Creating a Custom Connector

### 1. Create the Connector Class

```python
from typing import Any, Dict, Optional
from mcp.base import MCPConnector
from mcp.config import MCPConnectorConfig, MCPEdition
from mcp.exceptions import MCPConnectionError, MCPOperationError, MCPTimeoutError
from mcp.rate_limiter import get_connector_rate_limiter
from mcp.result import MCPConnectorResult
from mcp.registry import register_mcp_connector
import httpx
import os


@register_mcp_connector
class MyCustomConnector(MCPConnector[Dict[str, Any]]):
    """
    MCP connector for custom external service.

    This connector provides integration with [describe service].

    Operations:
        - fetch: Retrieve data from the service
        - submit: Submit data to the service
        - health_check: Check connector health

    Attributes:
        name: "my_custom" (unique identifier)
        display_name: "My Custom Connector" (for UI)
        description: Brief description of functionality
        requires_api_key: Whether API key is required
        allowlisted: Available in Community Edition
        min_edition: Minimum edition required
        supports_streaming: Whether streaming is supported
    """

    # Required: unique identifier
    name = "my_custom"

    # Optional: display name for UI
    display_name = "My Custom Connector"

    # Optional: description
    description = "Integration with custom external service"

    # Required: whether API key is needed
    requires_api_key = True
    api_key_env_var = "MY_CUSTOM_API_KEY"

    # Optional: edition availability
    allowlisted = True  # Available in Community Edition
    min_edition = MCPEdition.COMMUNITY

    # Optional: capabilities
    supports_streaming = False
    default_timeout = 30.0

    def __init__(
        self,
        config: Optional[MCPConnectorConfig] = None,
    ) -> None:
        """
        Initialize the connector.

        Args:
            config: Base MCP connector configuration
        """
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None

        # Configure rate limiter
        rate_limiter = get_connector_rate_limiter()
        rate_limiter.configure_connector(
            self.name,
            requests_per_minute=30,
            burst_size=5,
            enabled=True,
        )

    async def connect(self) -> bool:
        """
        Initialize the HTTP client.

        Returns:
            True if connection successful

        Raises:
            MCPConnectionError: If client initialization fails
        """
        if self._connected:
            return True

        try:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.default_timeout),
                headers={
                    "Authorization": f"Bearer {self._config.api_key}",
                    "User-Agent": "MCP-MyCustom/1.0",
                },
            )
            self._connected = True
            return True
        except Exception as e:
            raise MCPConnectionError(
                f"Failed to initialize client: {e}",
                connector_name=self.name,
            ) from None

    async def disconnect(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False

    async def health_check(self) -> MCPConnectorResult[Dict[str, Any]]:
        """
        Check health status of the connector.

        Returns:
            MCPConnectorResult with health information
        """
        return MCPConnectorResult.success_result(
            data={
                "healthy": self._connected,
                "connected": self._connected,
                "api_key_configured": bool(self._config.api_key),
            },
            connector_name=self.name,
            operation="health_check",
        )

    async def execute(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MCPConnectorResult[Dict[str, Any]]:
        """
        Execute an operation on the external service.

        Args:
            operation: Operation name (fetch, submit)
            params: Operation parameters
            **kwargs: Additional options

        Returns:
            MCPConnectorResult with operation result
        """
        params = params or {}

        # Check rate limit
        rate_limiter = get_connector_rate_limiter()
        allowed, rate_headers = await rate_limiter.check_rate_limit(self.name)

        if not allowed:
            return MCPConnectorResult.error_result(
                errors=["Rate limit exceeded. Please retry later."],
                connector_name=self.name,
                operation=operation,
                metadata={"rate_limit_headers": rate_headers},
            )

        # Route to operation handler
        try:
            if operation == "fetch":
                return await self._fetch(params)
            elif operation == "submit":
                return await self._submit(params)
            else:
                return MCPConnectorResult.error_result(
                    errors=[f"Unknown operation: {operation}"],
                    connector_name=self.name,
                    operation=operation,
                )
        except MCPTimeoutError as e:
            return MCPConnectorResult.error_result(
                errors=[str(e)],
                connector_name=self.name,
                operation=operation,
                metadata={"error_type": "timeout"},
            )
        except MCPOperationError as e:
            return MCPConnectorResult.error_result(
                errors=[str(e)],
                connector_name=self.name,
                operation=operation,
                metadata={"error_type": "operation_error"},
            )
        except Exception as e:
            return MCPConnectorResult.error_result(
                errors=[f"Internal error: {e}"],
                connector_name=self.name,
                operation=operation,
                metadata={"error_type": "internal"},
            )

    async def _fetch(self, params: Dict[str, Any]) -> MCPConnectorResult[Dict[str, Any]]:
        """Fetch data from the service."""
        # Implementation details...
        return MCPConnectorResult.success_result(
            data={"result": "data"},
            connector_name=self.name,
            operation="fetch",
        )

    async def _submit(self, params: Dict[str, Any]) -> MCPConnectorResult[Dict[str, Any]]:
        """Submit data to the service."""
        # Implementation details...
        return MCPConnectorResult.success_result(
            data={"status": "accepted"},
            connector_name=self.name,
            operation="submit",
        )
```

### 2. Register the Connector

Connectors are automatically registered when using the `@register_mcp_connector` decorator. The module must be imported at startup.

Add to `apps/api/mcp/connectors/__init__.py`:

```python
from mcp.connectors.my_custom import MyCustomConnector

__all__ = [
    "WebScraperConnector",
    "MyCustomConnector",
]
```

### 3. Configure (Optional)

Add configuration to `apps/api/config/settings.py`:

```python
my_custom_api_key: Optional[str] = Field(
    default_factory=lambda: os.getenv("MY_CUSTOM_API_KEY"),
    description="API key for custom connector",
)
```

## Required Class Attributes

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | str | Yes | Unique identifier (snake_case) |
| `display_name` | str | No | Human-readable name for UI |
| `description` | str | No | Brief description |
| `requires_api_key` | bool | No | Default: `True` |
| `api_key_env_var` | str | No | Env var name for API key |
| `allowlisted` | bool | No | Available in Community Edition |
| `min_edition` | MCPEdition | No | Default: `MCPEdition.PRO` |
| `supports_streaming` | bool | No | Default: `False` |
| `default_timeout` | float | No | Default: `30.0` |

## Required Methods

### `async def connect(self) -> bool`

Initialize connections, HTTP clients, or other resources.

```python
async def connect(self) -> bool:
    if self._connected:
        return True

    # Initialize resources
    self._client = httpx.AsyncClient(...)

    self._connected = True
    return True
```

### `async def disconnect(self) -> None`

Clean up resources gracefully.

```python
async def disconnect(self) -> None:
    if self._client:
        await self._client.aclose()
        self._client = None
    self._connected = False
```

### `async def health_check(self) -> MCPConnectorResult[Dict[str, Any]]`

Return health status information.

```python
async def health_check(self) -> MCPConnectorResult[Dict[str, Any]]:
    return MCPConnectorResult.success_result(
        data={
            "healthy": self._connected,
            "connected": self._connected,
            # Additional metrics...
        },
        connector_name=self.name,
        operation="health_check",
    )
```

### `async def execute(self, operation: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> MCPConnectorResult[T]`

Execute an operation with the given parameters.

```python
async def execute(
    self,
    operation: str,
    params: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> MCPConnectorResult[Dict[str, Any]]:
    params = params or {}

    # Rate limit check
    rate_limiter = get_connector_rate_limiter()
    allowed, rate_headers = await rate_limiter.check_rate_limit(self.name)
    if not allowed:
        return MCPConnectorResult.error_result(...)

    # Route to operation handler
    try:
        if operation == "my_operation":
            return await self._my_operation(params)
        else:
            return MCPConnectorResult.error_result(
                errors=[f"Unknown operation: {operation}"],
                connector_name=self.name,
                operation=operation,
            )
    except Exception as e:
        return MCPConnectorResult.error_result(...)
```

## Result Handling

### Success Result

```python
MCPConnectorResult.success_result(
    data={"key": "value"},
    connector_name=self.name,
    operation="fetch",
    metadata={"cached": False},
)
```

### Error Result

```python
MCPConnectorResult.error_result(
    errors=["Error message"],
    connector_name=self.name,
    operation="fetch",
    metadata={"error_type": "timeout"},
)
```

## Rate Limiting

Configure rate limiting in the connector constructor:

```python
from mcp.rate_limiter import get_connector_rate_limiter

def __init__(self, config=None):
    super().__init__(config)

    rate_limiter = get_connector_rate_limiter()
    rate_limiter.configure_connector(
        self.name,
        requests_per_minute=30,
        burst_size=5,
        enabled=True,
    )
```

Check rate limit before operations:

```python
async def execute(self, operation, params=None, **kwargs):
    rate_limiter = get_connector_rate_limiter()
    allowed, rate_headers = await rate_limiter.check_rate_limit(self.name)

    if not allowed:
        return MCPConnectorResult.error_result(
            errors=["Rate limit exceeded"],
            connector_name=self.name,
            operation=operation,
            metadata={"rate_limit_headers": rate_headers},
        )

    # Continue with operation...
```

## Retry Logic

Implement exponential backoff for transient failures:

```python
import asyncio

async def _fetch_with_retry(self, url: str) -> str:
    max_retries = 3
    base_delay = 1.0

    for attempt in range(max_retries):
        try:
            response = await self._client.get(url)

            if response.status_code == 200:
                return response.text
            elif response.status_code == 429:
                # Rate limited - wait and retry
                retry_after = float(response.headers.get("Retry-After", base_delay * (2 ** attempt)))
                await asyncio.sleep(retry_after)
            elif response.status_code >= 500:
                # Server error - retry with backoff
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
            elif response.status_code in (403, 404):
                # Client errors - don't retry
                raise MCPOperationError(f"HTTP {response.status_code}: {url}", connector_name=self.name)
            else:
                raise MCPOperationError(f"HTTP {response.status_code}: {url}", connector_name=self.name)

        except httpx.TimeoutException:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
            else:
                raise MCPTimeoutError(f"Request timed out: {url}", connector_name=self.name)

    raise MCPOperationError(f"Max retries exceeded: {url}", connector_name=self.name)
```

## Edition Access Control

Control connector availability by edition:

```python
# Available in Community Edition
allowlisted = True
min_edition = MCPEdition.COMMUNITY

# Only in Pro and Enterprise
allowlisted = False
min_edition = MCPEdition.PRO

# Enterprise only
allowlisted = False
min_edition = MCPEdition.ENTERPRISE
```

## Testing

### Unit Tests with Stubs

Use stubs for deterministic unit tests:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from mcp.connectors.my_custom import MyCustomConnector
from mcp.result import MCPConnectorResult

@pytest.mark.asyncio
async def test_fetch_operation():
    connector = MyCustomConnector()
    await connector.connect()

    # Mock the client response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "test"}
    connector._client.get = AsyncMock(return_value=mock_response)

    result = await connector.execute("fetch", {"id": "123"})

    assert result.success is True
    assert result.data["data"] == "test"

    await connector.disconnect()
```

### Integration Tests

Test with real services (marked as integration):

```python
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_service():
    async with MyCustomConnector() as connector:
        result = await connector.execute("fetch", {"id": "real_id"})
        assert result.success is True
```

## Using Connectors

### Direct Usage

```python
from mcp import get_mcp_connector

# Get connector instance
connector = get_mcp_connector("web_scraper")
await connector.connect()

# Execute operation
result = await connector.execute("scrape", {
    "url": "https://example.com",
    "selectors": {"title": "h1"},
})

if result.success:
    print(result.data["title"])

await connector.disconnect()
```

### Context Manager

```python
from mcp import get_mcp_connector

async with get_mcp_connector("web_scraper") as connector:
    result = await connector.execute("scrape", {"url": "https://example.com"})
    if result.success:
        print(result.data)
```

### With HybridAgent

Connectors can be wrapped as LangChain tools:

```python
from langchain.tools import Tool
from mcp import get_mcp_connector

def scrape_properties(url: str) -> str:
    """Scrape property listings from a URL."""
    async def _scrape():
        async with get_mcp_connector("web_scraper") as connector:
            result = await connector.execute("scrape", {
                "url": url,
                "selectors": {
                    "title": "h1.property-title",
                    "price": ".price",
                    "location": ".location",
                },
            })
            return result.data if result.success else None

    import asyncio
    return asyncio.run(_scrape())

# Register as tool
scraper_tool = Tool(
    name="property_scraper",
    func=scrape_properties,
    description="Scrape property listings from real estate websites",
)
```

## Best Practices

1. **Graceful Degradation**: Always handle errors gracefully and return meaningful error messages
2. **Rate Limiting**: Respect external API rate limits
3. **Timeouts**: Set reasonable timeouts to avoid blocking
4. **Caching**: Cache responses when appropriate
5. **Logging**: Log errors and important events for debugging
6. **Health Checks**: Implement meaningful health checks
7. **Testing**: Write comprehensive unit tests with stubs
8. **Documentation**: Document all operations and parameters

## Example: WebScraperConnector

See `apps/api/mcp/connectors/web_scraper.py` for a complete reference implementation with:

- Configurable scraping targets
- CSS selector-based extraction
- Rate limiting
- Exponential backoff retry
- Response caching
- Domain allowlisting
- Batch scraping support
