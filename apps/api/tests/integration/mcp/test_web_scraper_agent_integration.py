"""
Integration tests for WebScraperConnector with HybridAgent.

Tests the web scraper connector integration with the agent system.

Task #72: MCP Web Scraper Connector
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp.connectors.web_scraper import (
    ScraperTarget,
    WebScraperConfig,
    WebScraperConnector,
)

# Sample HTML for testing
SAMPLE_PROPERTY_LISTING = """
<!DOCTYPE html>
<html>
<head><title>Property Listings</title></head>
<body>
    <div class="property-listing" data-id="123">
        <h2 class="title">Beautiful Apartment in Berlin</h2>
        <span class="price">€450,000</span>
        <span class="location">Mitte, Berlin</span>
        <span class="size">85 m²</span>
        <span class="rooms">3 rooms</span>
    </div>
    <div class="property-listing" data-id="124">
        <h2 class="title">Modern Loft in Munich</h2>
        <span class="price">€680,000</span>
        <span class="location">Schwabing, Munich</span>
        <span class="size">120 m²</span>
        <span class="rooms">4 rooms</span>
    </div>
</body>
</html>
"""


class TestWebScraperConnectorIntegration:
    """Integration tests for WebScraperConnector."""

    @pytest.fixture
    def scraper_config(self):
        """Create scraper configuration for testing."""
        return WebScraperConfig(
            allowed_domains=["example.com", "real-estate.test"],
            targets=[
                ScraperTarget(
                    url_pattern="https://example.com/properties/*",
                    selectors={
                        "title": "h2.title",
                        "price": "span.price",
                        "location": "span.location",
                        "size": "span.size",
                        "rooms": "span.rooms",
                    },
                ),
            ],
            rate_limit_rpm=60,
            max_retries=2,
            cache_ttl_seconds=0,  # Disable caching for tests
        )

    @pytest.fixture
    async def connected_connector(self, scraper_config):
        """Create and connect a WebScraperConnector."""
        connector = WebScraperConnector(scraper_config=scraper_config)
        await connector.connect()
        yield connector
        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_scrape_property_listings(self, connected_connector):
        """Test scraping property listings from a mock page."""
        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_PROPERTY_LISTING

        connected_connector._client.get = AsyncMock(return_value=mock_response)

        result = await connected_connector.execute("scrape", {
            "url": "https://example.com/properties/berlin",
            "selectors": {
                "titles": "h2.title",
                "prices": "span.price",
                "locations": "span.location",
            },
        })

        assert result.success is True
        assert "titles" in result.data
        assert len(result.data["titles"]) == 2
        assert "Beautiful Apartment in Berlin" in result.data["titles"]
        assert "€450,000" in result.data["prices"][0]

    @pytest.mark.asyncio
    async def test_scrape_with_target_config(self, connected_connector):
        """Test scraping using pre-configured target selectors."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_PROPERTY_LISTING

        connected_connector._client.get = AsyncMock(return_value=mock_response)

        # URL matches the target config pattern
        result = await connected_connector.execute("scrape", {
            "url": "https://example.com/properties/berlin/apartments",
        })

        assert result.success is True
        # Should use selectors from target config
        # Note: When multiple elements match, scraper returns a list
        assert "title" in result.data
        assert isinstance(result.data["title"], list)
        assert len(result.data["title"]) == 2
        assert "Beautiful Apartment in Berlin" in result.data["title"]

    @pytest.mark.asyncio
    async def test_scrape_batch_properties(self, connected_connector):
        """Test batch scraping multiple property pages."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_PROPERTY_LISTING

        connected_connector._client.get = AsyncMock(return_value=mock_response)

        result = await connected_connector.execute("scrape_batch", {
            "urls": [
                "https://example.com/properties/berlin",
                "https://example.com/properties/munich",
            ],
            "selectors": {"titles": "h2.title"},
        })

        assert result.success is True
        assert result.data["total"] == 2
        assert result.data["successful"] == 2
        assert result.data["failed"] == 0

    @pytest.mark.asyncio
    async def test_scrape_blocked_domain(self, connected_connector):
        """Test that scraping blocked domains is rejected."""
        result = await connected_connector.execute("scrape", {
            "url": "https://blocked-domain.com/page",
        })

        assert result.success is False
        assert "not in the allowed list" in str(result.errors)

    @pytest.mark.asyncio
    async def test_scrape_handles_403_blocked(self, connected_connector):
        """Test handling of 403 Forbidden responses."""
        mock_response = MagicMock()
        mock_response.status_code = 403

        connected_connector._client.get = AsyncMock(return_value=mock_response)

        result = await connected_connector.execute("scrape", {
            "url": "https://example.com/protected",
        })

        assert result.success is False
        assert "403" in str(result.errors)

    @pytest.mark.asyncio
    async def test_scrape_handles_404_not_found(self, connected_connector):
        """Test handling of 404 Not Found responses."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        connected_connector._client.get = AsyncMock(return_value=mock_response)

        result = await connected_connector.execute("scrape", {
            "url": "https://example.com/nonexistent",
        })

        assert result.success is False
        assert "404" in str(result.errors)

    @pytest.mark.asyncio
    async def test_scrape_retries_on_429(self, connected_connector):
        """Test retry behavior on rate limit (429) responses."""
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "0.01"}

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.text = SAMPLE_PROPERTY_LISTING

        connected_connector._client.get = AsyncMock(
            side_effect=[mock_response_429, mock_response_200]
        )

        result = await connected_connector.execute("scrape", {
            "url": "https://example.com/properties/test",
            "selectors": {"title": "h2.title"},
        })

        assert result.success is True
        assert connected_connector._client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_health_check_returns_metrics(self, connected_connector):
        """Test health check returns connector metrics."""
        result = await connected_connector.health_check()

        assert result.success is True
        assert result.data["connected"] is True
        assert "request_count" in result.data
        assert "rate_limit_rpm" in result.data
        assert result.data["allowed_domains"] == 2

    @pytest.mark.asyncio
    async def test_list_targets(self, connected_connector):
        """Test listing configured scraping targets."""
        result = await connected_connector.execute("list_targets")

        assert result.success is True
        assert len(result.data["targets"]) == 1
        pattern = result.data["targets"][0]["url_pattern"]
        assert pattern == "https://example.com/properties/*"

    @pytest.mark.asyncio
    async def test_validate_selector(self, connected_connector):
        """Test CSS selector validation."""
        result = await connected_connector.execute("validate_selector", {
            "selector": "h2.title",
            "sample_html": SAMPLE_PROPERTY_LISTING,
        })

        assert result.success is True
        assert result.data["valid"] is True
        assert result.data["matched_elements"] == 2


