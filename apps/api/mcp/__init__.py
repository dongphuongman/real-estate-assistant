"""
MCP Connector Interface Package.

This package provides the standard connector interface for external tools
and data sources following the Model Context Protocol (MCP) pattern.

Usage:
    from mcp import MCPConnector, MCPConnectorConfig, MCPConnectorRegistry

    # Register a custom connector
    @register_mcp_connector
    class MyConnector(MCPConnector):
        name = "my_connector"
        ...

    # Get a connector instance
    connector = get_mcp_connector("my_connector")
    result = await connector.execute("query", {"param": "value"})

Community Edition Notes:
    - Only allowlisted connectors are available
    - Data minimization is enabled by default
    - No PII egress without explicit consent
"""

from mcp.allowlist_validator import (
    AllowlistConfig,
    AllowlistEntry,
    AllowlistValidator,
    get_allowlist_validator,
    reset_allowlist_validator,
)
from mcp.base import MCPConnector
from mcp.config import (
    ConnectionPoolConfig,
    MCPConnectorConfig,
    MCPEdition,
)
from mcp.exceptions import (
    MCPAuthenticationError,
    MCPConfigError,
    MCPConnectionError,
    MCPConnectionPoolExhaustedError,
    MCPConnectorNotFoundError,
    MCPError,
    MCPNotAllowlistedError,
    MCPOperationError,
    MCPTimeoutError,
)
from mcp.rate_limiter import (
    MCPConnectorRateLimiter,
    RateLimitConfig,
    get_connector_rate_limiter,
    reset_rate_limiter,
)
from mcp.registry import (
    MCPConnectorRegistry,
    get_mcp_connector,
    register_mcp_connector,
)
from mcp.result import MCPConnectorResult
from mcp.stubs import EchoStubConnector

__all__ = [
    # Base classes
    "MCPConnector",
    # Configuration
    "MCPConnectorConfig",
    "ConnectionPoolConfig",
    "MCPEdition",
    # Results
    "MCPConnectorResult",
    # Registry
    "MCPConnectorRegistry",
    "register_mcp_connector",
    "get_mcp_connector",
    # Allowlist (Task #68)
    "AllowlistValidator",
    "AllowlistConfig",
    "AllowlistEntry",
    "get_allowlist_validator",
    "reset_allowlist_validator",
    # Exceptions
    "MCPError",
    "MCPConnectionError",
    "MCPTimeoutError",
    "MCPAuthenticationError",
    "MCPNotAllowlistedError",
    "MCPConnectorNotFoundError",
    "MCPConfigError",
    "MCPOperationError",
    "MCPConnectionPoolExhaustedError",
    # Stubs
    "EchoStubConnector",
    # Rate Limiter (Task #68)
    "MCPConnectorRateLimiter",
    "RateLimitConfig",
    "get_connector_rate_limiter",
    "reset_rate_limiter",
]
