"""
Web Scraper Stub Connector for testing.

This module provides a deterministic stub for web scraping tests.
Never makes network calls - returns pre-configured responses.

Task #72: MCP Web Scraper Connector
"""

from typing import Any, Dict, List, Optional

from mcp.config import MCPEdition
from mcp.result import MCPConnectorResult
from mcp.stubs.base_stub import MCPStub


class WebScraperStubConnector(MCPStub[Dict[str, Any]]):
    """
    Stub connector for web scraping tests.

    Never makes network calls - returns pre-configured responses.
    Supports queued responses for testing different scenarios.

    Attributes:
        name: "web_scraper_stub"
        display_name: "Web Scraper Stub (Testing)"
        description: "Deterministic stub for web scraper testing"
        requires_api_key: False
        allowlisted: True
        min_edition: MCPEdition.COMMUNITY

    Default Responses:
        - scrape: Returns sample page data with title, content, links
        - scrape_batch: Returns results for each URL
        - validate_selector: Returns valid=True
        - list_targets: Returns empty targets list

    Example:
        stub = WebScraperStubConnector()

        # Add custom response
        stub.add_response({
            "title": "Custom Title",
            "content": "Custom content"
        })

        result = await stub.execute("scrape", {"url": "https://example.com"})
        assert result.data["title"] == "Custom Title"
    """

    name = "web_scraper_stub"
    display_name = "Web Scraper Stub (Testing)"
    description = "Deterministic stub for web scraper testing"
    requires_api_key = False
    allowlisted = True
    min_edition = MCPEdition.COMMUNITY
    supports_streaming = False

    def __init__(
        self,
        responses: Optional[List[Dict[str, Any]]] = None,
        latency_ms: float = 0.0,
        fail_rate: float = 0.0,
        record_calls: bool = True,
        default_domain: str = "example.com",
    ) -> None:
        """
        Initialize the web scraper stub.

        Args:
            responses: Queue of responses to return
            latency_ms: Simulated latency in milliseconds
            fail_rate: Probability of random failure
            record_calls: Whether to record call history
            default_domain: Default domain for generated responses
        """
        super().__init__(
            config=None,
            responses=responses,
            latency_ms=latency_ms,
            fail_rate=fail_rate,
            record_calls=record_calls,
        )
        self._default_domain = default_domain
        self._allowed_domains: List[str] = ["example.com", "*.example.com", "test.org"]

    async def execute(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MCPConnectorResult[Dict[str, Any]]:
        """
        Execute a stub operation.

        Args:
            operation: Operation name
            params: Operation parameters
            **kwargs: Additional options

        Returns:
            MCPConnectorResult with stub data
        """
        await self._simulate_latency()

        # Check for random failure
        if self._should_fail():
            result = self._create_error_result(operation, ["Random failure (fail_rate)"])
            self._record_call(operation, params, kwargs, result=result)
            return result

        # Check for queued errors
        if self._error_queue:
            error = self._error_queue.popleft()
            result = self._create_error_result(operation, [error])
            self._record_call(operation, params, kwargs, result=result)
            return result

        # Check for queued responses
        if self._response_queue:
            response = self._response_queue.popleft()
            result = self._create_success_result(operation, response)
            self._record_call(operation, params, kwargs, result=result)
            return result

        # Route to operation handlers
        if operation == "scrape":
            result = self._handle_scrape(params or {})
        elif operation == "scrape_batch":
            result = self._handle_scrape_batch(params or {})
        elif operation == "validate_selector":
            result = self._handle_validate_selector(params or {})
        elif operation == "list_targets":
            result = self._handle_list_targets()
        else:
            result = self._create_error_result(operation, [f"Unknown operation: {operation}"])

        self._record_call(operation, params, kwargs, result=result)
        return result

    def _handle_scrape(self, params: Dict[str, Any]) -> MCPConnectorResult[Dict[str, Any]]:
        """Handle scrape operation with default response."""
        url = params.get("url", "https://example.com")
        selectors = params.get("selectors", {})

        # Generate default response based on selectors
        data = {
            "url": url,
            "domain": self._default_domain,
            "scraped_at": 1234567890.0,
        }

        # Fill in selector results with sample data
        for field_name in selectors.keys() if selectors else ["content"]:
            if field_name == "title":
                data[field_name] = "Sample Page Title"
            elif field_name == "content":
                data[field_name] = "Sample page content for testing purposes."
            elif field_name == "links":
                data[field_name] = [
                    "https://example.com/page1",
                    "https://example.com/page2",
                ]
            elif field_name == "price":
                data[field_name] = "$1,234,567"
            elif field_name == "description":
                data[field_name] = "Sample property description for testing."
            else:
                data[field_name] = f"Sample {field_name}"

        return self._create_success_result("scrape", data)

    def _handle_scrape_batch(self, params: Dict[str, Any]) -> MCPConnectorResult[Dict[str, Any]]:
        """Handle scrape_batch operation."""
        urls = params.get("urls", [])

        results = []
        for url in urls[:50]:  # Max 50 URLs
            results.append({
                "url": url,
                "success": True,
                "data": {
                    "url": url,
                    "content": f"Content for {url}",
                },
                "errors": None,
            })

        return self._create_success_result("scrape_batch", {
            "results": results,
            "total": len(results),
            "successful": len(results),
            "failed": 0,
        })

    def _handle_validate_selector(self, params: Dict[str, Any]) -> MCPConnectorResult[Dict[str, Any]]:
        """Handle validate_selector operation."""
        selector = params.get("selector", "")

        # Basic validation - check for common invalid patterns
        invalid_patterns = ["[", "]", "!!", ":::"]
        is_valid = not any(p in selector for p in invalid_patterns)

        return self._create_success_result("validate_selector", {
            "selector": selector,
            "valid": is_valid,
            "matched_elements": 1 if is_valid else 0,
        })

    def _handle_list_targets(self) -> MCPConnectorResult[Dict[str, Any]]:
        """Handle list_targets operation."""
        return self._create_success_result("list_targets", {
            "targets": [],
            "allowed_domains": self._allowed_domains,
        })

    def _create_success_result(
        self, operation: str, data: Dict[str, Any]
    ) -> MCPConnectorResult[Dict[str, Any]]:
        """Create a success result."""
        return MCPConnectorResult.success_result(
            data=data,
            connector_name=self.name,
            operation=operation,
            metadata={"stub": True},
        )

    def _create_error_result(
        self, operation: str, errors: List[str]
    ) -> MCPConnectorResult[Dict[str, Any]]:
        """Create an error result."""
        return MCPConnectorResult.error_result(
            errors=errors,
            connector_name=self.name,
            operation=operation,
            metadata={"stub": True},
        )

    def set_allowed_domains(self, domains: List[str]) -> None:
        """
        Set the allowed domains for list_targets response.

        Args:
            domains: List of allowed domain patterns
        """
        self._allowed_domains = domains

    def queue_blocked_response(self, url: str) -> None:
        """
        Queue a blocked (403) error response.

        Args:
            url: URL that will be "blocked"
        """
        self.add_error(f"Access blocked (403): {url}")

    def queue_not_found_response(self, url: str) -> None:
        """
        Queue a not found (404) error response.

        Args:
            url: URL that will be "not found"
        """
        self.add_error(f"Page not found (404): {url}")

    def queue_timeout_response(self, url: str) -> None:
        """
        Queue a timeout error response.

        Args:
            url: URL that will "timeout"
        """
        self.add_error(f"Request timed out: {url}")