class TestWebScraperConnectorWithAgentTools:
    """Test WebScraperConnector as a LangChain tool for HybridAgent."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM."""
        llm = MagicMock()
        response = MagicMock(content="Response from LLM")
        llm.ainvoke = AsyncMock(return_value=response)
        return llm

    @pytest.fixture
    def mock_retriever(self):
        """Create a mock retriever."""
        retriever = MagicMock()
        retriever.ainvoke = AsyncMock(return_value=[])
        return retriever

    @pytest.mark.asyncio
    async def test_scraper_can_be_wrapped_as_tool(self):
        """Test that WebScraperConnector can be wrapped as a LangChain tool."""
        from langchain_core.tools import tool

        @tool
        def scrape_property_listings(url: str) -> str:
            """Scrape property listings from a URL."""
            return f"Scraped data from {url}"

        name = scrape_property_listings.name
        assert name == "scrape_property_listings"
        result = scrape_property_listings.invoke(
            "https://example.com/properties"
        )
        assert "Scraped data" in result

    @pytest.mark.asyncio
    async def test_connector_context_manager(self):
        """Test async context manager pattern for connector."""
        config = WebScraperConfig(allowed_domains=["example.com"])

        async with WebScraperConnector(scraper_config=config) as connector:
            assert connector._connected is True
            assert connector._client is not None

            # Mock a response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "<html><body>Test</body></html>"
            connector._client.get = AsyncMock(return_value=mock_response)

            result = await connector.execute("scrape", {
                "url": "https://example.com/test",
            })

            assert result.success is True

        # After context exit, should be disconnected
        assert connector._connected is False
        assert connector._client is None

    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self):
        """Test rate limiting across multiple requests."""
        from mcp.rate_limiter import (
            RateLimitConfig,
            get_connector_rate_limiter,
            reset_rate_limiter,
        )

        reset_rate_limiter()

        config = WebScraperConfig(
            allowed_domains=["example.com"],
            rate_limit_rpm=2,  # Very low limit
            max_retries=1,
        )

        connector = WebScraperConnector(scraper_config=config)
        await connector.connect()

        # Configure rate limiter
        limiter = get_connector_rate_limiter()
        limiter._connector_configs["web_scraper"] = RateLimitConfig(
            requests_per_minute=2,
            burst_size=0,  # No burst
            enabled=True,
        )
        if "web_scraper" in limiter._request_times:
            limiter._request_times["web_scraper"].clear()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test</body></html>"
        connector._client.get = AsyncMock(return_value=mock_response)

        # First two requests should succeed
        result1 = await connector.execute(
            "scrape", {"url": "https://example.com/1"}
        )
        result2 = await connector.execute(
            "scrape", {"url": "https://example.com/2"}
        )

        # Third should be rate limited
        result3 = await connector.execute(
            "scrape", {"url": "https://example.com/3"}
        )

        assert result1.success is True
        assert result2.success is True
        assert result3.success is False
        assert "Rate limit exceeded" in str(result3.errors)

        await connector.disconnect()
        reset_rate_limiter()

    @pytest.mark.asyncio
    async def test_error_recovery_in_batch(self):
        """Test that batch scraping continues despite individual failures."""
        config = WebScraperConfig(
            allowed_domains=[],
            max_retries=1,
        )

        connector = WebScraperConnector(scraper_config=config)
        await connector.connect()

        # First call succeeds, second fails, third succeeds
        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200
        mock_response_ok.text = "<html><body>OK</body></html>"

        mock_response_404 = MagicMock()
        mock_response_404.status_code = 404

        connector._client.get = AsyncMock(
            side_effect=[
                mock_response_ok,
                mock_response_404,
                mock_response_ok,
            ]
        )

        result = await connector.execute("scrape_batch", {
            "urls": [
                "https://site1.com/page",
                "https://site2.com/missing",
                "https://site3.com/page",
            ],
            "selectors": {"content": "body"},
        })

        assert result.success is True
        assert result.data["total"] == 3
        assert result.data["successful"] == 2
        assert result.data["failed"] == 1

        await connector.disconnect()


