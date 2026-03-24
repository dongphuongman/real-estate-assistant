"""
Unit tests for WebScraperConnector.

Tests the web scraper connector without making network calls.
Uses httpx mock transport for HTTP request simulation.

Task #72: MCP Web Scraper Connector
"""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from mcp.config import MCPEdition
from mcp.connectors.web_scraper import (
    ScraperTarget,
    WebScraperConfig,
    WebScraperConnector,
)
from mcp.exceptions import MCPOperationError

# Sample HTML for testing
SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body>
    <h1 class="title">Sample Title</h1>
    <article>
        <p class="content">This is sample content for testing.</p>
        <p class="content">Second paragraph.</p>
    </article>
    <ul class="links">
        <li><a href="/page1">Link 1</a></li>
        <li><a href="/page2">Link 2</a></li>
    </ul>
</body>
</html>
"""


class TestWebScraperConnectorAttributes:
    """Tests for connector class attributes."""

    def test_connector_name(self):
        """Test connector has correct name."""
        assert WebScraperConnector.name == "web_scraper"

    def test_connector_display_name(self):
        """Test connector has correct display name."""
        assert WebScraperConnector.display_name == "Web Scraper"

    def test_connector_description(self):
        """Test connector has description."""
        assert "web scraping" in WebScraperConnector.description.lower()

    def test_connector_allowlisted(self):
        """Test connector is allowlisted for CE."""
        assert WebScraperConnector.allowlisted is True

    def test_connector_min_edition(self):
        """Test connector minimum edition is COMMUNITY."""
        assert WebScraperConnector.min_edition == MCPEdition.COMMUNITY

    def test_connector_no_api_key_required(self):
        """Test connector does not require API key."""
        assert WebScraperConnector.requires_api_key is False

    def test_connector_no_streaming(self):
        """Test connector does not support streaming."""
        assert WebScraperConnector.supports_streaming is False


class TestScraperTarget:
    """Tests for ScraperTarget dataclass."""

    def test_url_pattern_matching(self):
        """Test URL pattern matching with glob patterns."""
        target = ScraperTarget(
            url_pattern="https://example.com/*",
            selectors={"title": "h1"},
        )
        assert target.matches("https://example.com/page1")
        assert target.matches("https://example.com/page2")
        assert not target.matches("https://other.com/page1")

    def test_default_values(self):
        """Test default values for ScraperTarget."""
        target = ScraperTarget(url_pattern="*")
        assert target.selectors == {}
        assert target.max_depth == 1
        assert target.enabled is True


class TestWebScraperConfig:
    """Tests for WebScraperConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = WebScraperConfig()
        assert config.allowed_domains == []
        assert config.targets == []
        assert config.rate_limit_rpm == 30
        assert config.max_retries == 3
        assert config.retry_delay_seconds == 1.0
        assert config.cache_ttl_seconds == 300
        assert config.timeout_seconds == 30.0

    def test_custom_values(self):
        """Test custom configuration values."""
        config = WebScraperConfig(
            allowed_domains=["example.com"],
            rate_limit_rpm=60,
            max_retries=5,
        )
        assert config.allowed_domains == ["example.com"]
        assert config.rate_limit_rpm == 60
        assert config.max_retries == 5


