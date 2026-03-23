"""
MCP Connector implementations.

This package contains real MCP connector implementations that make
actual network calls to external services.

Available Connectors:
    - WebScraperConnector: Configurable web scraping for content extraction

For testing, use stubs from mcp.stubs instead.
"""

from mcp.connectors.web_scraper import WebScraperConnector

__all__ = ["WebScraperConnector"]
