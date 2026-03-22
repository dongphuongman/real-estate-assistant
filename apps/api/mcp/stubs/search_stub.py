"""
PropertySearchStub for deterministic search testing.

Provides configurable search responses without vector store or network access.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from mcp.config import MCPEdition
from mcp.result import MCPConnectorResult
from mcp.stubs.base_stub import MCPStub


@dataclass
class SearchResult:
    """Result from a property search operation."""

    query: str
    properties: List[Dict[str, Any]] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 10
    metadata: Dict[str, Any] = field(default_factory=dict)


class PropertySearchStub(MCPStub[SearchResult]):
    """
    Stub for property search operations.

    Simulates search behavior with configurable results,
    ranking, and pagination.

    Attributes:
        name: "property_search_stub"
        display_name: "Property Search Stub (Testing)"

    Operations:
        - search: Execute a search query
        - suggest: Get search suggestions
        - facets: Get search facets/filters

    Example:
        stub = PropertySearchStub()
        stub.set_search_handler(lambda q: SearchResult(
            query=q,
            properties=[{"id": "1", "score": 0.95}],
            total=1,
        ))

        result = await stub.execute("search", {"query": "Krakow"})
        assert result.success
        assert result.data.total == 1
    """

    name = "property_search_stub"
    display_name = "Property Search Stub (Testing)"
    description = "Stub for property search operations"
    requires_api_key = False
    allowlisted = True
    min_edition = MCPEdition.COMMUNITY
    supports_streaming = False

    def __init__(
        self,
        search_results: Optional[List[SearchResult]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the search stub.

        Args:
            search_results: Pre-configured search results
            **kwargs: Additional arguments for MCPStub
        """
        super().__init__(**kwargs)
        self._search_handler: Optional[Callable[[str], SearchResult]] = None
        self._suggestions: List[str] = []

        # Queue pre-configured results
        if search_results:
            self.add_responses(search_results)

    def set_search_handler(self, handler: Callable[[str], SearchResult]) -> None:
        """
        Set a custom search handler.

        The handler receives the query string and returns a SearchResult.

        Args:
            handler: Function that takes a query and returns SearchResult
        """
        self._search_handler = handler

    def set_suggestions(self, suggestions: List[str]) -> None:
        """
        Set search suggestions.

        Args:
            suggestions: List of suggestion strings
        """
        self._suggestions = suggestions

    async def execute(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MCPConnectorResult[SearchResult]:
        """
        Execute a search operation.

        Args:
            operation: Operation to execute
            params: Operation parameters

        Returns:
            MCPConnectorResult with SearchResult
        """
        await self._simulate_latency()

        self._call_count += 1

        # Check for queued errors first
        if self._error_queue:
            error = self._error_queue.popleft()
            result = MCPConnectorResult.error_result(
                errors=[error],
                connector_name=self.name,
                operation=operation,
            )
            self._record_call(operation, params, kwargs, result=result)
            return result

        # Route to operation handler
        try:
            data = await self._handle_operation(operation, params or {})
            result = MCPConnectorResult.success_result(
                data=data,
                connector_name=self.name,
                operation=operation,
                metadata={"stub": True},
            )
            self._record_call(operation, params, kwargs, result=result)
            return result
        except Exception as e:
            result = MCPConnectorResult.error_result(
                errors=[str(e)],
                connector_name=self.name,
                operation=operation,
            )
            self._record_call(operation, params, kwargs, error=str(e))
            return result

    async def _handle_operation(self, operation: str, params: Dict[str, Any]) -> SearchResult:
        """Handle the operation."""
        if operation == "search":
            return await self._op_search(params)
        elif operation == "suggest":
            return self._op_suggest(params)
        elif operation == "facets":
            return self._op_facets(params)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    async def _op_search(self, params: Dict[str, Any]) -> SearchResult:
        """Execute a search."""
        query = params.get("query", "")
        page = params.get("page", 1)
        page_size = params.get("page_size", 10)

        # Check for queued responses
        if self._response_queue:
            result = self._response_queue.popleft()
            return result

        # Use custom handler if set
        if self._search_handler:
            result = self._search_handler(query)
            result.page = page
            result.page_size = page_size
            return result

        # Default: return empty result
        return SearchResult(
            query=query,
            properties=[],
            scores=[],
            total=0,
            page=page,
            page_size=page_size,
        )

    def _op_suggest(self, params: Dict[str, Any]) -> SearchResult:
        """Get search suggestions."""
        prefix = params.get("prefix", "")

        # Filter suggestions by prefix
        filtered = [s for s in self._suggestions if s.lower().startswith(prefix.lower())]

        return SearchResult(
            query=prefix,
            properties=[{"suggestion": s} for s in filtered[:10]],
            total=len(filtered),
            metadata={"type": "suggestions"},
        )

    def _op_facets(self, params: Dict[str, Any]) -> SearchResult:
        """Get search facets."""
        # Return mock facets
        return SearchResult(
            query="",
            properties=[
                {"facet": "city", "values": ["Krakow", "Warsaw"]},
                {"facet": "rooms", "values": ["1", "2", "3", "4+"]},
            ],
            total=2,
            metadata={"type": "facets"},
        )

    def reset(self) -> None:
        """Reset stub to initial state."""
        super().reset()
        self._search_handler = None
        self._suggestions = []
