"""
MCP Context Management for request correlation (Task #69).

This module provides context management for propagating request IDs
across MCP connector calls using contextvars. This enables:

1. Request correlation across async boundaries
2. Audit log tracing from API request to connector response
3. Distributed tracing support

The request ID flows from:
- FastAPI middleware (observability.py) -> request.state.request_id
- MCP context (this module) -> ContextVar
- MCP audit logger -> correlation in logs
"""

import uuid
from contextvars import ContextVar
from typing import Optional

# Context variable for request ID propagation
# This is async-safe and works across coroutine boundaries
_request_id_ctx: ContextVar[Optional[str]] = ContextVar("mcp_request_id", default=None)

# Context variable for client ID propagation
_client_id_ctx: ContextVar[Optional[str]] = ContextVar("mcp_client_id", default=None)


def set_request_id(request_id: Optional[str]) -> None:
    """
    Set the request ID in the current context.

    This should be called at the start of request processing
    (typically in middleware or before connector calls).

    Args:
        request_id: The request ID to set (or None to clear)
    """
    _request_id_ctx.set(request_id)


def get_request_id() -> Optional[str]:
    """
    Get the request ID from the current context.

    Returns:
        The current request ID or None if not set
    """
    return _request_id_ctx.get()


def generate_request_id() -> str:
    """
    Generate a new unique request ID.

    Returns:
        A UUID-based request ID
    """
    return uuid.uuid4().hex


def set_client_id(client_id: Optional[str]) -> None:
    """
    Set the client ID in the current context.

    Args:
        client_id: The client ID to set (or None to clear)
    """
    _client_id_ctx.set(client_id)


def get_client_id() -> Optional[str]:
    """
    Get the client ID from the current context.

    Returns:
        The current client ID or None if not set
    """
    return _client_id_ctx.get()


class MCPRequestContext:
    """
    Context manager for MCP request correlation.

    Usage:
        async with MCPRequestContext(request_id="abc123"):
            # All connector calls within this block will be correlated
            result = await connector.execute("search", params)

    Or with FastAPI request:
        async with MCPRequestContext.from_request(request):
            result = await connector.execute("search", params)
    """

    def __init__(
        self,
        request_id: Optional[str] = None,
        client_id: Optional[str] = None,
    ) -> None:
        """
        Initialize context with request ID.

        Args:
            request_id: Optional request ID (generated if not provided)
            client_id: Optional client ID
        """
        self._request_id = request_id or generate_request_id()
        self._client_id = client_id
        self._token_request_id = None
        self._token_client_id = None

    @classmethod
    def from_request(cls, request: any) -> "MCPRequestContext":
        """
        Create context from FastAPI request object.

        Args:
            request: FastAPI Request object

        Returns:
            MCPRequestContext with request ID from request.state
        """
        request_id = getattr(request.state, "request_id", None)
        client_id = getattr(request.state, "client_id", None)
        return cls(request_id=request_id, client_id=client_id)

    def __enter__(self) -> "MCPRequestContext":
        """Enter context and set request ID."""
        self._token_request_id = _request_id_ctx.set(self._request_id)
        if self._client_id is not None:
            self._token_client_id = _client_id_ctx.set(self._client_id)
        return self

    def __exit__(self, exc_type: any, exc_val: any, exc_tb: any) -> None:
        """Exit context and reset request ID."""
        if self._token_request_id is not None:
            _request_id_ctx.reset(self._token_request_id)
        if self._token_client_id is not None:
            _client_id_ctx.reset(self._token_client_id)

    @property
    def request_id(self) -> str:
        """Get the request ID for this context."""
        return self._request_id

    @property
    def client_id(self) -> Optional[str]:
        """Get the client ID for this context."""
        return self._client_id


async def with_request_context(
    request_id: Optional[str] = None,
    client_id: Optional[str] = None,
):
    """
    Async context manager for MCP request correlation.

    Usage:
        async with with_request_context("abc123") as ctx:
            result = await connector.execute("search", params)
            print(f"Request ID: {ctx.request_id}")

    Args:
        request_id: Optional request ID (generated if not provided)
        client_id: Optional client ID

    Yields:
        MCPRequestContext instance
    """
    ctx = MCPRequestContext(request_id=request_id, client_id=client_id)
    with ctx:
        yield ctx


def get_context_metadata() -> dict[str, Optional[str]]:
    """
    Get all context metadata as a dictionary.

    Useful for logging and debugging.

    Returns:
        Dictionary with request_id and client_id
    """
    return {
        "request_id": get_request_id(),
        "client_id": get_client_id(),
    }
