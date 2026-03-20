"""
MCPStub base class for deterministic testing.

This module provides the abstract base class for all MCP test stubs,
enabling configurable responses, call recording, and network isolation.
"""

import asyncio
from abc import abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, AsyncGenerator, Deque, Dict, Generic, List, Optional, TypeVar

from mcp.base import MCPConnector
from mcp.config import MCPConnectorConfig, MCPEdition
from mcp.result import MCPConnectorResult

T = TypeVar("T")


@dataclass
class StubCallRecord:
    """Record of a single call to a stub."""

    operation: str
    params: Optional[Dict[str, Any]]
    kwargs: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    result: Optional[MCPConnectorResult[Any]] = None
    error: Optional[str] = None


class MCPStub(MCPConnector[T], Generic[T]):
    """
    Abstract base class for MCP test stubs.

    Extends MCPConnector with testing-specific features:
    - Configurable response sequences
    - Call recording/replay
    - Latency simulation
    - Failure injection
    - Network isolation guarantee

    All stubs are safe for unit testing - they never make network calls.

    Attributes:
        responses: Queue of responses to return
        call_history: Record of all calls made
        network_isolated: Always True for stubs

    Example:
        class MyStub(MCPStub[Dict[str, Any]]):
            name = "my_stub"

            async def execute(self, operation, params, **kwargs):
                return self._get_next_response(operation)

        # Usage
        stub = MyStub(responses=[{"data": 1}, {"data": 2}])
        result1 = await stub.execute("query", {})  # {"data": 1}
        result2 = await stub.execute("query", {})  # {"data": 2}
    """

    name: str = ""  # Override in subclass
    display_name: str = ""  # Override in subclass
    description: str = "MCP test stub"
    requires_api_key: bool = False
    allowlisted: bool = True  # Stubs available in all editions
    min_edition: MCPEdition = MCPEdition.COMMUNITY
    supports_streaming: bool = True

    def __init__(
        self,
        config: Optional[MCPConnectorConfig] = None,
        responses: Optional[List[T]] = None,
        latency_ms: float = 0.0,
        fail_rate: float = 0.0,
        record_calls: bool = True,
    ) -> None:
        """
        Initialize the stub.

        Args:
            config: Optional configuration (stubs don't require API keys)
            responses: Initial list of responses to queue
            latency_ms: Simulated latency in milliseconds
            fail_rate: Probability of failure (0.0 to 1.0)
            record_calls: Whether to record call history
        """
        # Bypass parent validation for stubs
        self._config = config or self._create_default_config()
        self._connected = False
        self._connection_pool = None

        # Stub-specific state
        self._response_queue: Deque[T] = deque(responses or [])
        self._error_queue: Deque[str] = deque()
        self._latency_ms = latency_ms
        self._fail_rate = fail_rate
        self._record_calls = record_calls
        self._call_history: List[StubCallRecord] = []
        self._call_count = 0

    def _create_default_config(self) -> MCPConnectorConfig:
        """Create default configuration for stubs."""
        return MCPConnectorConfig(
            name=self.name,
            display_name=self.display_name,
            api_key_env_var="",
            timeout_seconds=30.0,
            allowlisted=True,
            min_edition=MCPEdition.COMMUNITY,
            supports_streaming=True,
        )

    async def connect(self) -> bool:
        """
        Simulate connection (always succeeds immediately).

        Returns:
            Always True for stubs
        """
        if self._latency_ms > 0:
            await asyncio.sleep(self._latency_ms / 1000)
        self._connected = True
        return True

    async def disconnect(self) -> None:
        """Simulate disconnection."""
        self._connected = False

    async def health_check(self) -> MCPConnectorResult[Dict[str, Any]]:
        """Return healthy status with stub statistics."""
        return MCPConnectorResult.success_result(
            data={
                "healthy": True,
                "connected": self._connected,
                "call_count": self._call_count,
                "response_queue_size": len(self._response_queue),
                "stub_type": self.__class__.__name__,
            },
            connector_name=self.name,
            operation="health_check",
        )

    @abstractmethod
    async def execute(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MCPConnectorResult[T]:
        """
        Execute an operation using stub data.

        Subclasses should call _record_call() and _simulate_latency(),
        then return appropriate stub data.

        Args:
            operation: Operation name to execute
            params: Parameters for the operation
            **kwargs: Additional options

        Returns:
            MCPConnectorResult with stub data
        """
        pass

    async def stream(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[T, None]:
        """
        Stream results from the stub.

        Default implementation yields the execute result as a single chunk.
        Subclasses can override for more realistic streaming behavior.

        Args:
            operation: Operation name to execute
            params: Parameters for the operation
            **kwargs: Additional options

        Yields:
            Chunks of the response
        """
        result = await self.execute(operation, params, **kwargs)
        if result.success and result.data is not None:
            yield result.data

    def add_response(self, response: T) -> None:
        """
        Add a response to the queue.

        Args:
            response: Response to add to queue
        """
        self._response_queue.append(response)

    def add_responses(self, responses: List[T]) -> None:
        """
        Add multiple responses to the queue.

        Args:
            responses: Responses to add to queue
        """
        self._response_queue.extend(responses)

    def add_error(self, error: str) -> None:
        """
        Add an error to the error queue.

        The next execute() will return this error instead of a response.

        Args:
            error: Error message to queue
        """
        self._error_queue.append(error)

    def _get_next_response(self, operation: str) -> MCPConnectorResult[T]:
        """
        Get the next response from the queue.

        Checks error queue first, then response queue.
        If both are empty, returns a default success result.

        Args:
            operation: Operation name for metadata

        Returns:
            MCPConnectorResult with queued response or error
        """
        self._call_count += 1

        # Check for queued errors first
        if self._error_queue:
            error = self._error_queue.popleft()
            return MCPConnectorResult.error_result(
                errors=[error],
                connector_name=self.name,
                operation=operation,
                metadata={"stub": True, "queued_error": True},
            )

        # Check for queued responses
        if self._response_queue:
            response = self._response_queue.popleft()
            return MCPConnectorResult.success_result(
                data=response,
                connector_name=self.name,
                operation=operation,
                metadata={"stub": True, "queued": True},
            )

        # No queued responses - return default
        return MCPConnectorResult.success_result(
            data=None,
            connector_name=self.name,
            operation=operation,
            metadata={"stub": True, "default": True},
        )

    def _should_fail(self) -> bool:
        """
        Determine if this call should simulate failure.

        Uses fail_rate probability.

        Returns:
            True if should fail, False otherwise
        """
        import random

        return random.random() < self._fail_rate

    async def _simulate_latency(self) -> None:
        """Simulate network latency if configured."""
        if self._latency_ms > 0:
            await asyncio.sleep(self._latency_ms / 1000)

    def _record_call(
        self,
        operation: str,
        params: Optional[Dict[str, Any]],
        kwargs: Dict[str, Any],
        result: Optional[MCPConnectorResult[T]] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Record a call for later verification.

        Args:
            operation: Operation name
            params: Call parameters
            kwargs: Additional keyword arguments
            result: Call result (if successful)
            error: Error message (if failed)
        """
        if self._record_calls:
            record = StubCallRecord(
                operation=operation,
                params=params,
                kwargs=kwargs,
                result=result,
                error=error,
            )
            self._call_history.append(record)

    def get_call_history(self) -> List[StubCallRecord]:
        """
        Get the list of all recorded calls.

        Returns:
            List of call records
        """
        return list(self._call_history)

    def get_last_call(self) -> Optional[StubCallRecord]:
        """
        Get the most recent call.

        Returns:
            Last call record or None if no calls
        """
        return self._call_history[-1] if self._call_history else None

    def clear_history(self) -> None:
        """Clear call history."""
        self._call_history.clear()

    def set_latency(self, latency_ms: float) -> None:
        """
        Set simulated latency.

        Args:
            latency_ms: Latency in milliseconds
        """
        self._latency_ms = latency_ms

    def set_fail_rate(self, fail_rate: float) -> None:
        """
        Set failure probability.

        Args:
            fail_rate: Probability of failure (0.0 to 1.0)
        """
        if not 0.0 <= fail_rate <= 1.0:
            raise ValueError("fail_rate must be between 0.0 and 1.0")
        self._fail_rate = fail_rate

    def reset(self) -> None:
        """Reset stub to initial state."""
        self._call_count = 0
        self._response_queue.clear()
        self._error_queue.clear()
        self._call_history.clear()
        self._latency_ms = 0.0
        self._fail_rate = 0.0
        self._connected = False

    @property
    def call_count(self) -> int:
        """Get total number of execute() calls."""
        return self._call_count

    @property
    def is_network_isolated(self) -> bool:
        """Stubs never make network calls."""
        return True