class TestWebScraperConnectorSync:
    """Synchronous tests for WebScraperConnector."""

    def test_domain_validation_blocks_non_allowed(self):
        """Test connector blocks requests to non-allowed domains."""
        config = WebScraperConfig(allowed_domains=["allowed.com"])
        connector = WebScraperConnector(scraper_config=config)

        # Should raise error for non-allowed domain
        with pytest.raises(MCPOperationError) as exc_info:
            connector._validate_url("https://blocked.com/page")
        assert "not in the allowed list" in str(exc_info.value)

    def test_domain_validation_allows_subdomain(self):
        """Test connector allows subdomains of allowed domains."""
        config = WebScraperConfig(allowed_domains=["example.com"])
        connector = WebScraperConnector(scraper_config=config)

        # Should allow subdomain
        domain = connector._validate_url("https://sub.example.com/page")
        assert domain == "sub.example.com"

    def test_domain_validation_allows_exact_match(self):
        """Test connector allows exact domain match."""
        config = WebScraperConfig(allowed_domains=["example.com"])
        connector = WebScraperConnector(scraper_config=config)

        domain = connector._validate_url("https://example.com/page")
        assert domain == "example.com"

    def test_domain_validation_no_allowlist(self):
        """Test connector allows all domains when no allowlist."""
        config = WebScraperConfig(allowed_domains=[])
        connector = WebScraperConnector(scraper_config=config)

        domain = connector._validate_url("https://any-domain.com/page")
        assert domain == "any-domain.com"

    def test_url_validation_invalid_scheme(self):
        """Test connector rejects non-HTTP schemes."""
        connector = WebScraperConnector()

        with pytest.raises(MCPOperationError) as exc_info:
            connector._validate_url("ftp://example.com/file")
        assert "Invalid URL scheme" in str(exc_info.value)

    def test_url_validation_missing_domain(self):
        """Test connector rejects URLs without domain."""
        connector = WebScraperConnector()

        with pytest.raises(MCPOperationError):
            connector._validate_url("/relative/path")

    def test_parse_content_with_selectors(self):
        """Test HTML parsing with CSS selectors."""
        connector = WebScraperConnector()

        result = connector._parse_content(SAMPLE_HTML, {
            "title": "h1.title",
            "content": "p.content",
            "links": "ul.links a",
        })

        assert result["title"] == "Sample Title"
        assert len(result["content"]) == 2
        assert "sample content" in result["content"][0] or "Second paragraph" in result["content"][0]
        assert len(result["links"]) == 2

    def test_parse_content_single_element(self):
        """Test parsing with single element selector."""
        connector = WebScraperConnector()

        result = connector._parse_content(SAMPLE_HTML, {"title": "h1.title"})

        assert result["title"] == "Sample Title"

    def test_parse_content_no_match(self):
        """Test parsing when selector matches nothing."""
        connector = WebScraperConnector()

        result = connector._parse_content(SAMPLE_HTML, {"missing": ".nonexistent"})

        assert result["missing"] is None

    def test_clean_text_normalization(self):
        """Test text cleaning normalizes whitespace."""
        connector = WebScraperConnector()

        dirty = "  Multiple   \n\n  spaces   \t  and  \n  newlines  "
        clean = connector._clean_text(dirty)

        assert clean == "Multiple spaces and newlines"

    def test_find_target_config_matching(self):
        """Test finding matching target configuration."""
        target = ScraperTarget(
            url_pattern="https://blog.example.com/*",
            selectors={"title": "h1"},
        )
        config = WebScraperConfig(targets=[target])
        connector = WebScraperConnector(scraper_config=config)

        found = connector._find_target_config("https://blog.example.com/post/123")

        assert found is not None
        assert found.selectors == {"title": "h1"}

    def test_find_target_config_no_match(self):
        """Test finding target when no match exists."""
        target = ScraperTarget(
            url_pattern="https://other.com/*",
            selectors={"title": "h1"},
        )
        config = WebScraperConfig(targets=[target])
        connector = WebScraperConnector(scraper_config=config)

        found = connector._find_target_config("https://example.com/page")

        assert found is None


