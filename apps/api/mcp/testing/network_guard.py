"""
NetworkGuard for enforcing network isolation in tests.

Provides context manager and utilities to ensure tests don't make
network calls, guaranteeing deterministic and fast unit tests.
"""

import socket
from contextlib import contextmanager
from typing import Generator
from unittest.mock import patch


class NetworkIsolationError(Exception):
    """Raised when a network call is attempted during isolation."""

    pass


class NetworkGuard:
    """
    Context manager for enforcing network isolation in tests.

    Blocks all network calls by patching socket.socket, ensuring
    unit tests remain deterministic and fast.

    Usage:
        with NetworkGuard.enabled():
            # Any network call raises NetworkIsolationError
            await connector.execute(...)  # Safe if using stubs

        # Or as a pytest fixture
        def test_with_isolation(network_isolated):
            # Network calls blocked here
            pass

    Attributes:
        _active: Whether network isolation is currently active
    """

    _active: bool = False

    @classmethod
    @contextmanager
    def enabled(cls) -> Generator["NetworkGuard", None, None]:
        """
        Enable network isolation for the context.

        Any attempt to create a network socket will raise NetworkIsolationError.

        Yields:
            NetworkGuard instance for verification
        """
        cls._active = True

        def block_socket(*args: object, **kwargs: object) -> None:
            raise NetworkIsolationError(
                "Network call attempted during isolated test. "
                "Use MCP stubs instead of real connectors."
            )

        with patch("socket.socket", side_effect=block_socket):
            guard = cls()
            yield guard

        cls._active = False

    @classmethod
    @contextmanager
    def disabled(cls) -> Generator["NetworkGuard", None, None]:
        """
        Temporarily disable network isolation (for integration tests).

        Yields:
            NetworkGuard instance
        """
        was_active = cls._active
        cls._active = False
        guard = cls()
        yield guard
        cls._active = was_active

    @classmethod
    def is_active(cls) -> bool:
        """
        Check if network isolation is currently active.

        Returns:
            True if network calls are blocked
        """
        return cls._active

    def verify_isolation(self) -> bool:
        """
        Verify that isolation is active.

        Returns:
            True if network is isolated

        Raises:
            RuntimeError: If isolation is not active
        """
        if not self._active:
            raise RuntimeError("Network isolation is not active")
        return True

    @staticmethod
    def check_network_available() -> bool:
        """
        Check if network is available (for integration tests).

        Returns:
            True if network is accessible
        """
        try:
            # Try to connect to a reliable host
            socket.create_connection(("8.8.8.8", 53), timeout=1)
            return True
        except OSError:
            return False


def assert_no_network_calls(func):
    """
    Decorator to ensure a function makes no network calls.

    Usage:
        @assert_no_network_calls
        def test_my_stub():
            # This will fail if it makes network calls
            ...

    Args:
        func: Function to wrap

    Returns:
        Wrapped function
    """
    import asyncio
    from functools import wraps

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        with NetworkGuard.enabled():
            return func(*args, **kwargs)

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        with NetworkGuard.enabled():
            return await func(*args, **kwargs)

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper
