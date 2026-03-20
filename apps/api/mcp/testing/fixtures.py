"""
Pytest fixtures for MCP stub testing.

This module provides fixtures for testing with MCP stubs.
Import these in your conftest.py or use directly in tests.

Usage in conftest.py:
    from mcp.testing.fixtures import *  # noqa: F401, F403
"""

from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest

from mcp.stubs import EchoStubConnector
from mcp.testing.network_guard import NetworkGuard
from mcp.testing.stub_registry import StubRegistry

if TYPE_CHECKING:
    pass


@pytest.fixture
def mcp_stub_registry() -> Generator[StubRegistry, None, None]:
    """
    Create a fresh stub registry for each test.

    The registry is automatically reset after the test.

    Yields:
        StubRegistry instance
    """
    registry = StubRegistry(enforce_network_isolation=True)
    yield registry
    registry.clear()


@pytest.fixture
def echo_stub() -> EchoStubConnector:
    """
    Create an echo stub for simple testing.

    Returns:
        EchoStubConnector instance
    """
    return EchoStubConnector()


@pytest.fixture
def network_isolated() -> Generator[NetworkGuard, None, None]:
    """
    Context manager for network isolation.

    Ensures no network calls are made during the test.

    Yields:
        NetworkGuard instance with isolation enabled
    """
    with NetworkGuard.enabled() as guard:
        yield guard


@pytest.fixture(autouse=False)
def auto_network_isolation(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """
    Auto-use fixture for network isolation in unit tests.

    Automatically enabled for tests not marked with @pytest.mark.integration.

    To use, add to conftest.py:
        @pytest.fixture(autouse=True)
        def auto_network_isolation_wrapper(request):
            from mcp.testing.fixtures import auto_network_isolation
            yield from auto_network_isolation(request)
    """
    # Check if test is marked as integration
    if request.node.get_closest_marker("integration"):
        # Skip isolation for integration tests
        yield
        return

    # Enable network isolation for unit tests
    with NetworkGuard.enabled():
        yield


# Stub response fixtures for common test scenarios


@pytest.fixture
def stub_property_responses() -> list[dict]:
    """
    Sample property response data for stub configuration.

    Returns:
        List of property response dictionaries
    """
    return [
        {
            "id": "stub-prop-1",
            "city": "Krakow",
            "rooms": 2,
            "bathrooms": 1,
            "price": 950,
            "area_sqm": 55,
            "has_parking": True,
            "property_type": "APARTMENT",
        },
        {
            "id": "stub-prop-2",
            "city": "Warsaw",
            "rooms": 3,
            "bathrooms": 2,
            "price": 1350,
            "area_sqm": 75,
            "has_parking": True,
            "property_type": "APARTMENT",
        },
    ]


@pytest.fixture
def stub_search_responses() -> list[dict]:
    """
    Sample search response data for stub configuration.

    Returns:
        List of search response dictionaries
    """
    return [
        {
            "query": "apartments in Krakow",
            "results": [
                {"id": "result-1", "score": 0.95},
                {"id": "result-2", "score": 0.87},
            ],
            "total": 2,
        },
        {
            "query": "2-bedroom Warsaw",
            "results": [
                {"id": "result-3", "score": 0.92},
            ],
            "total": 1,
        },
    ]