class TestWebScraperConnectorAsync:
    """Async tests for WebScraperConnector."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock httpx client."""
        client = AsyncMock(spec=httpx.AsyncClient)
        return client

    @pytest.fixture
    def connector(self):
        """Create a connector instance for testing."""
        return WebScraperConnector(
            scraper_config=WebScraperConfig(
                allowed_domains=[],
                max_retries=1,
                retry_delay_seconds=0.1,
            )
        )

    @pytest.mark.asyncio
    async def test_connect_initializes_client(self, connector):
        """Test connect initializes HTTP client."""
        result = await connector.connect()

        assert result is True
        assert connector._connected is True
        assert connector._client is not None

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_closes_client(self, connector):
        """Test disconnect closes HTTP client."""
        await connector.connect()
        await connector.disconnect()

        assert connector._connected is False
        assert connector._client is None

    @pytest.mark.asyncio
    async def test_health_check_returns_status(self, connector):
        """Test health check returns connector status."""
        await connector.connect()

        result = await connector.health_check()

        assert result.success is True
        assert result.data["connected"] is True
        assert "request_count" in result.data
        assert "rate_limit_rpm" in result.data

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_scrape_missing_url_param(self, connector):
        """Test scrape returns error when URL is missing."""
        await connector.connect()

        result = await connector.execute("scrape", {})

        assert result.success is False
        assert "Missing required parameter: url" in result.errors

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_scrape_success(self, connector):
        """Test successful scrape operation."""
        await connector.connect()

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_HTML

        connector._client.get = AsyncMock(return_value=mock_response)

        result = await connector.execute("scrape", {
            "url": "https://example.com/test",
            "selectors": {"title": "h1.title"},
        })

        assert result.success is True
        assert result.data["title"] == "Sample Title"
        assert result.data["url"] == "https://example.com/test"

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_scrape_blocked_403(self, connector):
        """Test scrape returns error for blocked (403) requests."""
        await connector.connect()

        mock_response = MagicMock()
        mock_response.status_code = 403
        connector._client.get = AsyncMock(return_value=mock_response)

        result = await connector.execute("scrape", {
            "url": "https://example.com/blocked",
        })

        assert result.success is False
        assert "403" in str(result.errors)

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_scrape_not_found_404(self, connector):
        """Test scrape returns error for not found (404) requests."""
        await connector.connect()

        mock_response = MagicMock()
        mock_response.status_code = 404
        connector._client.get = AsyncMock(return_value=mock_response)

        result = await connector.execute("scrape", {
            "url": "https://example.com/notfound",
        })

        assert result.success is False
        assert "404" in str(result.errors)

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_scrape_rate_limited_429_retry(self, connector):
        """Test scrape retries on rate limit (429) response."""
        # Use config with 2 retries (3 total attempts)
        config = WebScraperConfig(
            allowed_domains=[],
            max_retries=3,  # Need at least 2 attempts for retry
            retry_delay_seconds=0.05,
        )
        connector = WebScraperConnector(scraper_config=config)
        await connector.connect()

        # First call: 429, second call: 200
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "0.05"}

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.text = SAMPLE_HTML

        connector._client.get = AsyncMock(
            side_effect=[mock_response_429, mock_response_200]
        )

        result = await connector.execute("scrape", {
            "url": "https://example.com/ratelimited",
            "selectors": {"title": "h1.title"},
        })

        assert result.success is True
        assert connector._client.get.call_count == 2

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_scrape_timeout_retry(self, connector):
        """Test scrape retries on timeout."""
        # Use config with 2 retries
        config = WebScraperConfig(
            allowed_domains=[],
            max_retries=3,
            retry_delay_seconds=0.05,
        )
        connector = WebScraperConnector(scraper_config=config)
        await connector.connect()

        # First call: timeout, second call: success
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_HTML

        connector._client.get = AsyncMock(
            side_effect=[
                httpx.TimeoutException("Request timed out"),
                mock_response,
            ]
        )

        result = await connector.execute("scrape", {
            "url": "https://example.com/timeout",
            "selectors": {"title": "h1.title"},
        })

        assert result.success is True
        assert connector._client.get.call_count == 2

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_scrape_batch_success(self, connector):
        """Test successful batch scrape operation."""
        await connector.connect()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_HTML
        connector._client.get = AsyncMock(return_value=mock_response)

        result = await connector.execute("scrape_batch", {
            "urls": [
                "https://example.com/page1",
                "https://example.com/page2",
            ],
            "selectors": {"title": "h1.title"},
        })

        assert result.success is True
        assert result.data["total"] == 2
        assert result.data["successful"] == 2
        assert result.data["failed"] == 0

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_scrape_batch_max_urls(self, connector):
        """Test batch scrape rejects more than 50 URLs."""
        await connector.connect()

        urls = [f"https://example.com/page/{i}" for i in range(51)]

        result = await connector.execute("scrape_batch", {
            "urls": urls,
        })

        assert result.success is False
        assert "Maximum 50 URLs" in str(result.errors)

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_validate_selector_valid(self, connector):
        """Test validate_selector with valid CSS selector."""
        await connector.connect()

        result = await connector.execute("validate_selector", {
            "selector": "h1.title",
            "sample_html": SAMPLE_HTML,
        })

        assert result.success is True
        assert result.data["valid"] is True
        assert result.data["matched_elements"] >= 1

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_list_targets(self, connector):
        """Test list_targets operation."""
        target = ScraperTarget(
            url_pattern="https://example.com/*",
            selectors={"title": "h1"},
        )
        config = WebScraperConfig(
            allowed_domains=["example.com"],
            targets=[target],
        )
        connector = WebScraperConnector(scraper_config=config)
        await connector.connect()

        result = await connector.execute("list_targets")

        assert result.success is True
        assert len(result.data["targets"]) == 1
        assert result.data["allowed_domains"] == ["example.com"]

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_unknown_operation(self, connector):
        """Test unknown operation returns error."""
        await connector.connect()

        result = await connector.execute("unknown_op", {})

        assert result.success is False
        assert "Unknown operation" in str(result.errors)

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_caching(self, connector):
        """Test response caching."""
        config = WebScraperConfig(cache_ttl_seconds=60)
        connector = WebScraperConnector(scraper_config=config)
        await connector.connect()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_HTML
        connector._client.get = AsyncMock(return_value=mock_response)

        # First request
        result1 = await connector.execute("scrape", {
            "url": "https://example.com/cached",
            "selectors": {"title": "h1.title"},
        })

        # Second request (should be cached)
        result2 = await connector.execute("scrape", {
            "url": "https://example.com/cached",
            "selectors": {"title": "h1.title"},
        })

        assert result1.metadata.get("cached") is False
        assert result2.metadata.get("cached") is True
        assert connector._client.get.call_count == 1  # Only one HTTP call

        await connector.disconnect()


