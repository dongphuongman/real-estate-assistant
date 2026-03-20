"""
Echo stub connector for deterministic testing.

This module provides a stub MCP connector that echoes back input,
useful for unit testing without network dependencies.
"""

from typing import Any, AsyncGenerator, Dict, Optional

from mcp.config import MCPEdition
from mcp.stubs.base_stub import MCPStub


class EchoStubConnector(MCPStub[Dict[str, Any]]):
    """
    Deterministic stub connector for testing.

    Echoes back the operation and params in the result data.
    Never makes network calls - safe for unit tests.

    Extends MCPStub for enhanced testing capabilities while
    maintaining backward compatibility with legacy parameters.

    Attributes:
        name: Always "echo_stub"
        display_name: "Echo Stub (Testing)"
        allowlisted: True (available in CE for testing)
        min_edition: COMMUNITY

    Legacy Parameters (backward compatible):
        fail_next: If True, next execute() will fail
        latency_ms: Simulated latency in milliseconds

    New Parameters (from MCPStub):
        responses: Queue of responses to return
        fail_rate: Probability of random failure
        record_calls: Whether to record call history
    """

    name = "echo_stub"
    display_name = "Echo Stub (Testing)"
    description = "Deterministic stub connector for unit testing"
    requires_api_key = False
    allowlisted = True
    min_edition = MCPEdition.COMMUNITY
    supports_streaming = True

    def __init__(
        self,
        config: Optional[Any] = None,
        latency_ms: float = 0.0,
        fail_next: bool = False,
        responses: Optional[list] = None,
        fail_rate: float = 0.0,
        record_calls: bool = True,
    ) -> None:
        """
        Initialize the echo stub.

        Args:
            config: Optional configuration (ignored for stubs)
            latency_ms: Simulated latency in milliseconds
            fail_next: If True, next execute() will fail (legacy)
            responses: Queue of responses to return (new)
            fail_rate: Probability of random failure (new)
            record_calls: Whether to record call history (new)
        """
        super().__init__(
            config=None,  # Stubs don't need config
            responses=responses,
            latency_ms=latency_ms,
            fail_rate=fail_rate,
            record_calls=record_calls,
        )

        # Legacy fail_next support - converts to queued error
        self._fail_next_legacy = fail_next

    async def execute(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> "MCPConnectorResult[Dict[str, Any]]":
        """
        Echo back the operation and params.

        Args:
            operation: Operation name to echo
            params: Parameters to echo

        Returns:
            Result containing the echoed operation and params
        """
        # Simulate latency
        await self._simulate_latency()

        # Check for legacy fail_next flag
        if self._fail_next_legacy:
            self._fail_next_legacy = False
            result = self._create_error_result(operation, ["Simulated failure"])
            self._record_call(operation, params, kwargs, result=result)
            return result

        # Check for random failure (fail_rate)
        if self._should_fail():
            result = self._create_error_result(operation, ["Random failure"])
            self._record_call(operation, params, kwargs, result=result)
            return result

        # Check for queued responses/errors
        if self._error_queue:
            error = self._error_queue.popleft()
            result = self._create_error_result(operation, [error])
            self._record_call(operation, params, kwargs, result=result)
            return result

        if self._response_queue:
            response = self._response_queue.popleft()
            result = self._create_success_result(operation, response)
            self._record_call(operation, params, kwargs, result=result)
            return result

        # Default echo behavior
        self._call_count += 1
        echo_data = {
            "operation": operation,
            "params": params or {},
            "kwargs": kwargs,
            "echo": True,
            "call_count": self._call_count,
        }
        result = self._create_success_result(operation, echo_data)
        self._record_call(operation, params, kwargs, result=result)
        return result

    async def stream(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream echoed results.

        Args:
            operation: Operation name to echo
            params: Parameters to echo

        Yields:
            Chunks of the echoed data
        """
        # Simulate latency
        await self._simulate_latency()

        # Check for legacy fail_next flag
        if self._fail_next_legacy:
            self._fail_next_legacy = False
            yield {"error": "Simulated failure"}
            return

        # Check for random failure
        if self._should_fail():
            yield {"error": "Random failure (fail_rate)"}
            return

        # Check for queued errors
        if self._error_queue:
            error = self._error_queue.popleft()
            yield {"error": error}
            return

        # Check for queued responses
        if self._response_queue:
            response = self._response_queue.popleft()
            self._call_count += 1
            yield response
            return

        # Default streaming behavior - yield each key-value pair
        self._call_count += 1
        result = {
            "operation": operation,
            "params": params or {},
            "kwargs": kwargs,
            "echo": True,
            "streaming": True,
            "call_count": self._call_count,
        }

        for key, value in result.items():
            yield {"key": key, "value": value}

    def set_fail_next(self, fail: bool = True) -> None:
        """
        Configure next execute() to fail.

        Legacy method for backward compatibility.

        Args:
            fail: If True, next call will fail
        """
        self._fail_next_legacy = fail

    def _create_success_result(
        self, operation: str, data: Dict[str, Any]
    ) -> "MCPConnectorResult[Dict[str, Any]]":
        """Create a success result."""
        from mcp.result import MCPConnectorResult

        return MCPConnectorResult.success_result(
            data=data,
            connector_name=self.name,
            operation=operation,
            metadata={"stub": True},
        )

    def _create_error_result(
        self, operation: str, errors: list
    ) -> "MCPConnectorResult[Dict[str, Any]]":
        """Create an error result."""
        from mcp.result import MCPConnectorResult

        return MCPConnectorResult.error_result(
            errors=errors,
            connector_name=self.name,
            operation=operation,
            metadata={"stub": True},
        )


# Import for type hints
from mcp.result import MCPConnectorResult  # noqa: E402