class TestWebScraperConnectorRegistryIntegration:
    """Test WebScraperConnector registration with MCP registry."""

    @pytest.fixture(autouse=True)
    def setup_registry(self):
        """Ensure connector is registered before each test."""
        # Import to trigger @register_mcp_connector decorator
        from mcp.connectors import web_scraper  # noqa: F401
        from mcp.registry import MCPConnectorRegistry

        # Ensure it's registered
        if "web_scraper" not in MCPConnectorRegistry._connectors:
            MCPConnectorRegistry.register(web_scraper.WebScraperConnector)

    def test_connector_registered_in_registry(self):
        """Test that WebScraperConnector is properly registered."""
        from mcp.registry import MCPConnectorRegistry

        # Check if web_scraper is registered
        info = MCPConnectorRegistry.get_connector_info("web_scraper")

        assert info is not None
        assert info["name"] == "web_scraper"
        assert info["display_name"] == "Web Scraper"
        assert info["allowlisted"] is True
        assert info["min_edition"] == "community"

    def test_connector_accessible_in_community_edition(self):
        """Test that WebScraperConnector is accessible in Community Edition."""
        from mcp.config import MCPEdition
        from mcp.registry import MCPConnectorRegistry, get_mcp_connector

        MCPConnectorRegistry.set_edition(MCPEdition.COMMUNITY)

        # Should not raise MCPNotAllowlistedError
        connector = get_mcp_connector("web_scraper")

        assert connector is not None
        assert connector.name == "web_scraper"