class TestWebScraperConnectorRateLimiting:
    """Tests for rate limiting integration."""

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_returns_error(self):
        """Test rate limit exceeded returns error result."""
        from mcp.rate_limiter import reset_rate_limiter

        # Reset rate limiter
        reset_rate_limiter()

        config = WebScraperConfig(rate_limit_rpm=1, max_retries=1)
        connector = WebScraperConnector(scraper_config=config)
        await connector.connect()

        # Mock the client to avoid real network calls
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_HTML
        connector._client.get = AsyncMock(return_value=mock_response)

        # Configure rate limiter with very low limit
        from mcp.rate_limiter import RateLimitConfig, get_connector_rate_limiter

        limiter = get_connector_rate_limiter()
        # Set config directly to avoid the0 or default` issue
        limiter._connector_configs["web_scraper"] = RateLimitConfig(
            requests_per_minute=1,
            burst_size=0,  # No burst - exactly 1 request per minute
            enabled=True,
        )
        # Clear any existing request times
        if "web_scraper" in limiter._request_times:
            limiter._request_times["web_scraper"].clear()

        # First request should succeed
        result1 = await connector.execute("scrape", {"url": "https://example.com/test1"})
        assert result1.success is True

        # Second request should fail due to rate limit
        result2 = await connector.execute("scrape", {"url": "https://example.com/test2"})

        assert result2.success is False
        assert "Rate limit exceeded" in str(result2.errors)

        reset_rate_limiter()
        await connector.disconnect()


class TestWebScraperConnectorContextManager:
    """Tests for async context manager support."""

    @pytest.mark.asyncio
    async def test_context_manager_connect_disconnect(self):
        """Test async context manager connects and disconnects."""
        config = WebScraperConfig()
        async with WebScraperConnector(scraper_config=config) as connector:
            assert connector._connected is True
            assert connector._client is not None

        assert connector._connected is False
        assert connector._client is None
